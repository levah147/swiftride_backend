"""
FILE LOCATION: payments/urls.py

Payment API URL Configuration - PRODUCTION READY ✅

FIXED:
- Removed duplicate paths for deposit/initialize and deposit/verify
- Standardized all endpoints under /payments/ prefix
- Added backwards-compatible aliases for legacy endpoints
- Organized endpoints by category

URL Structure:
/api/payments/wallet/                    - Wallet details
/api/payments/wallet/balance/            - Wallet balance (alias)
/api/payments/wallet/transactions/       - Transaction history (alias)
/api/payments/transactions/              - Transaction list
/api/payments/deposit/initialize/        - Initialize Paystack payment
/api/payments/deposit/verify/            - Verify Paystack payment
/api/payments/banks/                     - List Nigerian banks
/api/payments/banks/validate/            - Validate bank account
/api/payments/withdrawals/               - Withdrawal list/create
/api/payments/withdrawals/{id}/          - Withdrawal detail
/api/payments/withdrawals/request/       - Request withdrawal (Paystack)
/api/payments/cards/                     - Payment cards list/create
/api/payments/cards/{id}/                - Payment card detail
/api/payments/cards/{id}/set-default/    - Set default card
/api/payments/webhooks/paystack/         - Paystack webhook
/api/payments/admin/withdrawals/{id}/approve/    - Admin: Approve withdrawal
/api/payments/admin/withdrawals/{id}/reject/     - Admin: Reject withdrawal
/api/payments/rides/{id}/pay/            - Process ride payment (Legacy)
"""
from django.urls import path
from . import views
from .views import (
    initialize_payment,
    verify_payment,
    list_nigerian_banks,
    validate_bank_account,
    request_withdrawal_paystack,
    quick_withdrawal,
    paystack_webhook,
)

app_name = 'payments'

urlpatterns = [
    # ==================== WALLET ====================
    path('wallet/', views.WalletDetailView.as_view(), name='wallet_detail'),
    path('wallet/balance/', views.get_wallet_balance, name='wallet_balance'),  # Backwards-compatible alias
    path('wallet/transactions/', views.get_wallet_transactions, name='wallet_transactions'),  # Backwards-compatible alias
    
    # ==================== TRANSACTIONS ====================
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    
    # ==================== DEPOSITS (Paystack Integration) ====================
    path('deposit/initialize/', initialize_payment, name='initialize_payment'),
    path('deposit/verify/', verify_payment, name='verify_payment'),
    path('deposit/', views.deposit_funds, name='deposit_funds'),  # Legacy endpoint for backward compatibility
    
    # ==================== BANK OPERATIONS ====================
    path('banks/', list_nigerian_banks, name='list_banks'),
    path('banks/validate/', validate_bank_account, name='validate_account'),
    
    # ==================== WITHDRAWALS (Enhanced with Paystack) ====================
    path('withdrawals/', views.WithdrawalListCreateView.as_view(), name='withdrawal_list_create'),
    path('withdrawals/<int:pk>/', views.WithdrawalDetailView.as_view(), name='withdrawal_detail'),
    path('withdrawals/request/', request_withdrawal_paystack, name='request_withdrawal_paystack'),  # ✅ NEW: Paystack integrated
    path('withdrawals/quick/', quick_withdrawal, name='quick_withdrawal'),  # ✅ ADD THIS LINE
    
    # ==================== PAYMENT CARDS ====================
    path('cards/', views.PaymentCardListCreateView.as_view(), name='card_list_create'),
    path('cards/<int:pk>/', views.PaymentCardDetailView.as_view(), name='card_detail'),
    path('cards/<int:pk>/set-default/', views.set_default_card, name='set_default_card'),
    
    # ==================== WEBHOOKS ====================
    path('webhooks/paystack/', paystack_webhook, name='paystack_webhook'),
    
    # ==================== ADMIN ACTIONS ====================
    path('admin/withdrawals/<int:pk>/approve/', views.admin_approve_withdrawal, name='admin_approve_withdrawal'),
    path('admin/withdrawals/<int:pk>/reject/', views.admin_reject_withdrawal, name='admin_reject_withdrawal'),
    
    # ==================== RIDES (Legacy) ====================
    path('rides/<int:ride_id>/pay/', views.process_ride_payment, name='process_ride_payment'),
]

"""
PAYSTACK WEBHOOK CONFIGURATION:

1. Add this URL to Paystack Dashboard:
   Production: https://yourdomain.com/api/payments/webhooks/paystack/
   Development: https://yourdomain.local/api/payments/webhooks/paystack/

2. Make sure to:
   - Use HTTPS (Paystack requires it)
   - Add Paystack secret key to Django settings
   - Test webhook with Paystack test environment first
   
3. Webhook Security:
   - Always verify Paystack signature in webhook handler
   - Never trust webhook data without verification
   - Log all webhook events for audit trail

4. Supported Events:
   - charge.success: Payment completed
   - transfer.success: Withdrawal completed
   - transfer.failed: Withdrawal failed
   - transfer.reversed: Withdrawal reversed
"""