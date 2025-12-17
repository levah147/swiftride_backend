"""
FILE LOCATION: rides/services.py

Service layer for rides business logic.
Handles ride matching, driver finding, fare calculations, etc.
"""
from django.db.models import Q, F
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import math
import logging

logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
    
    Returns:
        float: Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return round(distance, 2)


def find_nearby_drivers(
    pickup_latitude,
    pickup_longitude,
    radius_km=10,
    vehicle_type=None,
    limit=10
):
    """
    Find nearby available drivers using locations app.
    
    Args:
        pickup_latitude: Pickup location latitude
        pickup_longitude: Pickup location longitude
        radius_km: Search radius in kilometers (default: 10km)
        vehicle_type: VehicleType object or ID to filter by (optional)
        limit: Maximum number of drivers to return (default: 10)
    
    Returns:
        list: List of driver dictionaries with distance info
        
    Example:
        >>> drivers = find_nearby_drivers(7.7300, 8.5375, radius_km=5, vehicle_type='car')
        >>> print(f"Found {len(drivers)} drivers")
        >>> for driver in drivers:
        >>>     print(f"{driver['driver'].user.phone_number} - {driver['distance_km']}km away")
    """
    from locations.services import get_nearby_drivers as get_nearby_drivers_location
    
    try:
        # ✅ Use locations app to find nearby drivers
        nearby_drivers = get_nearby_drivers_location(
            latitude=pickup_latitude,
            longitude=pickup_longitude,
            radius_km=radius_km,
            vehicle_type=vehicle_type
        )
        
        # Limit results
        nearby_drivers = nearby_drivers[:limit]
        
        logger.info(
            f"Found {len(nearby_drivers)} drivers within {radius_km}km "
            f"of ({pickup_latitude}, {pickup_longitude})"
        )
        
        return nearby_drivers
        
    except Exception as e:
        logger.error(f"Error finding nearby drivers: {str(e)}")
        return []


def notify_nearby_drivers(ride):
    """
    Notify nearby drivers about a new ride request.
    
    Args:
        ride: Ride object
    
    Returns:
        int: Number of drivers notified
    """
    try:
        # Find nearby drivers
        nearby_drivers = find_nearby_drivers(
            pickup_latitude=ride.pickup_latitude,
            pickup_longitude=ride.pickup_longitude,
            radius_km=ride.city.minimum_driver_radius_km if ride.city else 10,
            vehicle_type=ride.vehicle_type.id if ride.vehicle_type else None,
            limit=20  # Notify up to 20 nearest drivers
        )
        
        if not nearby_drivers:
            logger.warning(f"No nearby drivers found for ride {ride.id}")
            return 0
        
        # Create ride requests for each driver
        from .models import RideRequest
        notified_count = 0
        
        for driver_data in nearby_drivers:
            driver = driver_data['driver']
            distance_km = driver_data['distance_km']
            
            # Skip if driver already has an active ride
            if driver.is_available:
                # Create ride request
                RideRequest.objects.create(
                    ride=ride,
                    driver=driver,
                    distance_km=distance_km,
                    status='pending'
                )
                
                # ✅ Send push notification
                try:
                    from notifications.tasks import send_notification_all_channels
                    send_notification_all_channels.delay(
                        user_id=driver.user.id,
                        notification_type='new_ride_request',
                        title='New Ride Request! 🚗',
                        body=f'{distance_km:.1f}km away - ₦{ride.total_fare}',
                        send_push=True,
                        data={
                            'ride_id': str(ride.id),
                            'distance_km': distance_km,
                            'fare': str(ride.total_fare),
                            'pickup_address': ride.pickup_address
                        }
                    )
                    notified_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to driver {driver.id}: {str(e)}")
        
        logger.info(f"Notified {notified_count} drivers for ride {ride.id}")
        return notified_count
        
    except Exception as e:
        logger.error(f"Error notifying drivers: {str(e)}")
        return 0


