

"""
FILE LOCATION: rides/tasks.py

Celery background tasks for rides app.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def expire_pending_ride_requests():
    """
    Expire ride requests that haven't been accepted.
    Runs every minute.
    """
    from .models import RideRequest, Ride
    
    now = timezone.now()
    
    # Find expired requests
    expired_requests = RideRequest.objects.filter(
        status='available',
        expires_at__lt=now
    )
    
    count = 0
    for request in expired_requests:
        # Mark request as expired
        request.status = 'expired'
        request.save()
        
        # Cancel the ride if still pending
        ride = request.ride
        if ride.status == 'pending':
            ride.status = 'cancelled'
            ride.cancelled_by = 'system'
            ride.cancellation_reason = 'No driver found within time limit'
            ride.cancelled_at = now
            ride.save()
            count += 1
            
            logger.info(f"Auto-cancelled ride #{ride.id} - no driver found")
            
            # TODO: Notify rider
    
    logger.info(f"Expired {expired_requests.count()} ride requests, cancelled {count} rides")
    return {'expired_requests': expired_requests.count(), 'cancelled_rides': count}


@shared_task
def cleanup_old_rides():
    """
    Archive old completed/cancelled rides (older than 90 days).
    Runs daily.
    """
    from .models import Ride
    
    ninety_days_ago = timezone.now() - timedelta(days=90)
    
    old_rides = Ride.objects.filter(
        status__in=['completed', 'cancelled'],
        created_at__lt=ninety_days_ago
    )
    
    count = old_rides.count()
    
    # TODO: Archive to separate table or storage
    # For now, just log
    logger.info(f"Found {count} old rides to archive")
    
    return {'old_rides_count': count}


@shared_task
def update_surge_pricing():
    """
    Calculate surge pricing based on demand.
    Runs every 5 minutes.
    """
    from .models import Ride, RideRequest
    from django.db.models import Count
    
    # Get recent ride requests (last 15 minutes)
    fifteen_min_ago = timezone.now() - timedelta(minutes=15)
    recent_requests = RideRequest.objects.filter(
        created_at__gte=fifteen_min_ago,
        status='available'
    ).count()
    
    # Count available drivers
    from drivers.models import Driver
    available_drivers = Driver.objects.filter(
        status='approved',
        is_online=True,
        is_available=True
    ).count()
    
    # Calculate surge
    if available_drivers > 0:
        demand_ratio = recent_requests / available_drivers
        surge_multiplier = 1.0
        
        if demand_ratio > 3:
            surge_multiplier = 2.0
        elif demand_ratio > 2:
            surge_multiplier = 1.5
        elif demand_ratio > 1:
            surge_multiplier = 1.2
        
        logger.info(f"Surge pricing: {surge_multiplier}x (requests: {recent_requests}, drivers: {available_drivers})")
        
        # TODO: Store surge data in cache or database
        from django.core.cache import cache
        cache.set('current_surge_multiplier', surge_multiplier, timeout=300)
    
    return {
        'requests': recent_requests,
        'drivers': available_drivers,
        'surge': surge_multiplier if available_drivers > 0 else 1.0
    }


@shared_task
def send_ride_reminders():
    """
    Send reminders for scheduled rides.
    Runs every hour.
    """
    from .models import Ride
    
    # Find scheduled rides happening in 1 hour
    one_hour_from_now = timezone.now() + timedelta(hours=1)
    two_hours_from_now = timezone.now() + timedelta(hours=2)
    
    upcoming_rides = Ride.objects.filter(
        ride_type='scheduled',
        status='pending',
        scheduled_time__gte=one_hour_from_now,
        scheduled_time__lte=two_hours_from_now
    )
    
    for ride in upcoming_rides:
        # TODO: Send reminder notification
        logger.info(f"Reminder: Ride #{ride.id} scheduled at {ride.scheduled_time}")
    
    return {'reminders_sent': upcoming_rides.count()}


@shared_task
def calculate_driver_earnings():
    """
    Calculate and update driver earnings.
    Runs daily.
    """
    from drivers.models import Driver
    from .models import Ride
    from django.db.models import Sum
    from datetime import date
    
    today = date.today()
    
    for driver in Driver.objects.filter(status='approved'):
        # Calculate today's earnings
        today_earnings = Ride.objects.filter(
            driver=driver,
            status='completed',
            completed_at__date=today
        ).aggregate(Sum('fare_amount'))['fare_amount__sum'] or 0
        
        # Update driver's total earnings
        driver.total_earnings += today_earnings
        driver.save(update_fields=['total_earnings'])
        
        logger.info(f"Driver {driver.id} earned ₦{today_earnings} today")
    
    return {'success': True}


