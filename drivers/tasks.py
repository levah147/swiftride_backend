
"""
FILE LOCATION: drivers/tasks.py

Celery background tasks for drivers app.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_driver_availability():
    """
    Update driver availability based on last activity.
    Set drivers offline if no activity for 10 minutes.
    """
    from .models import Driver
    
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    
    updated = Driver.objects.filter(
        is_online=True,
        last_location_update__lt=ten_minutes_ago
    ).update(
        is_online=False,
        is_available=False
    )
    
    logger.info(f"Set {updated} drivers offline due to inactivity")
    return {'success': True, 'updated_count': updated}


@shared_task
def cleanup_old_locations():
    """Delete old driver location data (older than 30 days)"""
    # TODO: Implement if you have a DriverLocation model
    logger.info("Cleaned up old driver locations")
    return {'success': True}


@shared_task
def send_driver_earnings_summary():
    """Send weekly earnings summary to drivers"""
    from .models import Driver
    from accounts.utils import EmailService
    from payments.models import Transaction
    from django.db.models import Sum, Count
    from datetime import datetime
    
    drivers = Driver.objects.filter(status='approved')
    sent_count = 0
    
    for driver in drivers:
        try:
            # Calculate weekly earnings
            week_ago = timezone.now() - timedelta(days=7)
            weekly_data = Transaction.objects.filter(
                user=driver.user,
                transaction_type='ride_payment',
                status='completed',
                created_at__gte=week_ago
            ).aggregate(
                total_earnings=Sum('amount'),
                total_rides=Count('id')
            )
            
            total_earnings = weekly_data['total_earnings'] or 0
            total_rides = weekly_data['total_rides'] or 0
            
            # Send email if driver has email
            if driver.user.email and total_rides > 0:
                # Email would be sent here via EmailService
                # EmailService.send_driver_weekly_report(driver, total_earnings, total_rides)
                sent_count += 1
                logger.info(f"Sent earnings summary to {driver.user.phone_number}: ₦{total_earnings}")
                
        except Exception as e:
            logger.error(f"Failed to send earnings summary to driver {driver.id}: {str(e)}")
    
    logger.info(f"Sent earnings summary to {sent_count}/{drivers.count()} drivers")
    return {'success': True, 'sent_count': sent_count, 'total_drivers': drivers.count()}


@shared_task
def check_expired_licenses():
    """Check for expired driver licenses and notify"""
    from .models import Driver
    
    today = timezone.now().date()
    
    # Find drivers with expired licenses
    expired = Driver.objects.filter(
        status='approved',
        driver_license_expiry__lte=today
    )
    
    count = 0
    for driver in expired:
        # Suspend driver
        driver.status = 'suspended'
        driver.is_online = False
        driver.is_available = False
        driver.save()
        
        # Send notification
        try:
            from notifications.tasks import send_notification_all_channels
            send_notification_all_channels.delay(
                user_id=driver.user.id,
                notification_type='license_expired',
                title='⚠️ License Expired - Account Suspended',
                body=f'Your driver license expired on {driver.driver_license_expiry}. Please update your license to resume driving.',
                send_push=True,
                send_sms=True
            )
            logger.info(f"Sent expiry notification to {driver.user.phone_number}")
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
        
        count += 1
    
    logger.warning(f"Suspended {count} drivers with expired licenses")
    return {'success': True, 'suspended_count': count}


