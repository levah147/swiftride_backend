

"""
FILE LOCATION: safety/tasks.py

Background safety monitoring tasks.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def schedule_safety_checks(ride_id):
    """
    Schedule safety checks for a ride.
    """
    try:
        from rides.models import Ride
        from .services import create_safety_check
        
        ride = Ride.objects.get(id=ride_id)
        
        # Create initial safety check
        safety_check = create_safety_check(ride)
        
        if safety_check:
            # Schedule check reminder
            send_safety_check_reminder.apply_async(
                args=[safety_check.id],
                eta=safety_check.check_time
            )
            
            return {'success': True, 'check_id': safety_check.id}
        
        return {'success': False, 'error': 'Check not created'}
        
    except Exception as e:
        logger.error(f"Error scheduling safety checks: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_safety_check_reminder(check_id):
    """
    Send safety check notification to user.
    """
    try:
        from .models import SafetyCheck
        
        check = SafetyCheck.objects.get(id=check_id)
        
        # Don't send if ride already ended
        if check.ride.status not in ['in_progress']:
            return {'success': False, 'error': 'Ride ended'}
        
        # Send push notification
        from notifications.tasks import send_notification_all_channels
        
        send_notification_all_channels.delay(
            user_id=check.ride.user.id,
            notification_type='safety_check',
            title='Safety Check 🔔',
            body='Are you OK? Please confirm.',
            send_push=True,
            data={
                'check_id': check.id,
                'ride_id': check.ride.id
            }
        )
        
        check.reminder_sent = True
        check.save()
        
        # Schedule follow-up if no response
        check_for_no_response.apply_async(
            args=[check_id],
            countdown=300  # 5 minutes
        )
        
        logger.info(f"🔔 Safety check reminder sent for check #{check_id}")
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Error sending safety check: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def check_for_no_response(check_id):
    """
    Check if user responded to safety check.
    Alert contacts if no response.
    """
    try:
        from .models import SafetyCheck
        
        check = SafetyCheck.objects.get(id=check_id)
        
        # Check if user responded
        if check.response == 'pending':
            # No response - alert contacts
            check.response = 'no_response'
            check.save()
            
            contacts = check.ride.user.emergency_contacts.filter(
                is_active=True
            )
            
            for contact in contacts:
                from notifications.tasks import send_sms_notification
                
                message = (
                    f"⚠️ SAFETY CHECK ALERT\n\n"
                    f"{check.ride.user.phone_number} hasn't responded to a safety check.\n\n"
                    f"Last known location: Will be updated in tracking link.\n"
                    f"Time: {timezone.now().strftime('%I:%M %p')}"
                )
                
                send_sms_notification.delay(
                    phone_number=contact.phone_number,
                    message=message
                )
            
            check.contacts_notified = True
            check.save()
            
            logger.warning(f"⚠️ No response to safety check #{check_id}, contacts notified")
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Error checking safety response: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_expired_trip_shares():
    """
    Deactivate expired trip shares.
    """
    try:
        from .models import TripShare
        
        expired = TripShare.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )
        
        count = expired.count()
        expired.update(is_active=False)
        
        logger.info(f"🧹 Deactivated {count} expired trip shares")
        
        return {'success': True, 'count': count}
        
    except Exception as e:
        logger.error(f"Error cleaning up trip shares: {str(e)}")
        return {'success': False, 'error': str(e)}


