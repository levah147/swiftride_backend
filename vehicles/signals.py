"""
FILE LOCATION: vehicles/signals.py
Signal handlers for vehicles app - WITH NOTIFICATIONS INTEGRATED!
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Vehicle, VehicleInspection


@receiver(post_save, sender=Vehicle)
def vehicle_created_handler(sender, instance, created, **kwargs):
    """
    Handle vehicle registration.
    Send notifications - handled by notifications app signals.
    """
    if created:
        print(f"🚗 New vehicle registered: {instance.license_plate}")


@receiver(post_save, sender=Vehicle)
def vehicle_verified_handler(sender, instance, created, **kwargs):
    """
    Handle vehicle verification.
    Notifications handled by notifications app signals.
    """
    if not created and instance.is_verified:
        print(f"✅ Vehicle verified: {instance.license_plate}")


@receiver(post_save, sender=VehicleInspection)
def inspection_completed_handler(sender, instance, created, **kwargs):
    """Handle vehicle inspection completion"""
    if created:
        print(f"✅ Inspection completed for {instance.vehicle.license_plate}: {instance.inspection_status}")
        
        # Send notification to driver
        try:
            from notifications.tasks import send_notification_all_channels
            
            if instance.inspection_status == 'passed':
                send_notification_all_channels.delay(
                    user_id=instance.vehicle.driver.user.id,
                    notification_type='inspection_passed',
                    title='Inspection Passed ✅',
                    body=f'Your {instance.vehicle.display_name} passed inspection',
                    send_push=True
                )
            elif instance.inspection_status == 'failed':
                send_notification_all_channels.delay(
                    user_id=instance.vehicle.driver.user.id,
                    notification_type='inspection_failed',
                    title='Inspection Failed',
                    body=f'Your {instance.vehicle.display_name} failed inspection. Please address the issues.',
                    send_push=True,
                    send_sms=True
                )
        except ImportError:
            pass





