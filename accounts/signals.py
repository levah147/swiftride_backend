
# """
# FILE LOCATION: accounts/signals.py
# Signal handlers for accounts app - WITH NOTIFICATIONS INTEGRATED!
# """
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model

# User = get_user_model()


# @receiver(post_save, sender=User)
# def user_created_handler(sender, instance, created, **kwargs):
#     """
#     Handle new user creation.
#     Creates wallet and sends welcome notification.
#     """
#     if created:
#         print(f"👤 New user created: {instance.phone_number}")
        
#         # Create wallet automatically
#         try:
#             from payments.models import Wallet
#             Wallet.objects.get_or_create(user=instance)
#             print(f"💰 Wallet created for {instance.phone_number}")
#         except ImportError:
#             pass
        
#         # Create notification preferences
#         try:
#             from notifications.models import NotificationPreference
#             NotificationPreference.objects.get_or_create(user=instance)
#             print(f"🔔 Notification preferences created for {instance.phone_number}")
#         except ImportError:
#             pass
        
#         # Send welcome notification (handled by notifications app signals)
#         # No need to call here - notifications app will handle it!


# @receiver(post_save, sender=User)
# def user_phone_verified_handler(sender, instance, created, **kwargs):
#     """Send notification when phone is verified"""
#     if not created and instance.is_phone_verified:
#         try:
#             from notifications.tasks import send_notification_all_channels
            
#             # Check if notification already sent
#             if not hasattr(instance, '_phone_verified_notif_sent'):
#                 send_notification_all_channels.delay(
#                     user_id=instance.id,
#                     notification_type='phone_verified',
#                     title='Phone Verified ✅',
#                     body='Your phone number has been verified successfully',
#                     send_push=True,
#                     send_sms=False
#                 )
#                 instance._phone_verified_notif_sent = True
#         except ImportError:
#             pass


"""
FILE LOCATION: accounts/signals.py

Signal handlers for accounts app integration.
Automatically creates wallet, notification preferences, and other required objects.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    Handle user creation events.
    
    When a new user is created:
    1. Create wallet automatically
    2. Create notification preferences
    3. Welcome notification is sent by notifications app signals
    4. Loyalty account is created by promotions app signals
    5. Safety settings are created by safety app signals
    """
    if created:
        logger.info(f"✅ New user registered: {instance.phone_number}")
        
        # Create wallet automatically
        try:
            from payments.models import Wallet
            Wallet.objects.get_or_create(user=instance)
            logger.info(f"💰 Wallet created for {instance.phone_number}")
        except Exception as e:
            logger.error(f"Error creating wallet for {instance.phone_number}: {str(e)}")
        
        # Create notification preferences automatically
        try:
            from notifications.models import NotificationPreference
            NotificationPreference.objects.get_or_create(user=instance)
            logger.info(f"🔔 Notification preferences created for {instance.phone_number}")
        except Exception as e:
            logger.error(f"Error creating notification preferences for {instance.phone_number}: {str(e)}")
        
        # Welcome notification is handled by notifications/signals.py
        # Loyalty account is handled by promotions/signals.py
        # Safety settings are handled by safety/signals.py


@receiver(post_save, sender=User)
def user_becomes_driver(sender, instance, **kwargs):
    """Handle when user becomes a driver"""
    if instance.is_driver:
        # Check if this is a new driver registration
        if not hasattr(instance, '_driver_status_changed'):
            instance._driver_status_changed = True
            logger.info(f"✅ User {instance.phone_number} is now a driver")
            
            # Driver notifications are handled by drivers/signals.py and notifications/signals.py

