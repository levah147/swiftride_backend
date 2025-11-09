
"""
FILE LOCATION: safety/signals.py

CRITICAL SAFETY SIGNAL HANDLERS
Automatic emergency response & user protection.

LIFE-SAVING INTEGRATIONS:
- Auto SOS triggers
- Emergency contact notifications
- Trip sharing alerts
- Safety check monitoring
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def create_safety_settings_handler(sender, instance, created, **kwargs):
    """
    Create default safety settings for new users.
    """
    if created:
        from .models import SafetySettings
        
        try:
            SafetySettings.objects.get_or_create(
                user=instance,
                defaults={
                    'auto_share_trips': False,
                    'enable_safety_checks': True,
                    'quick_sos': True,
                    'silent_sos': False,
                    'notify_contacts_on_ride_end': True
                }
            )
            
            logger.info(f"🛡️ Safety settings created for {instance.phone_number}")
            
        except Exception as e:
            logger.error(f"Error creating safety settings: {str(e)}")


@receiver(post_save, sender='safety.EmergencySOS')
def sos_triggered_handler(sender, instance, created, **kwargs):
    """
    CRITICAL: Handle SOS trigger - HIGHEST PRIORITY!
    
    1. Notify ALL emergency contacts immediately
    2. Alert admin team
    3. Notify driver (if in ride)
    4. Start tracking
    """
    if created:
        logger.critical(
            f"🚨 EMERGENCY SOS TRIGGERED! User: {instance.user.phone_number}, "
            f"Location: {instance.latitude}, {instance.longitude}"
        )
        
        try:
            # 1. Notify ALL emergency contacts
            from .services import notify_emergency_contacts
            notify_emergency_contacts(instance)
            
            # 2. Alert admin/support team
            from notifications.tasks import send_notification_all_channels
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            for admin in admins:
                send_notification_all_channels.delay(
                    user_id=admin.id,
                    notification_type='emergency_sos',
                    title='🚨 EMERGENCY SOS ALERT!',
                    body=f'User {instance.user.phone_number} triggered SOS!',
                    send_push=True,
                    send_sms=True,
                    data={
                        'sos_id': instance.id,
                        'user_id': instance.user.id,
                        'latitude': str(instance.latitude),
                        'longitude': str(instance.longitude),
                        'address': instance.address
                    }
                )
            
            # 3. Notify driver if in ride
            if instance.ride and instance.ride.driver:
                send_notification_all_channels.delay(
                    user_id=instance.ride.driver.user.id,
                    notification_type='rider_sos',
                    title='⚠️ PASSENGER EMERGENCY',
                    body='Your passenger has triggered an emergency alert.',
                    send_push=True,
                    send_sms=True,
                    data={'sos_id': instance.id}
                )
            
            # 4. Create support ticket automatically
            from support.services import create_ticket
            from support.models import SupportCategory
            
            category = SupportCategory.objects.filter(slug='emergency').first()
            if category:
                create_ticket(
                    user=instance.user,
                    category=category,
                    subject=f'EMERGENCY SOS - {instance.user.phone_number}',
                    description=f'Emergency SOS triggered at {instance.address}. Notes: {instance.notes}',
                    ride=instance.ride,
                    priority='urgent'
                )
            
            logger.critical(f"🚨 Emergency response initiated for SOS #{instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling SOS trigger: {str(e)}")


@receiver(post_save, sender='rides.Ride')
def ride_started_safety_handler(sender, instance, **kwargs):
    """
    When ride starts:
    - Auto-share if enabled
    - Schedule safety checks
    - Notify emergency contacts (if enabled)
    """
    if instance.status == 'in_progress':
        from .models import SafetySettings, TripShare
        
        try:
            settings = SafetySettings.objects.filter(user=instance.user).first()
            
            if settings:
                # Auto-share trip
                if settings.auto_share_trips:
                    contacts = instance.user.emergency_contacts.filter(
                        is_active=True,
                        notify_trip_share=True
                    )
                    
                    if contacts.exists():
                        from .services import create_trip_share
                        
                        contact_phones = list(contacts.values_list('phone_number', flat=True))
                        create_trip_share(instance, instance.user, contact_phones)
                        
                        logger.info(f"🔗 Auto-shared trip for ride #{instance.id}")
                
                # Schedule safety checks
                if settings.enable_safety_checks:
                    from .tasks import schedule_safety_checks
                    schedule_safety_checks.delay(instance.id)
                
                # Notify contacts of ride start
                if settings.notify_contacts_on_ride_start:
                    contacts = instance.user.emergency_contacts.filter(
                        is_active=True,
                        notify_trip_start=True
                    )
                    
                    for contact in contacts:
                        from .services import send_ride_start_sms
                        send_ride_start_sms(contact, instance)
        
        except Exception as e:
            logger.error(f"Error in ride start safety handler: {str(e)}")


@receiver(post_save, sender='rides.Ride')
def ride_ended_safety_handler(sender, instance, **kwargs):
    """
    When ride ends:
    - Deactivate trip share
    - Notify emergency contacts (if enabled)
    - Check if arrived at safe zone
    """
    if instance.status in ['completed', 'cancelled']:
        from .models import TripShare, SafeZone
        
        try:
            # Deactivate trip share
            trip_share = TripShare.objects.filter(ride=instance).first()
            if trip_share and trip_share.is_active:
                trip_share.deactivate()
                logger.info(f"🔗 Trip share deactivated for ride #{instance.id}")
            
            # Notify contacts of ride end
            settings = instance.user.safety_settings
            if settings and settings.notify_contacts_on_ride_end:
                contacts = instance.user.emergency_contacts.filter(
                    is_active=True,
                    notify_trip_end=True
                )
                
                for contact in contacts:
                    from notifications.tasks import send_sms_notification
                    
                    send_sms_notification.delay(
                        phone_number=contact.phone_number,
                        message=f"{instance.user.phone_number} has safely completed their ride to {instance.dropoff_location}."
                    )
            
            # Check safe zone arrival
            if instance.status == 'completed':
                safe_zones = SafeZone.objects.filter(
                    user=instance.user,
                    is_active=True,
                    notify_on_arrival=True
                )
                
                for zone in safe_zones:
                    from .services import check_safe_zone_arrival
                    if check_safe_zone_arrival(instance, zone):
                        logger.info(f"✅ User arrived at safe zone: {zone.name}")
                        break
        
        except Exception as e:
            logger.error(f"Error in ride end safety handler: {str(e)}")


@receiver(post_save, sender='safety.IncidentReport')
def incident_reported_handler(sender, instance, created, **kwargs):
    """
    Handle incident reports.
    Create support ticket and alert admins.
    """
    if created:
        logger.warning(
            f"⚠️ Incident reported: {instance.incident_type} "
            f"by {instance.user.phone_number}, severity: {instance.severity}"
        )
        
        try:
            # Create support ticket
            from support.services import create_ticket
            from support.models import SupportCategory
            
            category = SupportCategory.objects.filter(slug='safety-incident').first()
            if category:
                create_ticket(
                    user=instance.user,
                    category=category,
                    subject=f'Safety Incident: {instance.get_incident_type_display()}',
                    description=instance.description,
                    ride=instance.ride,
                    priority='high' if instance.severity >= 4 else 'medium'
                )
            
            # Alert admins for severe incidents
            if instance.severity >= 4:
                from notifications.tasks import send_notification_all_channels
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                admins = User.objects.filter(is_staff=True, is_active=True)
                
                for admin in admins:
                    send_notification_all_channels.delay(
                        user_id=admin.id,
                        notification_type='incident_report',
                        title='⚠️ Severe Incident Reported',
                        body=f'{instance.incident_type}: {instance.description[:100]}',
                        send_push=True,
                        data={'incident_id': instance.id}
                    )
            
            # Consider driver suspension for severe incidents
            if instance.severity == 5 and instance.ride and instance.ride.driver:
                instance.driver_suspended = True
                instance.save()
                
                # Update driver status
                driver = instance.ride.driver
                driver.is_active = False
                driver.status = 'suspended'
                driver.save()
                
                logger.critical(
                    f"🚫 Driver {driver.user.phone_number} suspended due to critical incident"
                )
        
        except Exception as e:
            logger.error(f"Error handling incident report: {str(e)}")
