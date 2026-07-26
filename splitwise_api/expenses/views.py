from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Group, GroupMember, Expense, Settlement
from .serializers import (
    RegisterSerializer, GroupSerializer, GroupMemberSerializer,
    ExpenseSerializer, SettlementSerializer, UserSerializer
)
from .permissions import IsGroupMember
from .utils import calculate_net_balances, simplify_debts


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(members__user=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        GroupMember.objects.create(group=group, user=self.request.user)


class GroupDetailView(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]


class AddMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        self.check_object_permissions(request, group)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)
        member, created = GroupMember.objects.get_or_create(group=group, user=user)

        if not created:
            return Response({'error': 'User already in group'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GroupMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        group = get_object_or_404(Group, id=group_id)
        if not group.members.filter(user=self.request.user).exists():
            return Expense.objects.none()
        return group.expenses.all().order_by('-created_at')

    def perform_create(self, serializer):
        group = get_object_or_404(Group, id=self.kwargs['group_id'])
        if not group.members.filter(user=self.request.user).exists():
            raise permissions.PermissionDenied("You are not a member of this group.")
        serializer.save(group=group, paid_by_id=self.request.data.get('paid_by_id', self.request.user.id))


class GroupBalancesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        self.check_object_permissions(request, group)

        balances = calculate_net_balances(group)
        result = []
        for user_id, balance in balances.items():
            user = User.objects.get(id=user_id)
            result.append({
                'user': UserSerializer(user).data,
                'balance': balance,
                'status': 'is owed' if balance > 0 else 'owes'
            })
        return Response(result)


class GroupSimplifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        self.check_object_permissions(request, group)

        balances = calculate_net_balances(group)
        transactions = simplify_debts(balances)

        result = []
        for txn in transactions:
            result.append({
                'from_user': UserSerializer(User.objects.get(id=txn['from_user'])).data,
                'to_user': UserSerializer(User.objects.get(id=txn['to_user'])).data,
                'amount': txn['amount']
            })
        return Response(result)


class SettleView(generics.CreateAPIView):
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        group = get_object_or_404(Group, id=self.kwargs['group_id'])
        serializer.save(group=group)


class UserSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_groups = Group.objects.filter(members__user=request.user).distinct()
        total_owed_to_me = 0
        total_i_owe = 0

        for group in user_groups:
            balances = calculate_net_balances(group)
            my_balance = balances.get(request.user.id, 0)
            if my_balance > 0:
                total_owed_to_me += my_balance
            else:
                total_i_owe += abs(my_balance)

        return Response({
            'total_owed_to_me': round(total_owed_to_me, 2),
            'total_i_owe': round(total_i_owe, 2),
            'net': round(total_owed_to_me - total_i_owe, 2)
        })