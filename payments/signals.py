"""
FILE LOCATION: payments/signals.py
Signal handlers for payments app - WITH NOTIFICATIONS INTEGRATED!

CRITICAL: This connects payments to rides!
When ride completes → automatic payment processing + notifications!
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction as db_transaction
from decimal import Decimal


@receiver(post_save, sender='rides.Ride')
def process_ride_payment(sender, instance, created, **kwargs):
    """
    AUTO-PROCESS PAYMENT when ride is completed!
    Also sends notifications to both rider and driver.
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
            print(f"💳 Processing payment for Ride #{instance.id}")
            
            # Import here to avoid circular imports
            from payments.services import process_ride_payment_service
            
            try:
                process_ride_payment_service(instance)
                print(f"✅ Payment processed for Ride #{instance.id}")
                
                # Notifications are now sent by Transaction signals in notifications app!
                
            except Exception as e:
                print(f"❌ Payment failed for Ride #{instance.id}: {str(e)}")


@receiver(post_save, sender='payments.Transaction')
def transaction_completed_handler(sender, instance, created, **kwargs):
    """
    Handle transaction completion.
    Notifications handled by notifications app signals.
    """
    if instance.status == 'completed':
        print(f"💰 Transaction completed: {instance.transaction_type} - ₦{instance.amount}")


@receiver(post_save, sender='payments.Withdrawal')
def withdrawal_status_handler(sender, instance, **kwargs):
    """
    Handle withdrawal status changes.
    Notifications handled by notifications app signals.
    """
    if instance.status == 'completed':
        print(f"✅ Withdrawal completed: ₦{instance.amount} to {instance.driver.user.phone_number}")
    elif instance.status == 'rejected':
        print(f"❌ Withdrawal rejected: ₦{instance.amount} for {instance.driver.user.phone_number}")
        
# """
# FILE LOCATION: payments/signals.py

# CRITICAL: This connects payments to rides!
# When ride completes → automatic payment processing!
# """
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.db import transaction as db_transaction
# from decimal import Decimal


# @receiver(post_save, sender='rides.Ride')
# def process_ride_payment(sender, instance, created, **kwargs):
#     """
#     AUTO-PROCESS PAYMENT when ride is completed!
#     This is THE critical integration point!
#     """
#     if instance.status == 'completed' and not created:
#         # Check if already paid
#         from payments.models import Transaction
#         existing = Transaction.objects.filter(
#             ride=instance,
#             transaction_type='ride_payment',
#             status='completed'
#         ).exists()
        
#         if not existing:
#             print(f"💳 Processing payment for Ride #{instance.id}")
            
#             # Import here to avoid circular imports
#             from payments.services import process_ride_payment_service
            
#             try:
#                 process_ride_payment_service(instance)
#                 print(f"✅ Payment processed for Ride #{instance.id}")
#             except Exception as e:
#                 print(f"❌ Payment failed for Ride #{instance.id}: {str(e)}")