def create_ride_request(ride):
    """
    Create ride requests for nearby drivers.
    
    Args:
        ride: Ride object
    
    Returns:
        int: Number of drivers notified
    """
    # ✅ Use the new notify_nearby_drivers function
    return notify_nearby_drivers(ride)


def assign_driver_to_ride(ride, driver):
    """
    Assign driver to a ride.
    
    Args:
        ride: Ride object
        driver: Driver object
    
    Returns:
        bool: Success status
    """
    try:
        with transaction.atomic():
            # Assign driver
            ride.driver = driver
            ride.status = 'accepted'
            ride.accepted_at = timezone.now()
            ride.save()
            
            # Mark driver as unavailable
            driver.is_available = False
            driver.save(update_fields=['is_available'])
            
            # Cancel other pending requests
            from .models import RideRequest
            RideRequest.objects.filter(
                ride=ride
            ).exclude(
                driver=driver
            ).update(status='cancelled')
            
            logger.info(f"Driver {driver.id} assigned to ride {ride.id}")
            return True
            
    except Exception as e:
        logger.error(f"Error assigning driver to ride: {str(e)}")
        return False


def calculate_driver_eta(driver, destination_lat, destination_lng):
    """
    Calculate estimated time for driver to reach destination.
    
    Args:
        driver: Driver object
        destination_lat: Destination latitude
        destination_lng: Destination longitude
    
    Returns:
        dict: {'distance_km': float, 'eta_minutes': int}
    """
    from locations.services import calculate_eta
    
    try:
        # Get driver's current location
        if not hasattr(driver, 'current_location'):
            return {'distance_km': 0, 'eta_minutes': 5}
        
        driver_location = driver.current_location
        
        # Calculate ETA using locations app
        eta_data = calculate_eta(
            driver_location=driver_location,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            average_speed_kmh=30  # City traffic speed
        )
        
        return eta_data
        
    except Exception as e:
        logger.error(f"Error calculating ETA: {str(e)}")
        return {'distance_km': 0, 'eta_minutes': 5}


def calculate_ride_eta(ride):
    """
    Calculate estimated time of arrival.
    
    Args:
        ride: Ride object
    
    Returns:
        int: ETA in minutes
    """
    if not ride.driver:
        return None
    
    try:
        # ✅ Use the new calculate_driver_eta function
        eta_data = calculate_driver_eta(
            driver=ride.driver,
            destination_lat=ride.pickup_latitude,
            destination_lng=ride.pickup_longitude
        )
        
        return eta_data.get('eta_minutes', 10)
        
    except Exception as e:
        logger.error(f"Error calculating ETA: {str(e)}")
        return None


def complete_ride(ride):
    """
    Complete a ride and perform post-ride actions.
    
    Args:
        ride: Ride object
    
    Returns:
        bool: Success status
    """
    try:
        with transaction.atomic():
            # Update ride status
            ride.status = 'completed'
            ride.completed_at = timezone.now()
            ride.save()
            
            # Make driver available again
            if ride.driver:
                ride.driver.is_available = True
                ride.driver.save(update_fields=['is_available'])
            
            logger.info(f"Ride {ride.id} completed")
            
            # Payment will be processed by signals
            # Rating placeholder will be created by signals
            
            return True
            
    except Exception as e:
        logger.error(f"Error completing ride: {str(e)}")
        return False


def cancel_ride(ride, cancelled_by, cancellation_reason=None):
    """
    Cancel a ride.
    
    Args:
        ride: Ride object
        cancelled_by: User who cancelled
        cancellation_reason: Reason for cancellation
    
    Returns:
        bool: Success status
    """
    try:
        with transaction.atomic():
            # Update ride
            ride.status = 'cancelled'
            ride.cancelled_by = cancelled_by
            ride.cancelled_at = timezone.now()
            
            if cancellation_reason:
                ride.cancellation_reason = cancellation_reason
            
            ride.save()
            
            # Make driver available if assigned
            if ride.driver:
                ride.driver.is_available = True
                ride.driver.save(update_fields=['is_available'])
            
            # Cancel all ride requests
            from .models import RideRequest
            RideRequest.objects.filter(ride=ride).update(status='cancelled')
            
            logger.info(f"Ride {ride.id} cancelled by {cancelled_by}")
            
            # Refund if payment already made (handled by payments app)
            
            return True
            
    except Exception as e:
        logger.error(f"Error cancelling ride: {str(e)}")
        return False


