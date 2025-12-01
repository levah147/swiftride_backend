"""
FILE LOCATION: payments/views.py

Complete Payment Views with Paystack Integration
Includes: Wallet, Transactions, Deposits, Withdrawals, Cards, Webhooks
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from decimal import Decimal
import json
import logging

from .models import Wallet, Transaction, Withdrawal, PaymentCard
from .serializers import (
    WalletSerializer,
    TransactionSerializer,
    WithdrawalSerializer,
    PaymentCardSerializer,
)
from .permissions import IsDriver
from .utils import (
    PaystackClient,
    generate_transaction_reference,
    kobo_to_naira,
    naira_to_kobo,
    validate_nigerian_account,
    format_currency,
    calculate_commission,
    log_transaction,
    log_payment_error,
)

logger = logging.getLogger(__name__)


# ==================== WALLET VIEWS ====================

class WalletDetailView(APIView):
    """
    Get wallet details for authenticated user
    
    GET /api/payments/wallet/
    
    Returns:
    {
        "id": 1,
        "balance": "5000.00",
        "user": {...}
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    """
    Get current wallet balance
    
    GET /api/wallet/balance/
    
    Returns:
    {
        "balance": "5000.00",
        "formatted": "₦5,000.00"
    }
    """
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    return Response({
        'balance': str(wallet.balance),
        'formatted': format_currency(wallet.balance)
    }, status=status.HTTP_200_OK)


# ==================== TRANSACTION VIEWS ====================

class TransactionListView(generics.ListAPIView):
    """
    List all transactions for authenticated user
    
    GET /api/payments/transactions/
    Query params:
    - type: Filter by transaction type
    - status: Filter by status
    - page: Page number
    
    Returns paginated transaction list
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(
        user=self.request.user
    ).order_by('-created_at')
    
    # Filter by type (supports both specific types and credit/debit)
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
        # Handle credit/debit filtering
            if transaction_type == 'credit':
                queryset = queryset.filter(
                transaction_type__in=['deposit', 'ride_earning', 'refund', 'bonus']
            )
            elif transaction_type == 'debit':
                queryset = queryset.filter(
                transaction_type__in=['withdrawal', 'ride_payment', 'commission']
            )
            else:
            # Specific transaction type
                queryset = queryset.filter(transaction_type=transaction_type)
    
        # Filter by status
        transaction_status = self.request.query_params.get('status')
        if transaction_status:
            queryset = queryset.filter(status=transaction_status)
        
        return queryset

class TransactionDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific transaction
    
    GET /api/payments/transactions/<id>/
    
    Returns complete transaction details including metadata
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_transactions(request):
    """
    Get wallet transactions with pagination
    
    GET /api/wallet/transactions/
    Query params:
    - transaction_type: 'credit', 'debit', or null for all
    - page: Page number
    - page_size: Items per page (default 20)
    
    Returns:
    {
        "results": [...],
        "count": 100,
        "next": "...",
        "previous": "..."
    }
    """
    # Get query params
    transaction_type = request.query_params.get('transaction_type')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    
    # Base queryset
    queryset = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Filter by type
    if transaction_type == 'credit':
        queryset = queryset.filter(
            transaction_type__in=['deposit', 'ride_earning', 'refund']
        )
    elif transaction_type == 'debit':
        queryset = queryset.filter(
            transaction_type__in=['withdrawal', 'ride_payment', 'commission']
        )
    
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    
    total_count = queryset.count()
    transactions = queryset[start:end]
    
    # Serialize
    serializer = TransactionSerializer(transactions, many=True)
    
    return Response({
        'results': serializer.data,
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'has_next': end < total_count,
        'has_previous': page > 1,
    }, status=status.HTTP_200_OK)


# ==================== LEGACY DEPOSIT (Keep for backward compatibility) ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_funds(request):
    """
    Legacy deposit endpoint (Mock - for testing only)
    Use /deposit/initialize/ for real Paystack payments
    
    POST /api/payments/deposit/
    {
        "amount": 1000.00,
        "payment_method": "card"
    }
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_method = request.data.get('payment_method', 'card')
        
        if amount <= 0:
            return Response({
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Create transaction
        with db_transaction.atomic():
            balance_before = wallet.balance
            wallet.add_funds(amount)
            balance_after = wallet.balance
            
            reference = generate_transaction_reference('DEP')
            
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                payment_method=payment_method,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=f'Mock deposit via {payment_method}',
                status='completed',
                completed_at=timezone.now()
            )
            
            log_transaction('deposit', amount, request.user.id, 'success', reference)
        
        return Response({
            'message': 'Deposit successful',
            'transaction': TransactionSerializer(transaction_obj).data,
            'new_balance': str(wallet.balance)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Deposit error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== PAYSTACK PAYMENT INITIALIZATION ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_payment(request):
    """
    Initialize Paystack payment
    
    POST /api/payments/deposit/initialize/
    {
        "amount": 1000.00,
        "payment_method": "card" | "bank_transfer" | "ussd"
    }
    
    Returns:
    {
        "success": true,
        "authorization_url": "https://checkout.paystack.com/...",
        "reference": "DEP-XXX",
        "access_code": "xxx",
        "amount": "1000.00",
        "transaction_id": 123
    }
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_method = request.data.get('payment_method', 'card')
        
        # Validation
        if amount < Decimal('100.00'):
            return Response({
                'error': 'Minimum deposit is ₦100.00'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if amount > Decimal('500000.00'):
            return Response({
                'error': 'Maximum deposit is ₦500,000.00'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate reference
        reference = generate_transaction_reference('DEP')
        
        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Create pending transaction
        transaction_obj = Transaction.objects.create(
            user=request.user,
            transaction_type='deposit',
            payment_method=payment_method,
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            reference=reference,
            description=f'Wallet deposit via {payment_method}',
            status='pending',
            metadata={
                'payment_gateway': 'paystack',
                'payment_method': payment_method
            }
        )
        
        # Initialize with Paystack
        client = PaystackClient()
        
        # Get email
        email = request.user.email or f"{request.user.phone_number}@swiftride.com"
        
        # Set channels
        channels = []
        if payment_method == 'card':
            channels = ['card']
        elif payment_method == 'bank_transfer':
            channels = ['bank_transfer', 'bank']
        elif payment_method == 'ussd':
            channels = ['ussd']
        else:
            channels = ['card', 'bank', 'ussd', 'bank_transfer']
        
        result = client.initialize_transaction(
            email=email,
            amount=amount,
            reference=reference,
            channels=channels,
            metadata={
                'user_id': request.user.id,
                'phone_number': request.user.phone_number,
                'transaction_id': transaction_obj.id
            }
        )
        
        logger.info(f"✅ Payment initialized: {reference} - ₦{amount}")
        
        return Response({
            'success': True,
            'authorization_url': result['authorization_url'],
            'access_code': result['access_code'],
            'reference': reference,
            'amount': str(amount),
            'transaction_id': transaction_obj.id
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Payment initialization error: {str(e)}")
        log_payment_error('initialization', request.user.id, amount, str(e))
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== PAYSTACK PAYMENT VERIFICATION ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Verify Paystack payment
    
    GET /api/payments/deposit/verify/?reference=DEP-XXX
    
    Returns:
    {
        "success": true,
        "message": "Payment verified",
        "transaction": {...},
        "wallet": {"balance": "5000.00"}
    }
    """
    reference = request.query_params.get('reference')
    
    if not reference:
        return Response({
            'error': 'Reference is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get transaction
        transaction_obj = Transaction.objects.get(
            reference=reference,
            user=request.user
        )
        
        # If already completed
        if transaction_obj.status == 'completed':
            wallet = request.user.wallet
            return Response({
                'success': True,
                'message': 'Already verified',
                'transaction': TransactionSerializer(transaction_obj).data,
                'wallet': {'balance': str(wallet.balance)}
            }, status=status.HTTP_200_OK)
        
        # Verify with Paystack
        client = PaystackClient()
        paystack_data = client.verify_transaction(reference)
        
        # Check status
        if paystack_data['status'] != 'success':
            transaction_obj.status = 'failed'
            transaction_obj.save()
            
            log_transaction('deposit_verify', transaction_obj.amount, 
                          request.user.id, 'failed', reference)
            
            return Response({
                'error': 'Payment failed',
                'status': paystack_data['status']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Payment successful - credit wallet
        with db_transaction.atomic():
            wallet = request.user.wallet
            amount_paid = kobo_to_naira(paystack_data['amount'])
            
            # Update transaction
            transaction_obj.balance_after = wallet.balance + amount_paid
            transaction_obj.status = 'completed'
            transaction_obj.completed_at = timezone.now()
            transaction_obj.metadata.update({
                'paystack_reference': paystack_data.get('reference'),
                'channel': paystack_data.get('channel'),
                'paid_at': paystack_data.get('paid_at')
            })
            transaction_obj.save()
            
            # Credit wallet
            wallet.add_funds(amount_paid)
            
            log_transaction('deposit_verify', amount_paid, request.user.id, 
                          'success', reference, channel=paystack_data.get('channel'))
            
            logger.info(f"✅ Payment verified: {reference} - ₦{amount_paid}")
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully',
            'transaction': TransactionSerializer(transaction_obj).data,
            'wallet': {'balance': str(wallet.balance)}
        }, status=status.HTTP_200_OK)
    
    except Transaction.DoesNotExist:
        return Response({
            'error': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        log_payment_error('verification', request.user.id, Decimal('0'), str(e), 
                         reference=reference)
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# TO BE CONTINUED IN PART 2...

"""
FILE LOCATION: payments/views.py - PART 2

CONTINUE FROM PART 1 - Add this code after the verify_payment function
"""

# ==================== BANK OPERATIONS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_nigerian_banks(request):
    """
    Get list of Nigerian banks from Paystack
    
    GET /api/payments/banks/
    
    Returns:
    {
        "success": true,
        "banks": [
            {"name": "Access Bank", "code": "044", "active": true},
            ...
        ],
        "count": 25
    }
    """
    try:
        client = PaystackClient()
        banks = client.list_banks()
        
        # Filter active banks
        active_banks = [
            {
                'name': bank['name'],
                'code': bank['code'],
                'active': bank.get('active', True)
            }
            for bank in banks
            if bank.get('active', True)
        ]
        
        return Response({
            'success': True,
            'banks': active_banks,
            'count': len(active_banks)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error fetching banks: {str(e)}")
        return Response({
            'error': 'Failed to fetch banks'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_bank_account(request):
    """
    Validate Nigerian bank account
    
    POST /api/payments/banks/validate/
    {
        "account_number": "0123456789",
        "bank_code": "044"
    }
    
    Returns:
    {
        "valid": true,
        "account_name": "JOHN DOE",
        "account_number": "0123456789",
        "bank_code": "044"
    }
    """
    account_number = request.data.get('account_number', '').strip()
    bank_code = request.data.get('bank_code', '').strip()
    
    if not account_number or not bank_code:
        return Response({
            'error': 'Account number and bank code required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    is_valid, account_name, error = validate_nigerian_account(
        account_number, 
        bank_code
    )
    
    if is_valid:
        return Response({
            'valid': True,
            'account_name': account_name,
            'account_number': account_number,
            'bank_code': bank_code
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'valid': False,
            'error': error or 'Invalid account'
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== WITHDRAWALS ====================

class WithdrawalListCreateView(generics.ListCreateAPIView):
    """
    List withdrawals or create withdrawal request (Legacy)
    
    GET /api/payments/withdrawals/
    POST /api/payments/withdrawals/
    
    Note: Use /withdrawals/request/ for Paystack withdrawals
    """
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated, IsDriver]
    
    def get_queryset(self):
        return Withdrawal.objects.filter(
            driver=self.request.user.driver_profile
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(driver=self.request.user.driver_profile)


class WithdrawalDetailView(generics.RetrieveAPIView):
    """
    Get withdrawal details
    
    GET /api/payments/withdrawals/{id}/
    """
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated, IsDriver]
    
    def get_queryset(self):
        return Withdrawal.objects.filter(
            driver=self.request.user.driver_profile
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDriver])
def request_withdrawal_paystack(request):
    """
    Request withdrawal with Paystack (Drivers only)
    
    POST /api/payments/withdrawals/request/
    {
        "amount": 5000.00,
        "bank_code": "044",
        "account_number": "0123456789",
        "account_name": "JOHN DOE"
    }
    
    Returns:
    {
        "success": true,
        "withdrawal_id": 123,
        "reference": "WD-XXX",
        "status": "processing",
        "amount": "5000.00"
    }
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        bank_code = request.data.get('bank_code', '').strip()
        account_number = request.data.get('account_number', '').strip()
        account_name = request.data.get('account_name', '').strip()
        
        # Validation
        if amount < Decimal('100.00'):
            return Response({
                'error': 'Minimum withdrawal is ₦100.00'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not all([bank_code, account_number, account_name]):
            return Response({
                'error': 'All bank details required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        driver = request.user.driver_profile
        wallet = request.user.wallet
        
        # Check balance
        if wallet.balance < amount:
            return Response({
                'error': f'Insufficient balance. Available: ₦{wallet.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify account
        client = PaystackClient()
        
        try:
            account_info = client.resolve_account_number(account_number, bank_code)
            logger.info(f"Account verified: {account_info['account_name']}")
        except Exception:
            return Response({
                'error': 'Could not verify bank account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create recipient
        try:
            recipient = client.create_transfer_recipient(
                name=account_name,
                account_number=account_number,
                bank_code=bank_code,
                metadata={'user_id': request.user.id, 'driver_id': driver.id}
            )
            recipient_code = recipient['recipient_code']
        except Exception as e:
            logger.error(f"Failed to create recipient: {str(e)}")
            return Response({
                'error': 'Failed to register bank account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process withdrawal
        with db_transaction.atomic():
            # Deduct from wallet
            balance_before = wallet.balance
            wallet.deduct_funds(amount)
            balance_after = wallet.balance
            
            # Create transaction
            reference = generate_transaction_reference('WD')
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='withdrawal',
                payment_method='bank_transfer',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=f'Withdrawal to {account_name}',
                status='pending',
                metadata={
                    'recipient_code': recipient_code,
                    'bank_code': bank_code,
                    'account_number': account_number,
                    'account_name': account_name
                }
            )
            
            # Create withdrawal
            bank_name = recipient.get('bank_name', 'Bank')
            withdrawal = Withdrawal.objects.create(
                driver=driver,
                amount=amount,
                bank_name=bank_name,
                account_number=account_number,
                account_name=account_name,
                status='processing',
                transaction=transaction_obj
            )
            
            # Initiate transfer
            try:
                transfer = client.initiate_transfer(
                    amount=amount,
                    recipient_code=recipient_code,
                    reason=f'Withdrawal for driver {driver.id}',
                    reference=reference,
                    metadata={'withdrawal_id': withdrawal.id}
                )
                
                transaction_obj.metadata['transfer_code'] = transfer.get('transfer_code')
                transaction_obj.save()
                
                log_transaction('withdrawal', amount, request.user.id, 
                              'processing', reference)
                
                logger.info(f"✅ Withdrawal initiated: {reference} - ₦{amount}")
                
                return Response({
                    'success': True,
                    'withdrawal_id': withdrawal.id,
                    'reference': reference,
                    'amount': str(amount),
                    'status': 'processing',
                    'estimated_time': '24 hours'
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                # Refund on failure
                wallet.add_funds(amount)
                transaction_obj.status = 'failed'
                transaction_obj.save()
                withdrawal.status = 'rejected'
                withdrawal.rejection_reason = str(e)
                withdrawal.save()
                
                log_payment_error('withdrawal', request.user.id, amount, str(e))
                
                return Response({
                    'error': 'Transfer failed. Funds returned to wallet.'
                }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Withdrawal error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== WALLET TOP-UP & WITHDRAWAL (Alternative endpoints) ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_top_up(request):
    """
    Mock wallet top-up for testing
    
    POST /api/wallet/top-up/
    {
        "amount": 1000.00,
        "description": "Top up"
    }
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', 'Wallet top-up')
        
        if amount <= 0:
            return Response({
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        with db_transaction.atomic():
            balance_before = wallet.balance
            wallet.add_funds(amount)
            balance_after = wallet.balance
            
            reference = generate_transaction_reference('TOP')
            
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                payment_method='wallet',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=description,
                status='completed',
                completed_at=timezone.now()
            )
        
        return Response({
            'success': True,
            'message': 'Top-up successful',
            'transaction': TransactionSerializer(transaction_obj).data,
            'new_balance': str(wallet.balance)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_withdraw(request):
    """
    Mock wallet withdrawal for testing
    
    POST /api/wallet/withdraw/
    {
        "amount": 1000.00,
        "description": "Withdrawal"
    }
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', 'Withdrawal')
        
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        if wallet.balance < amount:
            return Response({
                'error': 'Insufficient balance'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            balance_before = wallet.balance
            wallet.deduct_funds(amount)
            balance_after = wallet.balance
            
            reference = generate_transaction_reference('WTH')
            
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='withdrawal',
                payment_method='wallet',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=description,
                status='completed',
                completed_at=timezone.now()
            )
        
        return Response({
            'success': True,
            'message': 'Withdrawal successful',
            'transaction': TransactionSerializer(transaction_obj).data,
            'new_balance': str(wallet.balance)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== PAYMENT CARDS ====================

class PaymentCardListCreateView(generics.ListCreateAPIView):
    """
    List payment cards or add new card
    
    GET /api/payments/cards/
    POST /api/payments/cards/
    """
    serializer_class = PaymentCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentCard.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-is_default', '-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentCardDetailView(generics.RetrieveDestroyAPIView):
    """
    Get or delete payment card
    
    GET /api/payments/cards/{id}/
    DELETE /api/payments/cards/{id}/
    """
    serializer_class = PaymentCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentCard.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_card(request, pk):
    """
    Set card as default payment method
    
    POST /api/payments/cards/{id}/set-default/
    """
    try:
        card = PaymentCard.objects.get(
            pk=pk,
            user=request.user,
            is_active=True
        )
        
        # Unset other default cards
        PaymentCard.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        # Set this card as default
        card.is_default = True
        card.save()
        
        return Response({
            'message': 'Default card updated',
            'card': PaymentCardSerializer(card).data
        }, status=status.HTTP_200_OK)
    
    except PaymentCard.DoesNotExist:
        return Response({
            'error': 'Card not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== RIDE PAYMENTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_ride_payment(request, ride_id):
    """
    Process payment for completed ride
    
    POST /api/payments/rides/{ride_id}/pay/
    {
        "payment_method": "wallet"
    }
    
    Returns:
    {
        "success": true,
        "message": "Payment successful",
        "transaction": {...}
    }
    """
    try:
        from rides.models import Ride
        
        # Get ride
        ride = Ride.objects.get(pk=ride_id, rider=request.user)
        
        if ride.status != 'completed':
            return Response({
                'error': 'Ride must be completed before payment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if ride.payment_status == 'paid':
            return Response({
                'error': 'Ride already paid'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = request.data.get('payment_method', 'wallet')
        amount = ride.final_fare or ride.estimated_fare
        
        # Get wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        if wallet.balance < amount:
            return Response({
                'error': f'Insufficient balance. Required: ₦{amount}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process payment
        with db_transaction.atomic():
            # Deduct from rider wallet
            balance_before = wallet.balance
            wallet.deduct_funds(amount)
            balance_after = wallet.balance
            
            reference = generate_transaction_reference('RIDE')
            
            # Create rider transaction
            rider_transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='ride_payment',
                payment_method=payment_method,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=f'Payment for ride #{ride.id}',
                status='completed',
                completed_at=timezone.now(),
                metadata={'ride_id': ride.id}
            )
            
            # Calculate driver earnings and commission
            commission_amount = calculate_commission(amount)
            driver_earnings = amount - commission_amount
            
            # Credit driver wallet
            driver_wallet, _ = Wallet.objects.get_or_create(user=ride.driver.user)
            driver_balance_before = driver_wallet.balance
            driver_wallet.add_funds(driver_earnings)
            driver_balance_after = driver_wallet.balance
            
            # Create driver transaction
            Transaction.objects.create(
                user=ride.driver.user,
                transaction_type='ride_earning',
                payment_method=payment_method,
                amount=driver_earnings,
                balance_before=driver_balance_before,
                balance_after=driver_balance_after,
                reference=reference,
                description=f'Earnings from ride #{ride.id}',
                status='completed',
                completed_at=timezone.now(),
                metadata={
                    'ride_id': ride.id,
                    'total_fare': str(amount),
                    'commission': str(commission_amount)
                }
            )
            
            # Update ride payment status
            ride.payment_status = 'paid'
            ride.save()
            
            log_transaction('ride_payment', amount, request.user.id, 
                          'success', reference, ride_id=ride.id)
        
        return Response({
            'success': True,
            'message': 'Payment successful',
            'transaction': TransactionSerializer(rider_transaction).data,
            'driver_earnings': str(driver_earnings),
            'commission': str(commission_amount)
        }, status=status.HTTP_200_OK)
    
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Ride payment error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== PAYSTACK WEBHOOK ====================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Handle Paystack webhook events
    
    POST /api/payments/webhooks/paystack/
    
    Events:
    - charge.success: Payment successful
    - transfer.success: Withdrawal successful
    - transfer.failed: Withdrawal failed
    - transfer.reversed: Withdrawal reversed
    """
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    
    if not signature:
        logger.warning("⚠️ Webhook received without signature")
        return HttpResponse('No signature', status=400)
    
    payload = request.body
    
    if not PaystackClient.verify_webhook_signature(payload, signature):
        logger.warning("⚠️ Invalid webhook signature")
        return HttpResponse('Invalid signature', status=400)
    
    try:
        event_data = json.loads(payload.decode('utf-8'))
        event_type = event_data.get('event')
        data = event_data.get('data', {})
        
        logger.info(f"📥 Webhook received: {event_type}")
        
        if event_type == 'charge.success':
            handle_charge_success(data)
        elif event_type == 'transfer.success':
            handle_transfer_success(data)
        elif event_type == 'transfer.failed':
            handle_transfer_failed(data)
        elif event_type == 'transfer.reversed':
            handle_transfer_reversed(data)
        else:
            logger.info(f"ℹ️ Unhandled event: {event_type}")
        
        return HttpResponse('Webhook processed', status=200)
    
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}")
        return HttpResponse('Error processing webhook', status=500)


def handle_charge_success(data: dict):
    """Handle successful payment webhook"""
    reference = data.get('reference')
    amount_kobo = data.get('amount', 0)
    amount = kobo_to_naira(amount_kobo)
    
    try:
        transaction_obj = Transaction.objects.get(reference=reference)
        
        if transaction_obj.status == 'completed':
            logger.info(f"ℹ️ Transaction already completed: {reference}")
            return
        
        with db_transaction.atomic():
            wallet = transaction_obj.user.wallet
            
            transaction_obj.balance_after = wallet.balance + amount
            transaction_obj.status = 'completed'
            transaction_obj.completed_at = timezone.now()
            transaction_obj.metadata.update({
                'webhook_received': True,
                'channel': data.get('channel'),
                'paid_at': data.get('paid_at')
            })
            transaction_obj.save()
            
            wallet.add_funds(amount)
            
            log_transaction('webhook_charge', amount, transaction_obj.user.id, 
                          'success', reference)
            
            logger.info(f"✅ Webhook credited wallet: {reference} - ₦{amount}")
    
    except Transaction.DoesNotExist:
        logger.warning(f"⚠️ Transaction not found: {reference}")


def handle_transfer_success(data: dict):
    """Handle successful withdrawal webhook"""
    reference = data.get('reference')
    
    try:
        transaction_obj = Transaction.objects.get(reference=reference)
        withdrawal = transaction_obj.withdrawal_request
        
        with db_transaction.atomic():
            transaction_obj.status = 'completed'
            transaction_obj.completed_at = timezone.now()
            transaction_obj.metadata.update({
                'webhook_received': True,
                'transfer_status': 'success'
            })
            transaction_obj.save()
            
            withdrawal.status = 'completed'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            log_transaction('webhook_transfer', transaction_obj.amount, 
                          transaction_obj.user.id, 'success', reference)
            
            logger.info(f"✅ Webhook: Transfer completed: {reference}")
    
    except Transaction.DoesNotExist:
        logger.warning(f"⚠️ Transaction not found: {reference}")


def handle_transfer_failed(data: dict):
    """Handle failed withdrawal webhook"""
    reference = data.get('reference')
    
    try:
        transaction_obj = Transaction.objects.get(reference=reference)
        withdrawal = transaction_obj.withdrawal_request
        wallet = transaction_obj.user.wallet
        
        with db_transaction.atomic():
            # Refund wallet
            wallet.add_funds(transaction_obj.amount)
            
            transaction_obj.status = 'failed'
            transaction_obj.metadata.update({
                'webhook_received': True,
                'transfer_status': 'failed',
                'failure_reason': data.get('message')
            })
            transaction_obj.save()
            
            withdrawal.status = 'rejected'
            withdrawal.rejection_reason = f"Transfer failed: {data.get('message')}"
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            log_transaction('webhook_transfer_failed', transaction_obj.amount, 
                          transaction_obj.user.id, 'refunded', reference)
            
            logger.info(f"❌ Webhook: Transfer failed, refunded: {reference}")
    
    except Transaction.DoesNotExist:
        logger.warning(f"⚠️ Transaction not found: {reference}")


def handle_transfer_reversed(data: dict):
    """Handle reversed withdrawal (same as failed)"""
    handle_transfer_failed(data)


# ==================== ADMIN VIEWS ====================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_approve_withdrawal(request, pk):
    """
    Admin approve withdrawal request
    
    POST /api/payments/admin/withdrawals/{id}/approve/
    """
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
        
        if withdrawal.status != 'pending':
            return Response({
                'error': f'Cannot approve withdrawal with status: {withdrawal.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        withdrawal.status = 'approved'
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        # Update transaction
        if withdrawal.transaction:
            withdrawal.transaction.status = 'completed'
            withdrawal.transaction.completed_at = timezone.now()
            withdrawal.transaction.save()
        
        return Response({
            'message': 'Withdrawal approved',
            'withdrawal': WithdrawalSerializer(withdrawal).data
        }, status=status.HTTP_200_OK)
    
    except Withdrawal.DoesNotExist:
        return Response({
            'error': 'Withdrawal not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_reject_withdrawal(request, pk):
    """
    Admin reject withdrawal request
    
    POST /api/payments/admin/withdrawals/{id}/reject/
    {
        "reason": "Invalid account details"
    }
    """
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
        reason = request.data.get('reason', 'No reason provided')
        
        if withdrawal.status != 'pending':
            return Response({
                'error': f'Cannot reject withdrawal with status: {withdrawal.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            # Refund wallet
            wallet = withdrawal.driver.user.wallet
            wallet.add_funds(withdrawal.amount)
            
            # Update withdrawal
            withdrawal.status = 'rejected'
            withdrawal.rejection_reason = reason
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            # Update transaction
            if withdrawal.transaction:
                withdrawal.transaction.status = 'failed'
                withdrawal.transaction.save()
        
        return Response({
            'message': 'Withdrawal rejected',
            'withdrawal': WithdrawalSerializer(withdrawal).data
        }, status=status.HTTP_200_OK)
    
    except Withdrawal.DoesNotExist:
        return Response({
            'error': 'Withdrawal not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== END OF VIEWS ==================== 

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDriver])
def quick_withdrawal(request):
    """
    Quick withdrawal for drivers using their preferred bank account
    
    POST /api/payments/withdrawals/quick/
    {
        "amount": 5000.00
    }
    
    Automatically retrieves driver's preferred bank account from most recent withdrawal.
    If driver has no previous withdrawal, returns error.
    """
    try:
        amount = Decimal(str(request.data.get('amount', 0)))
        
        # Validation
        if amount <= 0:
            return Response({
                'error': 'Amount must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if amount < Decimal('100.00'):
            return Response({
                'error': 'Minimum withdrawal is ₦100.00'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get driver
        driver = request.user.driver_profile
        if not driver:
            return Response({
                'error': 'Only drivers can make withdrawals'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get wallet
        wallet = request.user.wallet
        
        # Check balance
        if wallet.balance < amount:
            return Response({
                'error': f'Insufficient balance. Current: ₦{wallet.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get driver's preferred bank account from most recent withdrawal
        recent_withdrawal = Withdrawal.objects.filter(
            driver=driver
        ).order_by('-created_at').first()
        
        if not recent_withdrawal:
            return Response({
                'error': 'Please make your first withdrawal manually to set preferred bank account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use bank details from most recent withdrawal
        bank_name = recent_withdrawal.bank_name
        account_number = recent_withdrawal.account_number
        account_name = recent_withdrawal.account_name
        
        # ✅ Correct
        logger.info(f'🏦 Processing quick withdrawal: ₦{amount} to {account_number}')
        
        # Create withdrawal request using existing logic
        with db_transaction.atomic():
            # Deduct from wallet
            balance_before = wallet.balance
            wallet.deduct_funds(amount)
            balance_after = wallet.balance
            
            # Create transaction
            reference = generate_transaction_reference('WTH')
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='withdrawal',
                payment_method='bank_transfer',
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                status='pending',
                description=f'Driver withdrawal to {account_name}'
            )
            
            # Create withdrawal
            withdrawal = Withdrawal.objects.create(
                driver=driver,
                amount=amount,
                bank_name=bank_name,
                account_number=account_number,
                account_name=account_name,
                status='pending',
                transaction=transaction_obj
            )
            
            log_transaction('withdrawal', amount, request.user.id, 'pending', reference)
            logger.info(f'✅ Withdrawal created: ₦{amount}')
        
        return Response({
            'message': 'Withdrawal request created successfully',
            'withdrawal': WithdrawalSerializer(withdrawal).data,
            'new_balance': str(wallet.balance)
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"❌ Quick withdrawal error: {str(e)}")
        return Response({
            'error': f'Withdrawal failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)