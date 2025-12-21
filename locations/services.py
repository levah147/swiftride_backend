"""
FILE LOCATION: locations/services.py

Service layer for location business logic.
GPS tracking, distance calculations, geofencing, etc.
"""
from django.db.models import Q
from django.utils import timezone
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
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return round(distance, 2)


def update_driver_location(driver, latitude, longitude, bearing=None, speed_kmh=None, accuracy_meters=None):
    """
    Update driver's current location.
    
    Args:
        driver: Driver object
        latitude: Latitude
        longitude: Longitude
        bearing: Heading/bearing in degrees (optional)
        speed_kmh: Speed in km/h (optional)
        accuracy_meters: GPS accuracy in meters (optional)
    
    Returns:
        DriverLocation: Updated location object
    """
    from .models import DriverLocation
    
    try:
        location, created = DriverLocation.objects.update_or_create(
            driver=driver,
            defaults={
                'latitude': Decimal(str(latitude)),
                'longitude': Decimal(str(longitude)),
                # ✅ FIX #4: Use 'is not None' to handle 0 values correctly
                'bearing': Decimal(str(bearing)) if bearing is not None else None,
                'speed_kmh': Decimal(str(speed_kmh)) if speed_kmh is not None else None,
                'accuracy_meters': Decimal(str(accuracy_meters)) if accuracy_meters is not None else None
            }
        )
        
        # Update driver's last_location_update timestamp
        driver.last_location_update = timezone.now()
        driver.save(update_fields=['last_location_update'])
        
        logger.info(f"Location updated for driver {driver.id}")
        
        return location
        
    except Exception as e:
        logger.error(f"Error updating driver location: {str(e)}")
        return None


def get_nearby_drivers(latitude, longitude, radius_km=10, vehicle_type=None):
    """
    Find nearby online drivers.
    
    Args:
        latitude: Search center latitude
        longitude: Search center longitude
        radius_km: Search radius in kilometers
        vehicle_type: Vehicle type slug or ID (optional) - e.g., 'car', 'bike', 'keke', 'suv'
    
    Returns:
        list: List of nearby drivers with distances
    """
    from .models import DriverLocation
    from datetime import timedelta
    
    try:
        # Get drivers with recent location updates
        from django.conf import settings
        stale_minutes = settings.RIDE_SETTINGS.get('DRIVER_LOCATION_STALE_MINUTES', 5)
        cutoff_time = timezone.now() - timedelta(minutes=stale_minutes)
        
        driver_locations = DriverLocation.objects.filter(
            driver__status='approved',
            driver__is_online=True,
            driver__is_available=True,
            last_updated__gte=cutoff_time
        ).select_related('driver__user', 'driver__current_vehicle', 'driver__current_vehicle__vehicle_type')
        
        # ✅ Filter by vehicle type (supports ID or name)
        if vehicle_type:
            # Filter by ID (primary key) or name
            # Note: VehicleType.id is a CharField primary key (e.g., 'car', 'bike')
            driver_locations = driver_locations.filter(
                Q(driver__current_vehicle__vehicle_type__id=vehicle_type) |
                Q(driver__current_vehicle__vehicle_type__name__iexact=vehicle_type),
                driver__current_vehicle__is_verified=True,
                driver__current_vehicle__is_active=True,
            ).filter(
                driver__current_vehicle__isnull=False  # Ensure vehicle exists
            )
        
        # Calculate distances
        nearby_drivers = []
        for driver_loc in driver_locations:
            distance = calculate_distance(
                latitude, longitude,
                float(driver_loc.latitude), float(driver_loc.longitude)
            )
            
            if distance <= radius_km:
                # ✅ FIX #2: Safe access to current_vehicle (guard against None)
                vehicle = driver_loc.driver.current_vehicle
                
                nearby_drivers.append({
                    'driver': driver_loc.driver,
                    'driver_location': driver_loc,
                    'distance_km': distance,
                    'latitude': float(driver_loc.latitude),
                    'longitude': float(driver_loc.longitude),
                    # Additional useful data
                    'driver_id': driver_loc.driver.id,
                    'driver_name': driver_loc.driver.user.get_full_name() or driver_loc.driver.user.phone_number,
                    'driver_phone': driver_loc.driver.user.phone_number,
                    'driver_rating': float(driver_loc.driver.rating) if driver_loc.driver.rating else 0.0,
                    # Safe vehicle access
                    'vehicle_type': vehicle.vehicle_type.name if vehicle and hasattr(vehicle, 'vehicle_type') and vehicle.vehicle_type else None,
                    'vehicle_model': f"{vehicle.make} {vehicle.model}" if vehicle else None,
                    'vehicle_color': vehicle.color if vehicle else None,
                    'license_plate': vehicle.license_plate if vehicle else None,
                })
        
        # Sort by distance (closest first)
        nearby_drivers.sort(key=lambda x: x['distance_km'])
        
        logger.info(f"Found {len(nearby_drivers)} drivers within {radius_km}km")
        
        return nearby_drivers
        
    except Exception as e:
        logger.error(f"Error finding nearby drivers: {str(e)}")
        return []


