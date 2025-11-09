'ENDFILE'
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
    """Setup signal handlers for other apps"""
    
    # DRIVERS APP SIGNALS
    try:
        from drivers.models import Driver
        
        @receiver(post_save, sender=Driver)
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
    except ImportError:
        pass
    
    # RIDES APP SIGNALS
    try:
        from rides.models import Ride
        
        @receiver(post_save, sender=Ride)
        def ride_notification(sender, instance, created, **kwargs):
            """Send notifications for ride events"""
            
            # New ride created
            if created and instance.status == 'pending':
                # Notify nearby drivers (handled in rides app)
                pass
            
            # Ride accepted
            elif instance.status == 'accepted' and instance.driver:
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_accepted',
                    title='Driver Accepted! 🚗',
                    body=f'{instance.driver.user.get_full_name()} is coming to pick you up',
                    send_push=True,
                    send_sms=False,
                    data={'ride_id': instance.id}
                )
            
            # Driver arrived
            elif instance.status == 'driver_arrived':
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
            elif instance.status == 'in_progress':
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_started',
                    title='Ride Started 🚀',
                    body='Your ride has started. Enjoy your trip!',
                    send_push=True,
                    data={'ride_id': instance.id}
                )
            
            # Ride completed
            elif instance.status == 'completed':
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
            elif instance.status == 'cancelled':
                safe_send_notification(
                    user_id=instance.user.id,
                    notification_type='ride_cancelled',
                    title='Ride Cancelled',
                    body='Your ride has been cancelled',
                    send_push=True,
                    data={'ride_id': instance.id}
                )
    except ImportError:
        pass
    
    # PAYMENTS APP SIGNALS
    try:
        from payments.models import Transaction, Withdrawal
        
        @receiver(post_save, sender=Transaction)
        def transaction_notification(sender, instance, created, **kwargs):
            """Notify user about transactions"""
            if created or instance.status == 'completed':
                
                # Deposit
                if instance.transaction_type == 'deposit' and instance.status == 'completed':
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
                elif instance.transaction_type == 'ride_payment' and instance.status == 'completed':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='payment_processed',
                        title='Payment Successful ✅',
                        body=f'₦{instance.amount} has been deducted for your ride',
                        send_push=True,
                        data={'amount': str(instance.amount)}
                    )
                
                # Driver earnings
                elif instance.transaction_type == 'ride_earning' and instance.status == 'completed':
                    safe_send_notification(
                        user_id=instance.user.id,
                        notification_type='earnings_added',
                        title='Earnings Added 💵',
                        body=f'₦{instance.amount} has been added to your wallet',
                        send_push=True,
                        data={'amount': str(instance.amount)}
                    )
        
        @receiver(post_save, sender=Withdrawal)
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
                        body=f'Your withdrawal request was rejected. Reason: {instance.rejection_reason}',
                        send_push=True,
                        send_sms=False
                    )
    except ImportError:
        pass
    
    # VEHICLES APP SIGNALS
    try:
        from vehicles.models import Vehicle
        
        @receiver(post_save, sender=Vehicle)
        def vehicle_notification(sender, instance, created, **kwargs):
            """Notify driver about vehicle status"""
            if created:
                safe_send_notification(
                    user_id=instance.driver.user.id,
                    notification_type='vehicle_registered',
                    title='Vehicle Registered 🚗',
                    body=f'Your {instance.display_name} has been registered',
                    send_push=True
                )
            elif instance.is_verified and not created:
                safe_send_notification(
                    user_id=instance.driver.user.id,
                    notification_type='vehicle_verified',
                    title='Vehicle Verified ✅',
                    body=f'Your {instance.display_name} has been verified',
                    send_push=True,
                    send_sms=True
                )
    except ImportError:
        pass
    
    # CHAT APP SIGNALS - NEW! 💬
    try:
        from chat.models import Message, Conversation
        
        # Message notifications are handled in chat/signals.py
        # to avoid duplicate notifications
        
    except ImportError:
        pass
    
    
    

