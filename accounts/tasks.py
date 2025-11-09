
"""
FILE LOCATION: accounts/tasks.py

Celery tasks for accounts app.
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
