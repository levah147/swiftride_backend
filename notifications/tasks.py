"""
FILE LOCATION: notifications/tasks.py

Celery tasks for notifications app.
Background tasks for sending notifications via different channels.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification, NotificationPreference, SMSLog, EmailLog
from .utils import (
    send_fcm_push_notification,
    send_sms_africastalking,
    send_sms_twilio,
    send_sms_termii,
    send_email_notification
)
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_push_notification_task(
    self,
    user_ids=None,
    user_type=None,
    title='',
    body='',
    notification_type='general',
    data_payload=None
):
    """
    Send push notification to users.
    
    Args:
        user_ids: List of user IDs (optional)
        user_type: 'all', 'riders', 'drivers' (optional)
        title: Notification title
        body: Notification body
        notification_type: Type of notification
        data_payload: Additional data
    """
    try:
        # Get users to send to
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
        elif user_type:
            if user_type == 'riders':
                users = User.objects.filter(is_driver=False)
            elif user_type == 'drivers':
                users = User.objects.filter(driver__isnull=False)
            else:  # all
                users = User.objects.all()
        else:
            return {'success': False, 'error': 'No users specified'}
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                # Create in-app notification
                notification = Notification.objects.create(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    data=data_payload or {}
                )
                
                # Check user preferences
                try:
                    prefs = user.notification_preferences
                    if not prefs.push_enabled:
                        continue
                except NotificationPreference.DoesNotExist:
                    # Default: send if no preferences set
                    pass
                
                # Send FCM push notification
                result = send_fcm_push_notification(
                    user=user,
                    title=title,
                    body=body,
                    data=data_payload or {}
                )
                
                if result.get('success'):
                    notification.sent_via_push = True
                    notification.save()
                    sent_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error sending push to user {user.id}: {str(e)}")
                failed_count += 1
                continue
        
        return {
            'success': True,
            'sent': sent_count,
            'failed': failed_count
        }
        
    except Exception as e:
        logger.error(f"Error in send_push_notification_task: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_sms_task(self, user_id, message, provider='africastalking'):
    """
    Send SMS to a user.
    
    Args:
        user_id: User ID
        message: SMS message
        provider: SMS provider ('africastalking', 'twilio', 'termii')
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check user preferences
        try:
            prefs = user.notification_preferences
            if not prefs.sms_enabled:
                return {'success': False, 'reason': 'SMS disabled by user'}
        except NotificationPreference.DoesNotExist:
            pass
        
        # Create SMS log
        sms_log = SMSLog.objects.create(
            user=user,
            phone_number=user.phone_number,
            message=message,
            provider=provider,
            status='pending'
        )
        
        # Send SMS based on provider
        if provider == 'africastalking':
            result = send_sms_africastalking(user.phone_number, message)
        elif provider == 'twilio':
            result = send_sms_twilio(user.phone_number, message)
        elif provider == 'termii':
            result = send_sms_termii(user.phone_number, message)
        else:
            result = {'success': False, 'error': 'Invalid provider'}
        
        # Update SMS log
        if result.get('success'):
            sms_log.status = 'sent'
            sms_log.provider_message_id = result.get('message_id')
            sms_log.cost = result.get('cost')
        else:
            sms_log.status = 'failed'
            sms_log.error_message = result.get('error')
        
        sms_log.save()
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_email_task(self, user_id, subject, body, html_body=None):
    """
    Send email to a user.
    
    Args:
        user_id: User ID
        subject: Email subject
        body: Email body (plain text)
        html_body: Email body (HTML)
    """
    try:
        user = User.objects.get(id=user_id)
        
        if not user.email:
            return {'success': False, 'reason': 'User has no email'}
        
        # Check user preferences
        try:
            prefs = user.notification_preferences
            if not prefs.email_enabled:
                return {'success': False, 'reason': 'Email disabled by user'}
        except NotificationPreference.DoesNotExist:
            pass
        
        # Create email log
        email_log = EmailLog.objects.create(
            user=user,
            recipient_email=user.email,
            subject=subject,
            body=body,
            html_body=html_body,
            status='pending'
        )
        
        # Send email
        result = send_email_notification(
            to_email=user.email,
            subject=subject,
            body=body,
            html_body=html_body
        )
        
        # Update email log
        if result.get('success'):
            email_log.status = 'sent'
            email_log.sent_at = timezone.now()
        else:
            email_log.status = 'failed'
            email_log.error_message = result.get('error')
        
        email_log.save()
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_notification_all_channels(
    user_id,
    notification_type,
    title,
    body,
    send_push=True,
    send_sms=False,
    send_email=False,
    data=None
):
    """
    Send notification via all specified channels.
    
    Args:
        user_id: User ID
        notification_type: Type of notification
        title: Notification title
        body: Notification body
        send_push: Send push notification
        send_sms: Send SMS
        send_email: Send email
        data: Additional data
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {}
        )
        
        # Send via push
        if send_push:
            send_push_notification_task.delay(
                user_ids=[user_id],
                title=title,
                body=body,
                notification_type=notification_type,
                data_payload=data
            )
        
        # Send via SMS
        if send_sms:
            send_sms_task.delay(
                user_id=user_id,
                message=f"{title}: {body}"
            )
        
        # Send via email
        if send_email:
            send_email_task.delay(
                user_id=user_id,
                subject=title,
                body=body
            )
        
        return {'success': True, 'notification_id': notification.id}
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error in send_notification_all_channels: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_notifications():
    """
    Cleanup old read notifications (older than 30 days).
    Run this task daily via Celery Beat.
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    deleted_count = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old notifications")
    
    return {
        'success': True,
        'deleted_count': deleted_count
    }


@shared_task
def cleanup_old_logs():
    """
    Cleanup old SMS and email logs (older than 90 days).
    Run this task weekly via Celery Beat.
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    # Cleanup SMS logs
    sms_deleted = SMSLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    # Cleanup email logs
    email_deleted = EmailLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {sms_deleted} SMS logs and {email_deleted} email logs")
    
    return {
        'success': True,
        'sms_deleted': sms_deleted,
        'email_deleted': email_deleted
    }


@shared_task
def send_daily_notification_summary():
    """
    Send daily notification summary to admin.
    Run this task daily via Celery Beat.
    """
    from datetime import timedelta
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Get statistics
    notifications_sent = Notification.objects.filter(
        created_at__date=yesterday
    ).count()
    
    sms_sent = SMSLog.objects.filter(
        created_at__date=yesterday,
        status='sent'
    ).count()
    
    emails_sent = EmailLog.objects.filter(
        created_at__date=yesterday,
        status='sent'
    ).count()
    
    # Send summary email to admin
    # (Implementation depends on your admin email setup)
    
    logger.info(
        f"Daily summary: {notifications_sent} notifications, "
        f"{sms_sent} SMS, {emails_sent} emails"
    )
    
    return {
        'success': True,
        'notifications': notifications_sent,
        'sms': sms_sent,
        'emails': emails_sent
    }