
"""
FILE LOCATION: admin_dashboard/tasks.py

Background tasks for admin dashboard.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_admin_report():
    """Generate daily report for admins"""
    from .services import get_platform_overview
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        stats = get_platform_overview()
        
        # Send to all admins
        admins = User.objects.filter(is_staff=True, is_active=True)
        
        for admin in admins:
            try:
                from notifications.tasks import send_notification_all_channels
                
                send_notification_all_channels.delay(
                    user_id=admin.id,
                    notification_type='admin_daily_report',
                    title='Daily Platform Report 📊',
                    body=f"Today: {stats['today_rides']} rides, ₦{stats['today_revenue']} revenue",
                    send_email=True,
                    data=stats
                )
            except:
                pass
        
        logger.info(f"📊 Daily admin report sent to {admins.count()} admins")
        
        return {'success': True, 'recipients': admins.count()}
        
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_logs():
    """Clean up old admin action logs (>1 year)"""
    from .models import AdminActionLog
    
    try:
        cutoff_date = timezone.now() - timedelta(days=365)
        
        deleted = AdminActionLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"🗑️ Cleaned up {deleted} old admin logs")
        
        return {'success': True, 'deleted': deleted}
        
    except Exception as e:
        logger.error(f"Error cleaning logs: {str(e)}")
        return {'success': False, 'error': str(e)}