def calculate_ride_fare(pickup_lat, pickup_lng, dest_lat, dest_lng, vehicle_type):
    """
    Calculate ride fare.
    
    Args:
        pickup_lat, pickup_lng: Pickup coordinates
        dest_lat, dest_lng: Destination coordinates
        vehicle_type: Vehicle type
    
    Returns:
        dict: Fare breakdown
    """
    try:
        from pricing.services import calculate_fare
        
        # Calculate distance
        distance = calculate_distance(pickup_lat, pickup_lng, dest_lat, dest_lng)
        
        # Calculate fare using pricing service
        fare_data = calculate_fare(
            vehicle_type_id=vehicle_type,
            distance_km=distance,
            duration_minutes=int((distance / 30) * 60)  # Estimate duration
        )
        
        return fare_data
        
    except Exception as e:
        logger.error(f"Error calculating fare: {str(e)}")
        return {
            'base_fare': Decimal('0.00'),
            'distance_fare': Decimal('0.00'),
            'time_fare': Decimal('0.00'),
            'total_fare': Decimal('0.00')
        }


def get_ride_statistics(driver=None, rider=None):
    """
    Get ride statistics.
    
    Args:
        driver: Driver object (optional)
        rider: User object (optional)
    
    Returns:
        dict: Statistics
    """
    from .models import Ride
    
    try:
        rides = Ride.objects.all()
        
        if driver:
            rides = rides.filter(driver=driver)
        
        if rider:
            rides = rides.filter(user=rider)
        
        stats = {
            'total_rides': rides.count(),
            'completed_rides': rides.filter(status='completed').count(),
            'cancelled_rides': rides.filter(status='cancelled').count(),
            'total_earnings': sum([
                ride.fare_amount for ride in rides.filter(status='completed')
            ]),
            'average_rating': 0  # Calculate from ratings
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return {}


def validate_ride_request(pickup_lat, pickup_lng, dest_lat, dest_lng):
    """
    Validate ride request parameters.
    
    Args:
        pickup_lat, pickup_lng: Pickup coordinates
        dest_lat, dest_lng: Destination coordinates
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check coordinates are valid
    if not (-90 <= pickup_lat <= 90) or not (-180 <= pickup_lng <= 180):
        return False, "Invalid pickup coordinates"
    
    if not (-90 <= dest_lat <= 90) or not (-180 <= dest_lng <= 180):
        return False, "Invalid destination coordinates"
    
    # Check pickup and destination are different
    distance = calculate_distance(pickup_lat, pickup_lng, dest_lat, dest_lng)
    
    if distance < 0.5:  # Less than 500 meters
        return False, "Pickup and destination are too close"
    
    if distance > 100:  # More than 100 km
        return False, "Distance too far for this service"
    
    return True, None


def get_driver_current_ride(driver):
    """
    Get driver's current active ride.
    
    Args:
        driver: Driver object
    
    Returns:
        Ride: Current ride or None
    """
    from .models import Ride
    
    try:
        return Ride.objects.filter(
            driver=driver,
            status__in=['accepted', 'driver_arrived', 'in_progress']
        ).first()
    except Exception as e:
        logger.error(f"Error getting current ride: {str(e)}")
        return None


def get_rider_active_ride(user):
    """
    Get rider's active ride.
    
    Args:
        user: User object
    
    Returns:
        Ride: Active ride or None
    """
    from .models import Ride
    
    try:
        return Ride.objects.filter(
            user=user,
            status__in=['pending', 'accepted', 'driver_arrived', 'in_progress']
        ).first()
    except Exception as e:
        logger.error(f"Error getting active ride: {str(e)}")
        return None 