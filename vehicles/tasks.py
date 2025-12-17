
"""
FILE LOCATION: vehicles/tasks.py
Celery tasks for vehicles app.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_vehicle_expirations():
    """Check for expired documents and send reminders"""
    from .models import Vehicle
    
    today = timezone.now().date()
    
    # Check registration expiry
    expired_reg = Vehicle.objects.filter(
        registration_expiry__lte=today,
        is_active=True
    )
    
    for vehicle in expired_reg:
        logger.warning(f"Vehicle {vehicle.license_plate} registration expired")
        
        # Notify driver
        try:
            from notifications.tasks import send_notification_all_channels
            send_notification_all_channels.delay(
                user_id=vehicle.driver.user.id,
                notification_type='vehicle_registration_expired',
                title='⚠️ Vehicle Registration Expired',
                body=f'Your vehicle ({vehicle.license_plate}) registration has expired. Please renew it to continue driving.',
                send_push=True
            )
            logger.info(f"Sent registration expiry notification for {vehicle.license_plate}")
        except Exception as e:
            logger.error(f"Failed to send registration expiry notification: {str(e)}")
    
    # Check insurance expiry
    expired_insurance = Vehicle.objects.filter(
        insurance_expiry__lte=today,
        is_active=True
    )
    
    for vehicle in expired_insurance:
        logger.warning(f"Vehicle {vehicle.license_plate} insurance expired")
        
        # Notify driver & deactivate vehicle
        try:
            from notifications.tasks import send_notification_all_channels
            send_notification_all_channels.delay(
                user_id=vehicle.driver.user.id,
                notification_type='vehicle_insurance_expired',
                title='🚨 Vehicle Insurance Expired - Vehicle Deactivated',
                body=f'Your vehicle ({vehicle.license_plate}) insurance has expired and has been deactivated. You cannot accept rides until insurance is renewed.',
                send_push=True,
                send_sms=True
            )
            logger.info(f"Sent insurance expiry notification for {vehicle.license_plate}")
        except Exception as e:
            logger.error(f"Failed to send insurance expiry notification: {str(e)}")
        
        vehicle.is_active = False
        vehicle.save()
    
    return {
        'expired_registrations': expired_reg.count(),
        'expired_insurance': expired_insurance.count()
    }


@shared_task
def update_vehicle_statistics():
    """Update vehicle ride statistics"""
    from .models import Vehicle
    from rides.models import Ride
    from django.db.models import Sum, Count
    
    for vehicle in Vehicle.objects.filter(is_active=True):
        stats = Ride.objects.filter(
            vehicle=vehicle,
            status='completed'
        ).aggregate(
            total_rides=Count('id'),
            total_distance=Sum('distance_km')
        )
        
        vehicle.total_rides = stats['total_rides'] or 0
        vehicle.total_distance_km = stats['total_distance'] or 0
        vehicle.save(update_fields=['total_rides', 'total_distance_km'])
    
    return {'success': True}