def calculate_eta(driver_location, destination_lat, destination_lng, average_speed_kmh=30):
    """
    Calculate estimated time of arrival.
    
    Args:
        driver_location: DriverLocation object
        destination_lat: Destination latitude
        destination_lng: Destination longitude
        average_speed_kmh: Average speed (default 30 km/h)
    
    Returns:
        dict: ETA information
    """
    try:
        distance_km = calculate_distance(
            float(driver_location.latitude),
            float(driver_location.longitude),
            destination_lat,
            destination_lng
        )
        
        # Calculate time in minutes
        eta_minutes = int((distance_km / average_speed_kmh) * 60)
        
        # Add buffer time (traffic, stops, etc.)
        eta_minutes = int(eta_minutes * 1.2)  # 20% buffer
        
        return {
            'distance_km': distance_km,
            'eta_minutes': eta_minutes,
            'eta_formatted': f"{eta_minutes} mins" if eta_minutes < 60 else f"{eta_minutes // 60}h {eta_minutes % 60}m"
        }
        
    except Exception as e:
        logger.error(f"Error calculating ETA: {str(e)}")
        return None


def track_ride_location(ride, latitude, longitude, speed_kmh=None, bearing=None, accuracy_meters=None):
    """
    Record a tracking point for a ride.
    
    Args:
        ride: Ride object
        latitude: Latitude
        longitude: Longitude
        speed_kmh: Speed (optional)
        bearing: Bearing (optional)
        accuracy_meters: GPS accuracy (optional)
    
    Returns:
        RideTracking: Created tracking point
    """
    from .models import RideTracking
    
    try:
        tracking_point = RideTracking.objects.create(
            ride=ride,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            # ✅ FIX #4: Use 'is not None' to handle 0 values correctly
            speed_kmh=Decimal(str(speed_kmh)) if speed_kmh is not None else None,
            bearing=Decimal(str(bearing)) if bearing is not None else None,
            accuracy_meters=Decimal(str(accuracy_meters)) if accuracy_meters is not None else None
        )
        
        logger.debug(f"Tracking point recorded for ride #{ride.id}")
        
        return tracking_point
        
    except Exception as e:
        logger.error(f"Error tracking ride location: {str(e)}")
        return None


def calculate_route_distance(tracking_points):
    """
    Calculate total distance from tracking points.
    
    Args:
        tracking_points: QuerySet of RideTracking objects
    
    Returns:
        float: Total distance in kilometers
    """
    try:
        # ✅ FIX #5: Fetch data once, check length in memory
        points = list(tracking_points.order_by('timestamp'))
        
        if len(points) < 2:
            return 0.0
        
        total_distance = 0.0
        
        for i in range(len(points) - 1):
            distance = calculate_distance(
                float(points[i].latitude),
                float(points[i].longitude),
                float(points[i + 1].latitude),
                float(points[i + 1].longitude)
            )
            total_distance += distance
        
        return round(total_distance, 2)
        
    except Exception as e:
        logger.error(f"Error calculating route distance: {str(e)}")
        return 0.0


