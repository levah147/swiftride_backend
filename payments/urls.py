from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Wallet
    path('wallet/', views.WalletDetailView.as_view(), name='wallet_detail'),
    path('deposit/', views.deposit_funds, name='deposit_funds'),
    
    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('rides/<int:ride_id>/pay/', views.process_ride_payment, name='process_ride_payment'),
    
    # Payment Cards
    path('cards/', views.PaymentCardListCreateView.as_view(), name='card_list_create'),
    path('cards/<int:pk>/', views.PaymentCardDetailView.as_view(), name='card_detail'),
    path('cards/<int:pk>/set-default/', views.set_default_card, name='set_default_card'),
    
    # Withdrawals (Driver)
    path('withdrawals/', views.WithdrawalListCreateView.as_view(), name='withdrawal_list_create'),
    path('withdrawals/<int:pk>/', views.WithdrawalDetailView.as_view(), name='withdrawal_detail'),
    
    # Admin
    path('admin/withdrawals/<int:pk>/approve/', views.admin_approve_withdrawal, name='admin_approve_withdrawal'),
    path('admin/withdrawals/<int:pk>/reject/', views.admin_reject_withdrawal, name='admin_reject_withdrawal'),
]