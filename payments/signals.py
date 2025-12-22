"""
FILE LOCATION: payments/signals.py

FIXED: Signal handlers for payments app - WITH NOTIFICATIONS INTEGRATED!

CRITICAL: This connects payments to rides!
When ride completes → automatic payment processing + ride status update!

IMPROVEMENTS:
- Added ride.payment_status update after successful payment
- Better error logging
- Notification integration ready
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)



@receiver(post_save, sender='rides.Ride')
def process_ride_payment(sender, instance, created, **kwargs):
    """
    AUTO-PROCESS PAYMENT when ride is completed!
    Handles both CASH and WALLET payments.
    """
    # Only process when ride is completed
    if instance.status != 'completed':
        return
    
    # Skip if already processed
    if instance.payment_status == 'paid':
        return
    
    logger.info(f"💳 Processing payment for Ride #{instance.id} - Method: {instance.payment_method}")
    
    # ✅ CASH PAYMENT - Just mark as paid (driver collected)
    if instance.payment_method == 'cash':
        try:
            instance.payment_status = 'paid'
            instance.save(update_fields=['payment_status'])
            logger.info(f"[PAID] Cash payment recorded for ride #{instance.id}")
            return
        except Exception as e:
            logger.error(f"❌ Failed to record cash payment for ride #{instance.id}: {str(e)}")
            return
    
    # ✅ WALLET PAYMENT - Deduct from wallet
    if instance.payment_method == 'wallet':
        from payments.models import Transaction
        
        # Check if already paid
        existing = Transaction.objects.filter(
            ride=instance,
            transaction_type='ride_payment',
            status='completed'
        ).exists()
        
        if existing:
            logger.info(f"⏭️ Payment already processed for Ride #{instance.id}")
            return
        
        # Import here to avoid circular imports
        from payments.services import process_ride_payment_service
        
        try:
            # Process wallet payment
            rider_txn, driver_txn = process_ride_payment_service(instance)
            
            # Update ride payment status
            instance.payment_status = 'paid'
            instance.save(update_fields=['payment_status'])
            
            logger.info(f"✅ Wallet payment processed for Ride #{instance.id}")
            logger.info(f"   Rider paid: ₦{rider_txn.amount}")
            logger.info(f"   Driver earned: ₦{driver_txn.amount}")
            logger.info(f"   Commission: ₦{driver_txn.commission_amount}")
            
        except ValueError as e:
            # Insufficient balance
            instance.payment_status = 'failed'
            instance.save(update_fields=['payment_status'])
            logger.error(f"❌ Wallet payment failed for Ride #{instance.id}: {str(e)}")
            
        except Exception as e:
            instance.payment_status = 'failed'
            instance.save(update_fields=['payment_status'])
            logger.error(f"❌ Payment processing error for Ride #{instance.id}: {str(e)}", exc_info=True)


@receiver(post_save, sender='payments.Transaction')
def transaction_completed_handler(sender, instance, created, **kwargs):
    """
    Handle transaction completion.
    Notifications handled by notifications app signals.
    
    This is a monitoring/logging handler only.
    """
    if instance.status == 'completed':
        logger.info(f"💰 Transaction completed: {instance.transaction_type} - ₦{instance.amount}")
        logger.info(f"   User: {instance.user.phone_number}")
        logger.info(f"   Reference: {instance.reference}")
        logger.info(f"   Balance: {instance.balance_before} → {instance.balance_after}")


@receiver(post_save, sender='payments.Withdrawal')
def withdrawal_status_handler(sender, instance, **kwargs):
    """
    Handle withdrawal status changes.
    Notifications handled by notifications app signals.
    
    This is a monitoring/logging handler only.
    """
    if instance.status == 'completed':
        logger.info(f"✅ Withdrawal completed: ₦{instance.amount} to {instance.driver.user.phone_number}")
        logger.info(f"   Bank: {instance.bank_name}")
        logger.info(f"   Account: {instance.account_number}")
    
    elif instance.status == 'rejected':
        logger.warning(f"❌ Withdrawal rejected: ₦{instance.amount} for {instance.driver.user.phone_number}")
        logger.warning(f"   Reason: {instance.rejection_reason}")
    
    elif instance.status == 'processing':
        logger.info(f"⏳ Withdrawal processing: ₦{instance.amount} for {instance.driver.user.phone_number}")