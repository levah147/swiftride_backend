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
    FIXED: AUTO-PROCESS PAYMENT when ride is completed!
    
    Also updates ride.payment_status to 'paid' after successful payment.
    Notifications are sent by Transaction signals in notifications app.
    
    Flow:
    1. Ride status changes to 'completed'
    2. Check if already paid
    3. Process payment (rider → platform → driver)
    4. Update ride.payment_status = 'paid'
    5. Notifications sent automatically
    """
    if instance.status == 'completed' and not created:
        # Check if already paid
        from payments.models import Transaction
        existing = Transaction.objects.filter(
            ride=instance,
            transaction_type='ride_payment',
            status='completed'
        ).exists()
        
        if not existing:
            logger.info(f"💳 Processing payment for Ride #{instance.id}")
            
            # Import here to avoid circular imports
            from payments.services import process_ride_payment_service
            
            try:
                # Process payment
                rider_txn, driver_txn = process_ride_payment_service(instance)
                
                # ✅ FIXED: Update ride payment status
                instance.payment_status = 'paid'
                instance.save(update_fields=['payment_status'])
                
                logger.info(f"✅ Payment processed for Ride #{instance.id}")
                logger.info(f"   Rider paid: ₦{rider_txn.amount}")
                logger.info(f"   Driver earned: ₦{driver_txn.amount}")
                logger.info(f"   Commission: ₦{driver_txn.commission_amount}")
                
                # Notifications are now sent by Transaction signals in notifications app!
                
            except Exception as e:
                logger.error(f"❌ Payment failed for Ride #{instance.id}: {str(e)}", exc_info=True)
                
                # Update ride payment status to failed
                instance.payment_status = 'failed'
                instance.save(update_fields=['payment_status'])


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