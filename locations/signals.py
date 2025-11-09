
"""
FILE LOCATION: locations/signals.py

Signal handlers for locations app.
Connects location tracking to rides, drivers, and notifications.

CRITICAL INTEGRATIONS:
- Auto-create DriverLocation when driver goes online
- Track ride routes when ride is in progress
- Trigger geofence notifications (driver arrived, etc.)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DriverLocation, RideTracking
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='drivers.Driver')
def driver_online_status_handler(sender, instance, **kwargs):
    """
    Handle driver going online/offline.
    Create/update DriverLocation when driver goes online.
    """
    if instance.is_online:
        try:
            # Create or get driver location
            driver_location, created = DriverLocation.objects.get_or_create(
                driver=instance
            )
            
            if created:
                logger.info(f"📍 DriverLocation created for driver {instance.id}")
            
            # Driver is online and ready to receive location updates
            logger.info(f"🟢 Driver {instance.id} is ONLINE - Location tracking active")
            
        except Exception as e:
            logger.error(f"Error creating driver location: {str(e)}")
    else:
        logger.info(f"🔴 Driver {instance.id} is OFFLINE - Location tracking paused")


@receiver(post_save, sender='rides.Ride')
def ride_tracking_handler(sender, instance, created, **kwargs):
    """
    Handle ride tracking.
    Start tracking when ride begins, stop when completed.
    """
    # Start tracking when ride status is 'in_progress'
    if instance.status == 'in_progress':
        logger.info(f"🚗 Started tracking ride #{instance.id}")
        
        # Create initial tracking point
        try:
            if instance.driver and hasattr(instance.driver, 'current_location'):
                driver_loc = instance.driver.current_location
                
                RideTracking.objects.create(
                    ride=instance,
                    latitude=driver_loc.latitude,
                    longitude=driver_loc.longitude,
                    speed_kmh=driver_loc.speed_kmh,
                    bearing=driver_loc.bearing,
                    accuracy_meters=driver_loc.accuracy_meters
                )
                
                logger.info(f"📍 Initial tracking point recorded for ride #{instance.id}")
        except Exception as e:
            logger.error(f"Error creating initial tracking point: {str(e)}")
    
    # Calculate actual distance when ride completes
    elif instance.status == 'completed':
        try:
            # Get all tracking points
            tracking_points = RideTracking.objects.filter(ride=instance).order_by('timestamp')
            
            if tracking_points.count() > 1:
                # Calculate total distance from tracking points
                from .services import calculate_route_distance
                
                total_distance = calculate_route_distance(tracking_points)
                
                logger.info(f"✅ Ride #{instance.id} completed - Actual distance: {total_distance}km")
                
                # You could store this in the ride model if needed
                # instance.actual_distance = total_distance
                # instance.save()
            
        except Exception as e:
            logger.error(f"Error calculating ride distance: {str(e)}")


@receiver(post_save, sender=DriverLocation)
def driver_location_updated_handler(sender, instance, created, **kwargs):
    """
    Handle driver location updates.
    Check for geofence events (driver approaching, driver arrived).
    """
    if not created:  # Only for updates, not creation
        driver = instance.driver
        
        # Check if driver has active ride
        try:
            from rides.models import Ride
            
            active_ride = Ride.objects.filter(
                driver=driver,
                status__in=['accepted', 'driver_arrived']
            ).first()
            
            if active_ride:
                # Calculate distance to pickup location
                from .services import calculate_distance
                
                distance = calculate_distance(
                    float(instance.latitude),
                    float(instance.longitude),
                    float(active_ride.pickup_latitude),
                    float(active_ride.pickup_longitude)
                )
                
                # Check geofences
                # Driver approaching (within 2km)
                if 0.5 < distance <= 2.0 and active_ride.status == 'accepted':
                    # Send notification
                    try:
                        from notifications.tasks import send_notification_all_channels
                        
                        send_notification_all_channels.delay(
                            user_id=active_ride.user.id,
                            notification_type='driver_approaching',
                            title='Driver Approaching 🚗',
                            body=f'Your driver is {distance:.1f}km away',
                            send_push=True,
                            data={
                                'ride_id': active_ride.id,
                                'distance_km': round(distance, 2)
                            }
                        )
                        
                        logger.info(f"📢 Driver approaching notification sent for ride #{active_ride.id}")
                    except ImportError:
                        pass
                
                # Driver arrived (within 100m)
                elif distance <= 0.1 and active_ride.status != 'driver_arrived':
                    # Update ride status
                    active_ride.status = 'driver_arrived'
                    active_ride.save()
                    
                    # Send notification
                    try:
                        from notifications.tasks import send_notification_all_channels
                        
                        send_notification_all_channels.delay(
                            user_id=active_ride.user.id,
                            notification_type='driver_arrived',
                            title='Driver Arrived! 📍',
                            body='Your driver has arrived at the pickup location',
                            send_push=True,
                            send_sms=True,
                            data={'ride_id': active_ride.id}
                        )
                        
                        logger.info(f"✅ Driver arrived notification sent for ride #{active_ride.id}")
                    except ImportError:
                        pass
        
        except Exception as e:
            logger.error(f"Error in driver location update handler: {str(e)}")


# Track ride route in real-time
@receiver(post_save, sender=DriverLocation)
def track_active_ride_route(sender, instance, created, **kwargs):
    """
    Track ride route by creating tracking points during active ride.
    """
    if not created:  # Only for updates
        try:
            from rides.models import Ride
            
            # Check if driver has ride in progress
            active_ride = Ride.objects.filter(
                driver=instance.driver,
                status='in_progress'
            ).first()
            
            if active_ride:
                # Create tracking point
                RideTracking.objects.create(
                    ride=active_ride,
                    latitude=instance.latitude,
                    longitude=instance.longitude,
                    speed_kmh=instance.speed_kmh,
                    bearing=instance.bearing,
                    accuracy_meters=instance.accuracy_meters
                )
                
                logger.debug(f"📍 Tracking point recorded for ride #{active_ride.id}")
        
        except Exception as e:
            logger.error(f"Error tracking ride route: {str(e)}")


