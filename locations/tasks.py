"""
FILE LOCATION: locations/tasks.py

Celery tasks for locations app.
Background jobs for cleanup and maintenance.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import DriverLocation, RideTracking
from .services import cleanup_old_tracking_points
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_ride_tracking():
    """
    Delete old ride tracking points (older than 30 days).
    Run this task daily via Celery Beat.
    """
    try:
        deleted_count = cleanup_old_tracking_points(days=30)
        
        logger.info(f"Cleaned up {deleted_count} old tracking points")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_ride_tracking: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def update_inactive_drivers():
    """
    Mark drivers as offline if their location hasn't been updated recently.
    Run this task every 5 minutes via Celery Beat.
    """
    try:
        cutoff_time = timezone.now() - timedelta(minutes=10)
        
        # Find driver locations that haven't been updated
        stale_locations = DriverLocation.objects.filter(
            last_updated__lt=cutoff_time,
            driver__is_online=True
        )
        
        updated_count = 0
        for driver_loc in stale_locations:
            driver = driver_loc.driver
            driver.is_online = False
            driver.is_available = False
            driver.save(update_fields=['is_online', 'is_available'])
            updated_count += 1
        
        if updated_count > 0:
            logger.info(f"Marked {updated_count} drivers as offline due to stale location")
        
        return {
            'success': True,
            'updated_count': updated_count
        }
        
    except Exception as e:
        logger.error(f"Error in update_inactive_drivers: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_location_statistics():
    """
    Generate daily location statistics.
    Run this task daily via Celery Beat.
    """
    try:
        from datetime import date
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get statistics
        active_drivers = DriverLocation.objects.filter(
            last_updated__date=yesterday,
            driver__is_online=True
        ).count()
        
        tracking_points = RideTracking.objects.filter(
            timestamp__date=yesterday
        ).count()
        
        rides_tracked = RideTracking.objects.filter(
            timestamp__date=yesterday
        ).values('ride').distinct().count()
        
        logger.info(
            f"Daily location stats - Active drivers: {active_drivers}, "
            f"Tracking points: {tracking_points}, Rides tracked: {rides_tracked}"
        )
        
        return {
            'success': True,
            'date': str(yesterday),
            'active_drivers': active_drivers,
            'tracking_points': tracking_points,
            'rides_tracked': rides_tracked
        }
        
    except Exception as e:
        logger.error(f"Error in generate_location_statistics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


