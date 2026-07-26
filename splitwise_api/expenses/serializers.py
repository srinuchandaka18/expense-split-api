# expenses/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Group, GroupMember, Expense, ExpenseSplit, Settlement


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'user_id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    members = GroupMemberSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'members', 'created_at']


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExpenseSplit
        fields = ['id', 'user', 'user_id', 'share_amount']


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    paid_by_id = serializers.IntegerField(write_only=True)
    splits = ExpenseSplitSerializer(many=True, required=False)

    class Meta:
        model = Expense
        fields = ['id', 'group', 'paid_by', 'paid_by_id', 'amount',
                  'description', 'split_type', 'splits', 'created_at']
        read_only_fields = ['group']

    def validate(self, data):
        split_type = data.get('split_type', 'equal')
        splits_data = self.initial_data.get('splits', [])

        if split_type == 'exact' and splits_data:
            total = sum(float(s['share_amount']) for s in splits_data)
            if round(total, 2) != round(float(data['amount']), 2):
                raise serializers.ValidationError("Sum of exact shares must equal the total expense amount.")

        if split_type == 'percentage' and splits_data:
            total_pct = sum(float(s['share_amount']) for s in splits_data)
            if round(total_pct, 2) != 100.0:
                raise serializers.ValidationError("Percentage shares must add up to 100.")
        return data

    def create(self, validated_data):
        splits_data = validated_data.pop('splits', [])
        expense = Expense.objects.create(**validated_data)

        if expense.split_type == 'equal':
            members = expense.group.members.all()
            count = members.count()
            if count == 0:
                raise serializers.ValidationError("Group has no members to split with.")
            share = round(float(expense.amount) / count, 2)
            for member in members:
                ExpenseSplit.objects.create(expense=expense, user=member.user, share_amount=share)

        elif expense.split_type == 'exact':
            for split in splits_data:
                ExpenseSplit.objects.create(expense=expense, user_id=split['user_id'], share_amount=split['share_amount'])

        elif expense.split_type == 'percentage':
            for split in splits_data:
                amount = round(float(expense.amount) * float(split['share_amount']) / 100, 2)
                ExpenseSplit.objects.create(expense=expense, user_id=split['user_id'], share_amount=amount)

        return expense


class SettlementSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    from_user_id = serializers.IntegerField(write_only=True)
    to_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Settlement
        fields = ['id', 'group', 'from_user', 'to_user', 'from_user_id', 'to_user_id', 'amount', 'settled_at']