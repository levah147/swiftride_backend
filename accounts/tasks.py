
"""
FILE LOCATION: accounts/tasks.py

Celery tasks for accounts app.
Includes async OTP sending, email sending, and maintenance tasks.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_otps():
    """Delete expired OTP records (older than 7 days)"""
    from .models import OTPVerification
    
    cutoff_date = timezone.now() - timedelta(days=7)
    
    deleted_count = OTPVerification.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} expired OTP records")
    return {'success': True, 'deleted_count': deleted_count}


@shared_task
def send_otp_async(phone_number, otp_code):
    """
    Send OTP asynchronously via SMS.
    
    This task is queued and processed in the background,
    improving API response time.
    """
    from .utils import SMSService
    
    try:
        success, message = SMSService.send_otp(phone_number, otp_code)
        
        if success:
            logger.info(f"Async OTP sent successfully to {phone_number}")
            return {'success': True, 'phone': phone_number}
        else:
            logger.error(f"Async OTP failed for {phone_number}: {message}")
            return {'success': False, 'error': message}
            
    except Exception as e:
        logger.error(f"Async OTP task error: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_email_async(user_id, email_type, **kwargs):
    """
    Send email asynchronously.
    
    Args:
        user_id: User ID
        email_type: Type of email ('welcome', 'password_reset', 'ride_confirmation')
        **kwargs: Additional data for email template
    """
    from .models import User
    from .utils import EmailService
    
    try:
        user = User.objects.get(id=user_id)
        
        if email_type == 'welcome':
            success = EmailService.send_welcome_email(user)
        elif email_type == 'password_reset':
            reset_token = kwargs.get('reset_token')
            success = EmailService.send_password_reset_email(user, reset_token)
        elif email_type == 'ride_confirmation':
            from rides.models import Ride
            ride_id = kwargs.get('ride_id')
            ride = Ride.objects.get(id=ride_id)
            success = EmailService.send_ride_confirmation(user, ride)
        else:
            logger.error(f"Unknown email type: {email_type}")
            return {'success': False, 'error': 'Unknown email type'}
        
        if success:
            logger.info(f"Async email sent: {email_type} to {user.email}")
            return {'success': True, 'email_type': email_type}
        else:
            logger.error(f"Async email failed: {email_type} to {user.email}")
            return {'success': False, 'error': 'Email sending failed'}
            
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Async email task error: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_bulk_notifications(user_ids, message, notification_type='info'):
    """
    Send bulk notifications to multiple users.
    
    Args:
        user_ids: List of user IDs
        message: Notification message
        notification_type: Type of notification
    """
    from .models import User
    
    try:
        users = User.objects.filter(id__in=user_ids)
        sent_count = 0
        
        for user in users:
            try:
                # Send via notifications app
                from notifications.models import Notification
                Notification.objects.create(
                    user=user,
                    title='System Notification',
                    message=message,
                    notification_type=notification_type
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to notify user {user.id}: {str(e)}")
        
        logger.info(f"Bulk notifications sent to {sent_count}/{len(user_ids)} users")
        return {'success': True, 'sent_count': sent_count, 'total': len(user_ids)}
        
    except Exception as e:
        logger.error(f"Bulk notification task error: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def deactivate_inactive_users():
    """Deactivate users who haven't logged in for 1 year"""
    from .models import User
    
    one_year_ago = timezone.now() - timedelta(days=365)
    
    inactive_users = User.objects.filter(
        last_login__lt=one_year_ago,
        is_active=True,
        is_staff=False  # Don't deactivate staff
    )
    
    count = inactive_users.update(is_active=False)
    
    logger.info(f"Deactivated {count} inactive users")
    return {'success': True, 'deactivated_count': count}
