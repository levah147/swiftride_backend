"""
FILE LOCATION: notifications/utils.py

Utility functions for sending notifications via different channels.
FCM, SMS, Email notifications.
"""
import logging
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import PushToken

User = get_user_model()
logger = logging.getLogger(__name__)


# ========================================
# PUSH NOTIFICATIONS (FCM)
# ========================================

def send_fcm_push_notification(user, title, body, data=None):
    """
    Send push notification via Firebase Cloud Messaging.
    
    Args:
        user: User object
        title: Notification title
        body: Notification body
        data: Additional data payload
    
    Returns:
        dict: {'success': bool, 'message_id': str, 'error': str}
    """
    try:
        # Get user's FCM token
        try:
            push_token = user.push_token
            fcm_token = push_token.token
        except PushToken.DoesNotExist:
            return {'success': False, 'error': 'No FCM token found'}
        
        if not fcm_token:
            return {'success': False, 'error': 'FCM token is empty'}
        
        # FCM API endpoint
        fcm_url = 'https://fcm.googleapis.com/fcm/send'
        
        # Headers
        headers = {
            'Authorization': f'key={settings.FCM_SERVER_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Payload
        payload = {
            'to': fcm_token,
            'notification': {
                'title': title,
                'body': body,
                'sound': 'default',
                'badge': '1'
            },
            'data': data or {}
        }
        
        # Send request
        response = requests.post(fcm_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('message_id'),
                'multicast_id': result.get('multicast_id')
            }
        else:
            return {
                'success': False,
                'error': f'FCM API error: {response.status_code}'
            }
    
    except Exception as e:
        logger.error(f"Error sending FCM notification: {str(e)}")
        return {'success': False, 'error': str(e)}


# ========================================
# SMS NOTIFICATIONS
# ========================================

def send_sms_africastalking(phone_number, message):
    """
    Send SMS via Africa's Talking.
    
    Args:
        phone_number: Phone number
        message: SMS message
    
    Returns:
        dict: {'success': bool, 'message_id': str, 'cost': float, 'error': str}
    """
    try:
        # Africa's Talking API
        url = 'https://api.africastalking.com/version1/messaging'
        
        headers = {
            'ApiKey': settings.AFRICASTALKING_API_KEY,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'username': settings.AFRICASTALKING_USERNAME,
            'to': phone_number,
            'message': message
        }
        
        response = requests.post(url, data=data, headers=headers, timeout=10)
        
        if response.status_code == 201:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId'),
                'cost': result.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('cost', '0')
            }
        else:
            return {
                'success': False,
                'error': f'Africa\'s Talking API error: {response.status_code}'
            }
    
    except Exception as e:
        logger.error(f"Error sending SMS via Africa's Talking: {str(e)}")
        return {'success': False, 'error': str(e)}


def send_sms_twilio(phone_number, message):
    """
    Send SMS via Twilio.
    
    Args:
        phone_number: Phone number
        message: SMS message
    
    Returns:
        dict: {'success': bool, 'message_id': str, 'error': str}
    """
    try:
        from twilio.rest import Client
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        return {
            'success': True,
            'message_id': message.sid
        }
    
    except ImportError:
        return {'success': False, 'error': 'Twilio library not installed'}
    except Exception as e:
        logger.error(f"Error sending SMS via Twilio: {str(e)}")
        return {'success': False, 'error': str(e)}


def send_sms_termii(phone_number, message):
    """
    Send SMS via Termii.
    
    Args:
        phone_number: Phone number
        message: SMS message
    
    Returns:
        dict: {'success': bool, 'message_id': str, 'error': str}
    """
    try:
        url = 'https://api.termii.com/api/sms/send'
        
        data = {
            'api_key': settings.TERMII_API_KEY,
            'to': phone_number,
            'from': settings.TERMII_SENDER_ID,
            'sms': message,
            'type': 'plain',
            'channel': 'generic'
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('message_id')
            }
        else:
            return {
                'success': False,
                'error': f'Termii API error: {response.status_code}'
            }
    
    except Exception as e:
        logger.error(f"Error sending SMS via Termii: {str(e)}")
        return {'success': False, 'error': str(e)}


# ========================================
# EMAIL NOTIFICATIONS
# ========================================

def send_email_notification(to_email, subject, body, html_body=None):
    """
    Send email notification.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body (plain text)
        html_body: Email body (HTML)
    
    Returns:
        dict: {'success': bool, 'message_id': str, 'error': str}
    """
    try:
        from django.core.mail import send_mail
        from django.core.mail import EmailMultiAlternatives
        
        if html_body:
            # Send HTML email
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email]
            )
            email.attach_alternative(html_body, "text/html")
            email.send()
        else:
            # Send plain text email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False
            )
        
        return {
            'success': True,
            'message_id': 'email_sent'
        }
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {'success': False, 'error': str(e)}


# ========================================
# SAFE NOTIFICATION HELPER (For Tests)
# ========================================

def safe_send_notification(*args, **kwargs):
    """
    Safely send notification via Celery.
    Falls back to synchronous execution if Celery is unavailable.
    
    This function is used in signals to handle Celery connection errors gracefully.
    It tries to send notification asynchronously via Celery, and falls back to
    synchronous execution if Celery is not available (e.g., during tests).
    
    Args:
        *args: Positional arguments for send_notification_all_channels
        **kwargs: Keyword arguments for send_notification_all_channels
    
    Returns:
        bool: True if notification was sent, False otherwise
    """
    try:
        # Lazy import to avoid circular dependency
        from .tasks import send_notification_all_channels
        
        # Try to send notification asynchronously via Celery
        send_notification_all_channels.delay(*args, **kwargs)
        return True
    except Exception as e:
        # If Celery is not available (e.g., during tests), try synchronous execution
        logger.warning(f"Could not send notification asynchronously: {str(e)}")
        try:
            # Lazy import to avoid circular dependency
            from .tasks import send_notification_all_channels
            
            # Fallback to synchronous execution
            send_notification_all_channels(*args, **kwargs)
            return True
        except Exception as sync_error:
            # If synchronous execution also fails, log and continue
            logger.error(f"Could not send notification synchronously: {str(sync_error)}")
            return False
