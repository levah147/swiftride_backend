

"""
FILE LOCATION: payments/services.py

Payment processing business logic.
"""
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
import uuid
from .models import Wallet, Transaction


def process_ride_payment_service(ride):
    """
    Process payment for completed ride.
    
    Flow:
    1. Rider pays fare
    2. Platform takes commission
    3. Driver gets earnings
    """
    from pricing.utils import calculate_platform_commission
    
    with db_transaction.atomic():
        rider = ride.user
        driver = ride.driver
        total_fare = ride.fare_amount
        
        # Get or create wallets
        rider_wallet, _ = Wallet.objects.get_or_create(user=rider)
        driver_wallet, _ = Wallet.objects.get_or_create(user=driver.user)
        
        # Calculate commission
        commission, driver_earnings = calculate_platform_commission(total_fare, 20.0)
        
        # 1. Deduct from rider
        rider_balance_before = rider_wallet.balance
        rider_wallet.deduct_funds(total_fare)
        rider_balance_after = rider_wallet.balance
        
        # Create rider payment transaction
        rider_txn = Transaction.objects.create(
            user=rider,
            transaction_type='ride_payment',
            payment_method='wallet',
            amount=total_fare,
            balance_before=rider_balance_before,
            balance_after=rider_balance_after,
            status='completed',
            reference=f"RIDE-{ride.id}-{uuid.uuid4().hex[:8].upper()}",
            description=f"Payment for ride #{ride.id}",
            ride=ride,
            completed_at=timezone.now()
        )
        
        # 2. Add to driver (earnings after commission)
        driver_balance_before = driver_wallet.balance
        driver_wallet.add_funds(driver_earnings)
        driver_balance_after = driver_wallet.balance
        
        # Create driver earning transaction
        driver_txn = Transaction.objects.create(
            user=driver.user,
            transaction_type='ride_earning',
            payment_method='wallet',
            amount=driver_earnings,
            balance_before=driver_balance_before,
            balance_after=driver_balance_after,
            status='completed',
            reference=f"EARN-{ride.id}-{uuid.uuid4().hex[:8].upper()}",
            description=f"Earnings from ride #{ride.id}",
            ride=ride,
            commission_amount=commission,
            completed_at=timezone.now()
        )
        
        return rider_txn, driver_txn


def deposit_to_wallet(user, amount, payment_method='card'):
    """Deposit money to user wallet"""
    with db_transaction.atomic():
        wallet, _ = Wallet.objects.get_or_create(user=user)
        
        balance_before = wallet.balance
        wallet.add_funds(amount)
        balance_after = wallet.balance
        
        txn = Transaction.objects.create(
            user=user,
            transaction_type='deposit',
            payment_method=payment_method,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            status='completed',
            reference=f"DEP-{uuid.uuid4().hex[:12].upper()}",
            description=f"Wallet deposit via {payment_method}",
            completed_at=timezone.now()
        )
        
        return txn


def process_withdrawal(withdrawal):
    """Process driver withdrawal"""
    with db_transaction.atomic():
        driver = withdrawal.driver
        wallet = driver.user.wallet
        
        balance_before = wallet.balance
        wallet.deduct_funds(withdrawal.amount)
        balance_after = wallet.balance
        
        txn = Transaction.objects.create(
            user=driver.user,
            transaction_type='withdrawal',
            payment_method='bank_transfer',
            amount=withdrawal.amount,
            balance_before=balance_before,
            balance_after=balance_after,
            status='completed',
            reference=f"WD-{uuid.uuid4().hex[:12].upper()}",
            description=f"Withdrawal to {withdrawal.bank_name}",
            completed_at=timezone.now()
        )
        
        withdrawal.transaction = txn
        withdrawal.status = 'completed'
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        return txn



