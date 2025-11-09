

"""
FILE LOCATION: rides/utils.py

Helper functions for rides app.
"""
from decimal import Decimal
from typing import List, Dict, Tuple
import math


def find_nearby_drivers(
    pickup_lat: float,
    pickup_lon: float,
    max_distance_km: float = 5.0,
    vehicle_type: str = None
) -> List:
    """
    Find available drivers near pickup location.
    
    Args:
        pickup_lat: Pickup latitude
        pickup_lon: Pickup longitude
        max_distance_km: Maximum search radius
        vehicle_type: Filter by vehicle type
    
    Returns:
        List of Driver objects sorted by distance
    """
    from drivers.models import Driver
    from common_utils import calculate_distance
    
    # Get all available drivers
    drivers = Driver.objects.filter(
        status='approved',
        is_online=True,
        is_available=True
    ).select_related('user')
    
    if vehicle_type:
        drivers = drivers.filter(vehicle_type=vehicle_type)
    
    # Calculate distances and filter
    nearby_drivers = []
    
    for driver in drivers:
        # TODO: Get driver's current location from cache/database
        # For now, use a placeholder
        driver_lat = 0.0  # Would come from driver's last location update
        driver_lon = 0.0
        
        # distance = calculate_distance(
        #     pickup_lat, pickup_lon,
        #     driver_lat, driver_lon
        # )
        
        # if distance <= max_distance_km:
        #     nearby_drivers.append((driver, distance))
        
        # Placeholder - return all for now
        nearby_drivers.append((driver, 0))
    
    # Sort by distance
    nearby_drivers.sort(key=lambda x: x[1])
    
    return [driver for driver, distance in nearby_drivers]


def calculate_estimated_time(
    pickup_lat: float,
    pickup_lon: float,
    dest_lat: float,
    dest_lon: float,
    avg_speed_kmh: float = 30.0
) -> int:
    """
    Calculate estimated ride duration.
    
    Args:
        pickup_lat: Pickup latitude
        pickup_lon: Pickup longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        avg_speed_kmh: Average speed
    
    Returns:
        Estimated duration in minutes
    """
    from common_utils import calculate_distance, estimate_duration
    
    distance = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
    duration = estimate_duration(distance, avg_speed_kmh)
    
    return duration


def calculate_base_fare(distance_km: Decimal) -> Decimal:
    """
    Calculate base fare based on distance.
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Base fare amount
    """
    BASE_FARE = Decimal('500.00')  # Base fare ₦500
    PRICE_PER_KM = Decimal('100.00')  # ₦100 per km
    
    fare = BASE_FARE + (distance_km * PRICE_PER_KM)
    return fare.quantize(Decimal('0.01'))


def apply_surge_pricing(base_fare: Decimal, surge_multiplier: Decimal = Decimal('1.0')) -> Decimal:
    """
    Apply surge pricing multiplier.
    
    Args:
        base_fare: Base fare amount
        surge_multiplier: Surge multiplier (1.0 = no surge, 2.0 = 2x)
    
    Returns:
        Final fare with surge applied
    """
    return (base_fare * surge_multiplier).quantize(Decimal('0.01'))


def calculate_cancellation_fee(
    ride_status: str,
    cancelled_by: str,
    minutes_since_accepted: int = 0
) -> Decimal:
    """
    Calculate cancellation fee.
    
    Rules:
    - Free cancellation within 2 minutes of acceptance
    - ₦200 fee after 2 minutes
    - ₦500 fee if driver already arriving
    - No fee if driver cancels
    
    Args:
        ride_status: Current ride status
        cancelled_by: Who cancelled (rider/driver/system)
        minutes_since_accepted: Minutes since driver accepted
    
    Returns:
        Cancellation fee amount
    """
    if cancelled_by == 'driver' or cancelled_by == 'system':
        return Decimal('0.00')
    
    if ride_status == 'pending':
        return Decimal('0.00')
    
    if ride_status == 'accepted':
        if minutes_since_accepted <= 2:
            return Decimal('0.00')
        else:
            return Decimal('200.00')
    
    if ride_status == 'arriving':
        return Decimal('500.00')
    
    if ride_status == 'in_progress':
        # Cannot cancel in progress ride
        return Decimal('0.00')
    
    return Decimal('0.00')


def validate_ride_locations(
    pickup_lat: float,
    pickup_lon: float,
    dest_lat: float,
    dest_lon: float
) -> Tuple[bool, str]:
    """
    Validate ride pickup and destination coordinates.
    
    Args:
        pickup_lat: Pickup latitude
        pickup_lon: Pickup longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check latitude bounds
    if not (-90 <= pickup_lat <= 90):
        return False, "Invalid pickup latitude"
    if not (-90 <= dest_lat <= 90):
        return False, "Invalid destination latitude"
    
    # Check longitude bounds
    if not (-180 <= pickup_lon <= 180):
        return False, "Invalid pickup longitude"
    if not (-180 <= dest_lon <= 180):
        return False, "Invalid destination longitude"
    
    # Check if pickup and destination are too close (less than 100m)
    from common_utils import calculate_distance
    distance = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
    
    if distance < 0.1:  # Less than 100 meters
        return False, "Pickup and destination are too close (minimum 100m)"
    
    # Check if distance is reasonable (max 500km for single ride)
    if distance > 500:
        return False, "Distance too far (maximum 500km)"
    
    return True, ""


def format_ride_eta(minutes: int) -> str:
    """
    Format ETA in a human-readable way.
    
    Args:
        minutes: ETA in minutes
    
    Returns:
        Formatted string
    """
    if minutes < 1:
        return "Arriving now"
    elif minutes == 1:
        return "1 minute away"
    elif minutes < 60:
        return f"{minutes} minutes away"
    else:
        hours = minutes // 60
        remaining_mins = minutes % 60
        if remaining_mins == 0:
            return f"{hours} hour{'s' if hours > 1 else ''} away"
        return f"{hours}h {remaining_mins}m away"


