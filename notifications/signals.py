"""
FILE LOCATION: notifications/signals.py

Signal handlers that automatically send notifications when events occur.
This connects notifications to ALL other apps including CHAT!
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .utils import safe_send_notification

User = get_user_model()


@receiver(post_save, sender=User)
def user_created_notification(sender, instance, created, **kwargs):
    """Send welcome notification when user registers"""
    if created:
        safe_send_notification(
            user_id=instance.id,
            notification_type='welcome',
            title='Welcome to SwiftRide! 🎉',
            body='Thank you for joining SwiftRide. Start booking rides now!',
            send_push=True,
            send_sms=False,
            send_email=False
        )


# Import and register signals from other apps
def setup_cross_app_signals():
    """Setup signal handlers for other apps - CALLED FROM apps.py ready() method"""
    
    # DRIVERS APP SIGNALS
    try:
        from drivers.models import Driver
        
        def driver_status_notification(sender, instance, created, **kwargs):
            """Notify driver when application status changes"""
            if not created:
                if instance.status == 'approved':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='driver_approved',
                        title='Application Approved! ✅',
                        body='Congratulations! Your driver application has been approved.',
                        send_push=True,
                        send_sms=True,
                        send_email=True
                    )
                elif instance.status == 'rejected':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='driver_rejected',
                        title='Application Update',
                        body='Your driver application needs review. Please contact support.',
                        send_push=True,
                        send_sms=False
                    )
        
        # Connect signal using post_save.connect (not decorator) so it works when called from ready()
        post_save.connect(driver_status_notification, sender=Driver, weak=False)
        
    except (ImportError, AttributeError) as e:
        # Models might not be available yet, that's OK
        pass
    
    # RIDES APP SIGNALS
    try:
        from rides.models import Ride
        
        def ride_notification(sender, instance, created, **kwargs):
            """Send notifications for ride events"""
            
            # New ride created - notifications handled in rides app
            if created and instance.status == 'pending':
                pass
            
            # Ride accepted
            elif instance.status == 'accepted' and instance.driver and not created:
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_accepted',
                    title='Driver Accepted! 🚗',
                    body=f'{instance.driver.user.get_full_name() or instance.driver.user.phone_number} is coming to pick you up',
                    send_push=True,
                    send_sms=False,
                    data={'ride_id': instance.id}
                )
            
            # Driver arrived
            elif instance.status == 'driver_arrived' and not created:
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='driver_arrived',
                    title='Driver Arrived! 📍',
                    body='Your driver has arrived at the pickup location',
                    send_push=True,
                    send_sms=True,
                    data={'ride_id': instance.id}
                )
            
            # Ride started
            elif instance.status == 'in_progress' and not created:
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_started',
                    title='Ride Started 🚀',
                    body='Your ride has started. Enjoy your trip!',
                    send_push=True,
                    data={'ride_id': instance.id}
                )
            
            # Ride completed
            elif instance.status == 'completed' and not created:
                # Notify rider
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_completed',
                    title='Ride Completed ✅',
                    body='Thank you for riding with SwiftRide!',
                    send_push=True,
                    data={'ride_id': instance.id}
                )
                
                # Notify driver
                if instance.driver:
                    safe_send_notification(
                        user_id=instance.driver.user.id,
                        notification_type='ride_completed',
                        title='Ride Completed ✅',
                        body='Payment has been processed and added to your wallet',
                        send_push=True,
                        data={'ride_id': instance.id}
                    )
            
            # Ride cancelled
            elif instance.status == 'cancelled' and not created:
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_cancelled',
                    title='Ride Cancelled',
                    body='Your ride has been cancelled',
                    send_push=True,
                    data={'ride_id': instance.id}
                )
        
        # Connect signal
        post_save.connect(ride_notification, sender=Ride, weak=False)
        
    except (ImportError, AttributeError) as e:
        pass
    
    # PAYMENTS APP SIGNALS
    try:
        from payments.models import Transaction, Withdrawal
        
        def transaction_notification(sender, instance, created, **kwargs):
            """Notify user about transactions"""
            if instance.status == 'completed':
                
                # Deposit
                if instance.transaction_type == 'deposit':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='wallet_credited',
                        title='Wallet Credited 💰',
                        body=f'₦{instance.amount} has been added to your wallet',
                        send_push=True,
                        send_sms=False,
                        data={'amount': str(instance.amount)}
                    )
                
                # Ride payment
                elif instance.transaction_type == 'ride_payment':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='payment_processed',
                        title='Payment Successful ✅',
                        body=f'₦{instance.amount} has been deducted for your ride',
                        send_push=True,
                        data={'amount': str(instance.amount)}
                    )
                
                # Driver earnings
                elif instance.transaction_type == 'ride_earning':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='earnings_added',
                        title='Earnings Added 💵',
                        body=f'₦{instance.amount} has been added to your wallet',
                        send_push=True,
                        data={'amount': str(instance.amount)}
                    )
        
        def withdrawal_notification(sender, instance, created, **kwargs):
            """Notify driver about withdrawal status"""
            if not created:
                if instance.status == 'completed':
                    safe_send_notification(
                        user_id=instance.driver.user.id,
                        notification_type='withdrawal_approved',
                        title='Withdrawal Approved ✅',
                        body=f'₦{instance.amount} has been sent to your bank account',
                        send_push=True,
                        send_sms=True,
                        data={'amount': str(instance.amount)}
                    )
                elif instance.status == 'rejected':
                    safe_send_notification(
                        user_id=instance.driver.user.id,
                        notification_type='withdrawal_rejected',
                        title='Withdrawal Rejected',
                        body=f'Your withdrawal request was rejected. Reason: {instance.rejection_reason or "Contact support for details"}',
                        send_push=True,
                        send_sms=False
                    )
        
        # Connect signals
        post_save.connect(transaction_notification, sender=Transaction, weak=False)
        post_save.connect(withdrawal_notification, sender=Withdrawal, weak=False)
        
    except (ImportError, AttributeError) as e:
        pass
    
    # VEHICLES APP SIGNALS
    try:
        from vehicles.models import Vehicle
        
        def vehicle_notification(sender, instance, created, **kwargs):
            """Notify driver about vehicle status"""
            if created:
                safe_send_notification(
                    user_id=instance.driver.user.id,
                    notification_type='vehicle_registered',
                    title='Vehicle Registered 🚗',
                    body=f'Your {instance.display_name or instance.license_plate} has been registered',
                    send_push=True
                )
            elif instance.is_verified and not created:
                # Check if this is the first time it's verified
                safe_send_notification(
                    user_id=instance.driver.user.id,
                    notification_type='vehicle_verified',
                    title='Vehicle Verified ✅',
                    body=f'Your {instance.display_name or instance.license_plate} has been verified',
                    send_push=True,
                    send_sms=True
                )
        
        # Connect signal
        post_save.connect(vehicle_notification, sender=Vehicle, weak=False)
        
    except (ImportError, AttributeError) as e:
        pass