# """
# FILE LOCATION: notifications/signals.py

# Signal handlers that automatically send notifications when events occur.
# This connects notifications to ALL other apps!
# """
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model
# from .tasks import send_notification_all_channels

# User = get_user_model()


# @receiver(post_save, sender=User)
# def user_created_notification(sender, instance, created, **kwargs):
#     """Send welcome notification when user registers"""
#     if created:
#         send_notification_all_channels.delay(
#             user_id=instance.id,
#             notification_type='welcome',
#             title='Welcome to SwiftRide! 🎉',
#             body='Thank you for joining SwiftRide. Start booking rides now!',
#             send_push=True,
#             send_sms=False,
#             send_email=False
#         )


# # Import and register signals from other apps
# def setup_cross_app_signals():
#     """Setup signal handlers for other apps"""
    
#     # DRIVERS APP SIGNALS
#     try:
#         from drivers.models import Driver
        
#         @receiver(post_save, sender=Driver)
#         def driver_status_notification(sender, instance, created, **kwargs):
#             """Notify driver when application status changes"""
#             if not created:
#                 if instance.status == 'approved':
#                     send_notification_all_channels.delay(
#                         user_id=instance.user.id,
#                         notification_type='driver_approved',
#                         title='Application Approved! ✅',
#                         body='Congratulations! Your driver application has been approved.',
#                         send_push=True,
#                         send_sms=True,
#                         send_email=True
#                     )
#                 elif instance.status == 'rejected':
#                     send_notification_all_channels.delay(
#                         user_id=instance.user.id,
#                         notification_type='driver_rejected',
#                         title='Application Update',
#                         body='Your driver application needs review. Please contact support.',
#                         send_push=True,
#                         send_sms=False
#                     )
#     except ImportError:
#         pass
    
#     # RIDES APP SIGNALS
#     try:
#         from rides.models import Ride
        
#         @receiver(post_save, sender=Ride)
#         def ride_notification(sender, instance, created, **kwargs):
#             """Send notifications for ride events"""
            
#             # New ride created
#             if created and instance.status == 'pending':
#                 # Notify nearby drivers (handled in rides app)
#                 pass
            
#             # Ride accepted
#             elif instance.status == 'accepted' and instance.driver:
#                 send_notification_all_channels.delay(
#                     user_id=instance.user.id,
#                     notification_type='ride_accepted',
#                     title='Driver Accepted! 🚗',
#                     body=f'{instance.driver.user.get_full_name()} is coming to pick you up',
#                     send_push=True,
#                     send_sms=False,
#                     data={'ride_id': instance.id}
#                 )
            
#             # Driver arrived
#             elif instance.status == 'driver_arrived':
#                 send_notification_all_channels.delay(
#                     user_id=instance.user.id,
#                     notification_type='driver_arrived',
#                     title='Driver Arrived! 📍',
#                     body='Your driver has arrived at the pickup location',
#                     send_push=True,
#                     send_sms=True,
#                     data={'ride_id': instance.id}
#                 )
            
#             # Ride started
#             elif instance.status == 'in_progress':
#                 send_notification_all_channels.delay(
#                     user_id=instance.user.id,
#                     notification_type='ride_started',
#                     title='Ride Started 🚀',
#                     body='Your ride has started. Enjoy your trip!',
#                     send_push=True,
#                     data={'ride_id': instance.id}
#                 )
            
#             # Ride completed
#             elif instance.status == 'completed':
#                 # Notify rider
#                 send_notification_all_channels.delay(
#                     user_id=instance.user.id,
#                     notification_type='ride_completed',
#                     title='Ride Completed ✅',
#                     body='Thank you for riding with SwiftRide!',
#                     send_push=True,
#                     data={'ride_id': instance.id}
#                 )
                
#                 # Notify driver
#                 if instance.driver:
#                     send_notification_all_channels.delay(
#                         user_id=instance.driver.user.id,
#                         notification_type='ride_completed',
#                         title='Ride Completed ✅',
#                         body='Payment has been processed and added to your wallet',
#                         send_push=True,
#                         data={'ride_id': instance.id}
#                     )
            
