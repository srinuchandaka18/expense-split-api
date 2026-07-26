# expenses/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Groups
    path('groups/', views.GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:group_id>/members/', views.AddMemberView.as_view(), name='add-member'),

    # Expenses
    path('groups/<int:group_id>/expenses/', views.ExpenseListCreateView.as_view(), name='expense-list-create'),

    # Balances
    path('groups/<int:group_id>/balances/', views.GroupBalancesView.as_view(), name='group-balances'),
    path('groups/<int:group_id>/simplify/', views.GroupSimplifyView.as_view(), name='group-simplify'),
    path('groups/<int:group_id>/settle/', views.SettleView.as_view(), name='settle'),

    # User summary
    path('users/summary/', views.UserSummaryView.as_view(), name='user-summary'),
]