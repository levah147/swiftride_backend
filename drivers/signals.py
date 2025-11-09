"""
FILE LOCATION: drivers/signals.py
Signal handlers for drivers app - WITH NOTIFICATIONS INTEGRATED!
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Driver


@receiver(post_save, sender=Driver)
def driver_application_handler(sender, instance, created, **kwargs):
    """
    Handle driver application events.
    Send notifications for status changes.
    """
    if created:
        print(f"🚗 New driver application: {instance.user.phone_number}")
        
        # Send notification to driver
        try:
            from notifications.tasks import send_notification_all_channels
            send_notification_all_channels.delay(
                user_id=instance.user.id,
                notification_type='driver_application_received',
                title='Application Received 📝',
                body='Your driver application has been received and is under review',
                send_push=True,
                send_sms=False
            )
        except ImportError:
            pass
    
    # Status change notifications handled by notifications app signals
    # But we update user.is_driver flag here
    if instance.status == 'approved':
        instance.user.is_driver = True
        instance.user.save(update_fields=['is_driver'])
        print(f"✅ Driver approved: {instance.user.phone_number}")


@receiver(post_save, sender=Driver)
def driver_online_status_handler(sender, instance, **kwargs):
    """Handle driver going online/offline"""
    if instance.is_online:
        print(f"🟢 Driver {instance.user.phone_number} is now ONLINE")
    else:
        print(f"🔴 Driver {instance.user.phone_number} is now OFFLINE")
        

# """
# FILE LOCATION: drivers/signals.py

# Signal handlers for drivers app integration.
# """
# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
# from .models import Driver, DriverRating


# @receiver(post_save, sender=Driver)
# def driver_status_changed(sender, instance, created, **kwargs):
#     """
#     Handle driver status changes.
    
#     Actions:
#     - When approved: Update user.is_driver = True
#     - When approved: Send approval notification
#     - When rejected: Send rejection notification
#     """
#     if created:
#         print(f"✅ New driver application: {instance.user.phone_number}")
#         # TODO: Notify admin of new application
    
#     elif instance.status == 'approved' and not created:
#         # Ensure user is marked as driver
#         if not instance.user.is_driver:
#             instance.user.is_driver = True
#             instance.user.save(update_fields=['is_driver'])
#             print(f"✅ Driver approved: {instance.user.phone_number}")
        
#         # TODO: Send approval notification to driver
#         # from notifications.services import send_notification
#         # send_notification(
#         #     user=instance.user,
#         #     title='Driver Application Approved!',
#         #     message='Congratulations! You can now start accepting rides.'
#         # )
    
#     elif instance.status == 'rejected':
#         print(f"❌ Driver rejected: {instance.user.phone_number}")
#         # TODO: Send rejection notification with reason


# @receiver(post_save, sender=DriverRating)
# def rating_created(sender, instance, created, **kwargs):
#     """
#     Handle new driver rating.
    
#     Actions:
#     - Update driver's average rating (already done in model)
#     - TODO: Send notification to driver
#     """
#     if created:
#         print(f"⭐ New rating for driver {instance.driver.id}: {instance.rating} stars")
#         # Driver rating is auto-updated in DriverRating.save()


