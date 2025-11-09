#   views.py for payments app



from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
import uuid

from .models import Wallet, Transaction, PaymentCard, Withdrawal
from .serializers import (
    WalletSerializer, TransactionSerializer, DepositSerializer,
    PaymentCardSerializer, WithdrawalSerializer, WithdrawalCreateSerializer
) 

class WalletDetailView(generics.RetrieveAPIView):
    """Get current user's wallet details"""
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Get or create wallet for user
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class TransactionListView(generics.ListAPIView):
    """List user's transaction history"""
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Filter by transaction type
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_funds(request):
    """Deposit money into wallet"""
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    amount = serializer.validated_data['amount']
    payment_method = serializer.validated_data['payment_method']
    
    try:
        with db_transaction.atomic():
            # Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            
            # Create transaction record
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                payment_method=payment_method,
                amount=amount,
                balance_before=wallet.balance,
                balance_after=wallet.balance + amount,
                reference=f"DEP-{uuid.uuid4().hex[:12].upper()}",
                description=f"Wallet deposit via {payment_method}",
                status='completed'  # In production, would be 'pending' until payment gateway confirms
            )
            
            # Add funds to wallet
            wallet.add_funds(amount)
            transaction.completed_at = timezone.now()
            transaction.save()
            
            return Response({
                'success': True,
                'message': f'Successfully deposited ₦{amount}',
                'transaction': TransactionSerializer(transaction).data,
                'wallet': WalletSerializer(wallet).data
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_ride_payment(request, ride_id):
    """Process payment for a ride"""
    from rides.models import Ride
    
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
    except Ride.DoesNotExist:
        return Response({
            'error': 'Ride not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status != 'completed':
        return Response({
            'error': 'Cannot process payment for incomplete ride'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if already paid
    if Transaction.objects.filter(
        ride=ride, 
        transaction_type='ride_payment',
        status='completed'
    ).exists():
        return Response({
            'error': 'Ride already paid'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with db_transaction.atomic():
            # Get rider's wallet
            rider_wallet, _ = Wallet.objects.get_or_create(user=request.user)
            
            # Check sufficient balance
            if rider_wallet.balance < ride.fare_amount:
                return Response({
                    'error': f'Insufficient balance. Required: ₦{ride.fare_amount}, Available: ₦{rider_wallet.balance}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Deduct from rider
            rider_transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='ride_payment',
                payment_method='wallet',
                amount=ride.fare_amount,
                balance_before=rider_wallet.balance,
                balance_after=rider_wallet.balance - ride.fare_amount,
                reference=f"RIDE-PAY-{uuid.uuid4().hex[:12].upper()}",
                description=f"Payment for Ride #{ride.id}",
                status='completed',
                ride=ride,
                completed_at=timezone.now()
            )
            rider_wallet.deduct_funds(ride.fare_amount)
            
            # Calculate platform commission (e.g., 15%)
            commission_rate = Decimal('0.15')
            commission_amount = ride.fare_amount * commission_rate
            driver_earning = ride.fare_amount - commission_amount
            
            # Credit driver (if assigned)
            if ride.driver:
                driver_wallet, _ = Wallet.objects.get_or_create(user=ride.driver.user)
                
                # Driver earning
                driver_transaction = Transaction.objects.create(
                    user=ride.driver.user,
                    transaction_type='ride_earning',
                    payment_method='wallet',
                    amount=driver_earning,
                    balance_before=driver_wallet.balance,
                    balance_after=driver_wallet.balance + driver_earning,
                    reference=f"RIDE-EARN-{uuid.uuid4().hex[:12].upper()}",
                    description=f"Earning from Ride #{ride.id}",
                    status='completed',
                    ride=ride,
                    completed_at=timezone.now(),
                    metadata={'commission': str(commission_amount)}
                )
                driver_wallet.add_funds(driver_earning)
                
                # Commission transaction (record only)
                Transaction.objects.create(
                    user=ride.driver.user,
                    transaction_type='commission',
                    payment_method='wallet',
                    amount=commission_amount,
                    balance_before=driver_wallet.balance,
                    balance_after=driver_wallet.balance,
                    reference=f"COMM-{uuid.uuid4().hex[:12].upper()}",
                    description=f"Platform commission for Ride #{ride.id}",
                    status='completed',
                    ride=ride,
                    completed_at=timezone.now()
                )
            
            return Response({
                'success': True,
                'message': 'Payment processed successfully',
                'transaction': TransactionSerializer(rider_transaction).data,
                'wallet': WalletSerializer(rider_wallet).data
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== Payment Cards ====================

class PaymentCardListCreateView(generics.ListCreateAPIView):
    """List and add payment cards"""
    serializer_class = PaymentCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentCard.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        # In production, integrate with payment gateway to tokenize card
        # For now, just save the card details
        serializer.save(
            user=self.request.user,
            card_token=f"tok_{uuid.uuid4().hex[:16]}"  # Mock token
        )


class PaymentCardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a payment card"""
    serializer_class = PaymentCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentCard.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_card(request, pk):
    """Set a card as default"""
    try:
        card = PaymentCard.objects.get(pk=pk, user=request.user, is_active=True)
        
        # Unset all other defaults
        PaymentCard.objects.filter(user=request.user).update(is_default=False)
        
        # Set this as default
        card.is_default = True
        card.save()
        
        return Response({
            'success': True,
            'message': 'Default card updated',
            'card': PaymentCardSerializer(card).data
        }, status=status.HTTP_200_OK)
    
    except PaymentCard.DoesNotExist:
        return Response({
            'error': 'Card not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== Driver Withdrawals ====================

class WithdrawalListCreateView(generics.ListCreateAPIView):
    """List and create withdrawal requests (Drivers only)"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WithdrawalCreateSerializer
        return WithdrawalSerializer
    
    def get_queryset(self):
        # Only drivers can withdraw
        if not hasattr(self.request.user, 'driver_profile'):
            return Withdrawal.objects.none()
        
        return Withdrawal.objects.filter(
            driver=self.request.user.driver_profile
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        # Check if user is a driver
        if not hasattr(request.user, 'driver_profile'):
            return Response({
                'error': 'Only drivers can request withdrawals'
            }, status=status.HTTP_403_FORBIDDEN)
        
        driver = request.user.driver_profile
        wallet = request.user.wallet
        
        serializer = WithdrawalCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        
        # Check balance
        if wallet.balance < amount:
            return Response({
                'error': f'Insufficient balance. Available: ₦{wallet.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with db_transaction.atomic():
                # Create withdrawal request
                withdrawal = Withdrawal.objects.create(
                    driver=driver,
                    amount=amount,
                    bank_name=serializer.validated_data['bank_name'],
                    account_number=serializer.validated_data['account_number'],
                    account_name=serializer.validated_data['account_name'],
                    status='pending'
                )
                
                # Create pending transaction
                transaction_obj = Transaction.objects.create(
                    user=request.user,
                    transaction_type='withdrawal',
                    payment_method='bank_transfer',
                    amount=amount,
                    balance_before=wallet.balance,
                    balance_after=wallet.balance - amount,
                    reference=f"WITH-{uuid.uuid4().hex[:12].upper()}",
                    description=f"Withdrawal to {serializer.validated_data['bank_name']}",
                    status='pending'
                )
                
                withdrawal.transaction = transaction_obj
                withdrawal.save()
                
                # Deduct from wallet (held until processed)
                wallet.deduct_funds(amount)
                
                return Response({
                    'success': True,
                    'message': 'Withdrawal request submitted',
                    'withdrawal': WithdrawalSerializer(withdrawal).data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalDetailView(generics.RetrieveAPIView):
    """Get withdrawal details"""
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'driver_profile'):
            return Withdrawal.objects.none()
        
        return Withdrawal.objects.filter(driver=self.request.user.driver_profile)


# ==================== Admin Endpoints ====================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_approve_withdrawal(request, pk):
    """Admin: Approve withdrawal request"""
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
        
        if withdrawal.status != 'pending':
            return Response({
                'error': 'Only pending withdrawals can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            withdrawal.status = 'completed'
            withdrawal.processed_by = request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            # Update transaction
            if withdrawal.transaction:
                withdrawal.transaction.status = 'completed'
                withdrawal.transaction.completed_at = timezone.now()
                withdrawal.transaction.save()
            
            return Response({
                'success': True,
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
    """Admin: Reject withdrawal request"""
    try:
        withdrawal = Withdrawal.objects.get(pk=pk)
        rejection_reason = request.data.get('rejection_reason')
        
        if not rejection_reason:
            return Response({
                'error': 'Rejection reason is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if withdrawal.status != 'pending':
            return Response({
                'error': 'Only pending withdrawals can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            # Refund to wallet
            wallet = withdrawal.driver.user.wallet
            wallet.add_funds(withdrawal.amount)
            
            withdrawal.status = 'rejected'
            withdrawal.rejection_reason = rejection_reason
            withdrawal.processed_by = request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            # Update transaction
            if withdrawal.transaction:
                withdrawal.transaction.status = 'failed'
                withdrawal.transaction.save()
            
            return Response({
                'success': True,
                'message': 'Withdrawal rejected and funds refunded',
                'withdrawal': WithdrawalSerializer(withdrawal).data
            }, status=status.HTTP_200_OK)
    
    except Withdrawal.DoesNotExist:
        return Response({
            'error': 'Withdrawal not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
        

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def process_ride_payment(request, ride_id):
#     """Process payment for a ride with proper commission calculation"""
#     from rides.models import Ride
    
#     try:
#         ride = Ride.objects.select_related(
#             'driver', 'vehicle_type', 'city'
#         ).get(id=ride_id, user=request.user)
#     except Ride.DoesNotExist:
#         return Response({'error': 'Ride not found'}, status=404)
    
#     if ride.status != 'completed':
#         return Response({'error': 'Can only pay for completed rides'}, status=400)
    
#     # Check if already paid
#     if Transaction.objects.filter(
#         ride=ride,
#         transaction_type='ride_payment',
#         status='completed'
#     ).exists():
#         return Response({'error': 'Ride already paid'}, status=400)
    
#     try:
#         with db_transaction.atomic():
#             # Get rider's wallet
#             rider_wallet, _ = Wallet.objects.get_or_create(user=request.user)
            
#             # Check balance
#             if rider_wallet.balance < ride.fare_amount:
#                 return Response({
#                     'error': f'Insufficient balance. Required: ₦{ride.fare_amount}, Available: ₦{rider_wallet.balance}'
#                 }, status=400)
            
#             # Get commission rate from vehicle type
#             commission_rate = ride.vehicle_type.platform_commission_percentage
#             commission_amount = (ride.fare_amount * commission_rate) / 100
#             driver_earning = ride.fare_amount - commission_amount
            
#             # Calculate surge amount (for tracking)
#             if ride.surge_multiplier > 1:
#                 base_total = ride.base_fare + ride.distance_fare + ride.time_fare + ride.fuel_adjustment
#                 surge_amount = ride.fare_amount - base_total
#             else:
#                 surge_amount = 0
            
#             # Deduct from rider
#             rider_transaction = Transaction.objects.create(
#                 user=request.user,
#                 transaction_type='ride_payment',
#                 payment_method='wallet',
#                 amount=ride.fare_amount,
#                 balance_before=rider_wallet.balance,
#                 balance_after=rider_wallet.balance - ride.fare_amount,
#                 reference=f"RIDE-PAY-{uuid.uuid4().hex[:12].upper()}",
#                 description=f"Payment for Ride #{ride.id}",
#                 status='completed',
#                 ride=ride,
#                 completed_at=timezone.now(),
#                 # Breakdown
#                 base_fare=ride.base_fare,
#                 surge_multiplier=ride.surge_multiplier,
#                 surge_amount=surge_amount,
#                 fuel_adjustment=ride.fuel_adjustment,
#                 commission_rate=commission_rate,
#                 commission_amount=commission_amount
#             )
#             rider_wallet.deduct_funds(ride.fare_amount)
            
#             # Credit driver
#             if ride.driver:
#                 driver_wallet, _ = Wallet.objects.get_or_create(user=ride.driver.user)
                
#                 driver_transaction = Transaction.objects.create(
#                     user=ride.driver.user,
#                     transaction_type='ride_earning',
#                     payment_method='wallet',
#                     amount=driver_earning,
#                     balance_before=driver_wallet.balance,
#                     balance_after=driver_wallet.balance + driver_earning,
#                     reference=f"RIDE-EARN-{uuid.uuid4().hex[:12].upper()}",
#                     description=f"Earning from Ride #{ride.id}",
#                     status='completed',
#                     ride=ride,
#                     completed_at=timezone.now(),
#                     base_fare=ride.base_fare,
#                     surge_multiplier=ride.surge_multiplier,
#                     surge_amount=surge_amount,
#                     fuel_adjustment=ride.fuel_adjustment,
#                     commission_rate=commission_rate,
#                     commission_amount=commission_amount,
#                     metadata={
#                         'gross_fare': str(ride.fare_amount),
#                         'commission': str(commission_amount),
#                         'net_earning': str(driver_earning)
#                     }
#                 )
#                 driver_wallet.add_funds(driver_earning)
                
#                 # Update driver earnings
#                 ride.driver.total_earnings += driver_earning
#                 ride.driver.save(update_fields=['total_earnings'])
            
#             return Response({
#                 'success': True,
#                 'message': 'Payment processed successfully',
#                 'transaction': TransactionSerializer(rider_transaction).data,
#                 'breakdown': {
#                     'total_fare': float(ride.fare_amount),
#                     'commission_rate': float(commission_rate),
#                     'commission_amount': float(commission_amount),
#                     'driver_earning': float(driver_earning)
#                 }
#             })
    
#     except Exception as e:
#         return Response({'error': str(e)}, status=400)
    
    
    
    
    