#             # Ride cancelled
#             elif instance.status == 'cancelled':
#                 send_notification_all_channels.delay(
#                     user_id=instance.user.id,
#                     notification_type='ride_cancelled',
#                     title='Ride Cancelled',
#                     body='Your ride has been cancelled',
#                     send_push=True,
#                     data={'ride_id': instance.id}
#                 )
#     except ImportError:
#         pass
    
#     # PAYMENTS APP SIGNALS
#     try:
#         from payments.models import Transaction, Withdrawal
        
#         @receiver(post_save, sender=Transaction)
#         def transaction_notification(sender, instance, created, **kwargs):
#             """Notify user about transactions"""
#             if created or instance.status == 'completed':
                
#                 # Deposit
#                 if instance.transaction_type == 'deposit' and instance.status == 'completed':
#                     send_notification_all_channels.delay(
#                         user_id=instance.user.id,
#                         notification_type='wallet_credited',
#                         title='Wallet Credited 💰',
#                         body=f'₦{instance.amount} has been added to your wallet',
#                         send_push=True,
#                         send_sms=False,
#                         data={'amount': str(instance.amount)}
#                     )
                
#                 # Ride payment
#                 elif instance.transaction_type == 'ride_payment' and instance.status == 'completed':
#                     send_notification_all_channels.delay(
#                         user_id=instance.user.id,
#                         notification_type='payment_processed',
#                         title='Payment Successful ✅',
#                         body=f'₦{instance.amount} has been deducted for your ride',
#                         send_push=True,
#                         data={'amount': str(instance.amount)}
#                     )
                
#                 # Driver earnings
#                 elif instance.transaction_type == 'ride_earning' and instance.status == 'completed':
#                     send_notification_all_channels.delay(
#                         user_id=instance.user.id,
#                         notification_type='earnings_added',
#                         title='Earnings Added 💵',
#                         body=f'₦{instance.amount} has been added to your wallet',
#                         send_push=True,
#                         data={'amount': str(instance.amount)}
#                     )
        
#         @receiver(post_save, sender=Withdrawal)
#         def withdrawal_notification(sender, instance, created, **kwargs):
#             """Notify driver about withdrawal status"""
#             if not created:
#                 if instance.status == 'completed':
#                     send_notification_all_channels.delay(
#                         user_id=instance.driver.user.id,
#                         notification_type='withdrawal_approved',
#                         title='Withdrawal Approved ✅',
#                         body=f'₦{instance.amount} has been sent to your bank account',
#                         send_push=True,
#                         send_sms=True,
#                         data={'amount': str(instance.amount)}
#                     )
#                 elif instance.status == 'rejected':
#                     send_notification_all_channels.delay(
#                         user_id=instance.driver.user.id,
#                         notification_type='withdrawal_rejected',
#                         title='Withdrawal Rejected',
#                         body=f'Your withdrawal request was rejected. Reason: {instance.rejection_reason}',
#                         send_push=True,
#                         send_sms=False
#                     )
#     except ImportError:
#         pass
    
#     # VEHICLES APP SIGNALS
#     try:
#         from vehicles.models import Vehicle
        
#         @receiver(post_save, sender=Vehicle)
#         def vehicle_notification(sender, instance, created, **kwargs):
#             """Notify driver about vehicle status"""
#             if created:
#                 send_notification_all_channels.delay(
#                     user_id=instance.driver.user.id,
#                     notification_type='vehicle_registered',
#                     title='Vehicle Registered 🚗',
#                     body=f'Your {instance.display_name} has been registered',
#                     send_push=True
#                 )
#             elif instance.is_verified and not created:
#                 send_notification_all_channels.delay(
#                     user_id=instance.driver.user.id,
#                     notification_type='vehicle_verified',
#                     title='Vehicle Verified ✅',
#                     body=f'Your {instance.display_name} has been verified',
#                     send_push=True,
#                     send_sms=True
#                 )
#     except ImportError:
#         pass