def check_geofence(latitude, longitude, center_lat, center_lng, radius_meters):
    """
    Check if point is within geofence.
    
    Args:
        latitude, longitude: Point to check
        center_lat, center_lng: Geofence center
        radius_meters: Geofence radius in meters
    
    Returns:
        tuple: (is_inside, distance_meters)
    """
    try:
        distance_km = calculate_distance(latitude, longitude, center_lat, center_lng)
        distance_meters = distance_km * 1000
        
        is_inside = distance_meters <= radius_meters
        
        return is_inside, round(distance_meters, 2)
        
    except Exception as e:
        logger.error(f"Error checking geofence: {str(e)}")
        return False, 0.0


def get_ride_route(ride_id):
    """
    Get all tracking points for a ride.
    
    Args:
        ride_id: Ride ID
    
    Returns:
        list: List of tracking points
    """
    from .models import RideTracking
    
    try:
        tracking_points = RideTracking.objects.filter(
            ride_id=ride_id
        ).order_by('timestamp')
        
        route = []
        for point in tracking_points:
            route.append({
                'latitude': float(point.latitude),
                'longitude': float(point.longitude),
                'speed_kmh': float(point.speed_kmh) if point.speed_kmh else 0,
                'bearing': float(point.bearing) if point.bearing else 0,
                'timestamp': point.timestamp.isoformat()
            })
        
        return route
        
    except Exception as e:
        logger.error(f"Error getting ride route: {str(e)}")
        return []


def save_favorite_location(user, location_type, address, latitude, longitude):
    """
    Save a favorite location for user.
    
    Args:
        user: User object
        location_type: 'home', 'work', or 'other'
        address: Address string
        latitude: Latitude
        longitude: Longitude
    
    Returns:
        SavedLocation: Created location
    """
    from .models import SavedLocation
    
    try:
        location, created = SavedLocation.objects.update_or_create(
            user=user,
            location_type=location_type,
            defaults={
                'address': address,
                'latitude': Decimal(str(latitude)),
                'longitude': Decimal(str(longitude)),
                'is_active': True
            }
        )
        
        logger.info(f"Saved {location_type} location for user {user.id}")
        
        return location
        
    except Exception as e:
        logger.error(f"Error saving favorite location: {str(e)}")
        return None


def add_recent_location(user, address, latitude, longitude):
    """
    Add or update recent location for user.
    
    Args:
        user: User object
        address: Address string
        latitude: Latitude
        longitude: Longitude
    
    Returns:
        RecentLocation: Created/updated location
    """
    from .models import RecentLocation
    
    try:
        location, created = RecentLocation.objects.get_or_create(
            user=user,
            address=address,
            defaults={
                'latitude': Decimal(str(latitude)),
                'longitude': Decimal(str(longitude))
            }
        )
        
        if not created:
            # Increment search count
            location.search_count += 1
            location.save(update_fields=['search_count'])
        
        logger.info(f"Recent location updated for user {user.id}")
        
        return location
        
    except Exception as e:
        logger.error(f"Error adding recent location: {str(e)}")
        return None


def cleanup_old_tracking_points(days=30):
    """
    Delete old ride tracking points.
    
    Args:
        days: Delete tracking older than this many days
    
    Returns:
        int: Number of points deleted
    """
    from .models import RideTracking
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count = RideTracking.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Deleted {deleted_count} old tracking points")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up tracking points: {str(e)}")
        return 0


def get_driver_location_history(driver, hours=24):
    """
    Get driver's location history.
    
    Args:
        driver: Driver object
        hours: Last N hours
    
    Returns:
        list: Location history
    """
    from .models import RideTracking
    from datetime import timedelta
    
    try:
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get all rides by driver
        tracking_points = RideTracking.objects.filter(
            ride__driver=driver,
            timestamp__gte=cutoff_time
        ).order_by('timestamp')
        
        history = []
        for point in tracking_points:
            history.append({
                'latitude': float(point.latitude),
                'longitude': float(point.longitude),
                'timestamp': point.timestamp.isoformat(),
                'ride_id': point.ride_id
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting location history: {str(e)}")
        return []