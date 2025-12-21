"""
FILE LOCATION: locations/views.py

API views for locations app.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import requests
from django.conf import settings

from .models import DriverLocation, SavedLocation, RecentLocation, RideTracking
from .serializers import SavedLocationSerializer, RecentLocationSerializer
from .services import (
    update_driver_location,
    get_nearby_drivers,
    calculate_distance,
    calculate_eta,
    track_ride_location,
    add_recent_location as add_recent_location_service
)


# ========================================
# Saved Locations
# ========================================

class SavedLocationListCreateView(generics.ListCreateAPIView):
    """List and create saved locations"""
    serializer_class = SavedLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedLocation.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedLocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete saved location"""
    serializer_class = SavedLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedLocation.objects.filter(user=self.request.user)


# ========================================
# Recent Locations
# ========================================

class RecentLocationListView(generics.ListAPIView):
    """List recent locations"""
    serializer_class = RecentLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RecentLocation.objects.filter(user=self.request.user)[:10]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_recent_location(request):
    """Add or update recent location"""
    address = request.data.get('address')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not all([address, latitude, longitude]):
        return Response(
            {'error': 'Address, latitude, and longitude are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use service
    location = add_recent_location_service(
        user=request.user,
        address=address,
        latitude=latitude,
        longitude=longitude
    )
    
    if location:
        serializer = RecentLocationSerializer(location)
        return Response(serializer.data)
    
    return Response(
        {'error': 'Failed to add recent location'},
        status=status.HTTP_400_BAD_REQUEST
    )


# ==================== views/location_views.py ====================
# BACKEND REVERSE GEOCODING - Add this to your Django backend
# Uses Nominatim (free, no API key) with fallback options

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import requests
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reverse_geocode(request):
    """
    Reverse geocode coordinates to get city name
    More reliable than device geocoding for Nigeria/Africa
    
    Query params:
        - lat: latitude (required)
        - lng: longitude (required)
    
    Returns:
        {
            "city": "Abuja",
            "state": "Federal Capital Territory",
            "country": "Nigeria",
            "display_name": "Full formatted address",
            "town": "...",  # Alternative to city
            "village": "..." # For rural areas
        }
    """
    try:
        # Get coordinates from query params
        latitude = request.GET.get('lat')
        longitude = request.GET.get('lng')
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Both lat and lng parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate coordinates
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError('Invalid coordinate range')
        except ValueError as e:
            return Response(
                {'error': f'Invalid coordinates: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"🔍 Reverse geocoding: {lat}, {lng}")
        
        # Try Nominatim first (free, no API key needed)
        result = _nominatim_reverse_geocode(lat, lng)
        
        if result:
            logger.info(f"✅ Nominatim success: {result.get('city', 'N/A')}")
            return Response(result, status=status.HTTP_200_OK)
        
        # Fallback to Google Maps API (if you have it configured)
        # Uncomment if you want to use Google as backup
        # result = _google_reverse_geocode(lat, lng)
        # if result:
        #     logger.info(f"✅ Google Maps success: {result.get('city', 'N/A')}")
        #     return Response(result, status=status.HTTP_200_OK)
        
        # All methods failed
        logger.error("❌ All geocoding methods failed")
        return Response(
            {
                'error': 'Could not determine location',
                'city': 'Makurdi',  # Fallback
                'country': 'Nigeria'
            },
            status=status.HTTP_200_OK  # Still return 200 with fallback
        )
        
    except Exception as e:
        logger.error(f"❌ Reverse geocoding error: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _nominatim_reverse_geocode(lat, lng):
    """
    Use OpenStreetMap Nominatim for reverse geocoding
    FREE - No API key required
    """
    try:
        # Nominatim API endpoint
        url = "https://nominatim.openstreetmap.org/reverse"
        
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 10,  # City level
        }
        
        headers = {
            'User-Agent': 'SwiftRide-App/1.0'  # Required by Nominatim
        }
        
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Extract location data
            result = {
                'city': (
                    address.get('city') or 
                    address.get('town') or 
                    address.get('village') or 
                    address.get('state')
                ),
                'town': address.get('town'),
                'village': address.get('village'),
                'state': address.get('state'),
                'country': address.get('country'),
                'display_name': data.get('display_name'),
                'formatted': _format_address(address),
            }
            
            return result
            
    except requests.exceptions.Timeout:
        logger.warning("⚠️ Nominatim timeout")
    except Exception as e:
        logger.error(f"❌ Nominatim error: {str(e)}")
    
    return None


def _google_reverse_geocode(lat, lng):
    """
    Use Google Maps Geocoding API (requires API key)
    More accurate but costs money
    """
    try:
        from django.conf import settings
        
        # Get API key from settings
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not api_key:
            logger.warning("⚠️ Google Maps API key not configured")
            return None
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        params = {
            'latlng': f"{lat},{lng}",
            'key': api_key,
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                result = data['results'][0]
                address_components = result.get('address_components', [])
                
                # Extract city
                city = None
                state = None
                country = None
                
                for component in address_components:
                    types = component.get('types', [])
                    
                    if 'locality' in types:
                        city = component.get('long_name')
                    elif 'administrative_area_level_2' in types and not city:
                        city = component.get('long_name')
                    elif 'administrative_area_level_1' in types:
                        state = component.get('long_name')
                    elif 'country' in types:
                        country = component.get('long_name')
                
                return {
                    'city': city,
                    'state': state,
                    'country': country,
                    'display_name': result.get('formatted_address'),
                    'formatted': result.get('formatted_address'),
                }
                
    except Exception as e:
        logger.error(f"❌ Google Maps error: {str(e)}")
    
    return None


def _format_address(address):
    """Format address nicely"""
    parts = []
    
    if address.get('road'):
        parts.append(address['road'])
    if address.get('suburb'):
        parts.append(address['suburb'])
    if address.get('city') or address.get('town'):
        parts.append(address.get('city') or address.get('town'))
    if address.get('state'):
        parts.append(address['state'])
    
    return ', '.join(parts) if parts else None



# ========================================
# City Detection
# ========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def detect_city_from_coordinates(request):
    """Detect city using Google Maps Geocoding API"""
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'latitude and longitude are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get Google Maps API key
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    
    if not api_key:
        return Response(
            {'error': 'Google Maps API key not configured'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            # Extract city from address components
            for component in data['results'][0]['address_components']:
                if 'locality' in component['types']:
                    city = component['long_name']
                    return Response({
                        'city': city,
                        'formatted_address': data['results'][0]['formatted_address']
                    })
        
        return Response(
            {'error': 'Could not detect city'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ========================================
# Driver Location Tracking
# ========================================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def update_driver_location_api(request):
#     """Update driver's current location"""
#     try:
#         driver = request.user.driver
#     except:
#         return Response(
#             {'error': 'Only drivers can update location'},
#             status=status.HTTP_403_FORBIDDEN
#         )
    
#     latitude = request.data.get('latitude')
#     longitude = request.data.get('longitude')
    
#     if not latitude or not longitude:
#         return Response(
#             {'error': 'latitude and longitude required'},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     # Use service
#     location = update_driver_location(
#         driver=driver,
#         latitude=latitude,
#         longitude=longitude,
#         bearing=request.data.get('bearing'),
#         speed_kmh=request.data.get('speed_kmh'),
#         accuracy_meters=request.data.get('accuracy_meters')
#     )
    
#     if location:
#         return Response({
#             'success': True,
#             'message': 'Location updated',
#             'data': {
#                 'latitude': float(location.latitude),
#                 'longitude': float(location.longitude),
#                 'last_updated': location.last_updated.isoformat()
#             }
#         })
    
#     return Response(
#         {'error': 'Failed to update location'},
#         status=status.HTTP_400_BAD_REQUEST
#     )


# ========================================
# Driver Location QUERIES (not updates)
# ========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearby_drivers_api(request):
    """
    Get nearby online drivers (called by RIDERS looking for drivers)
    """
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    radius_km = float(request.query_params.get('radius', 10))
    vehicle_type = request.query_params.get('vehicle_type')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'latitude and longitude required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Validate coordinates
        lat = float(latitude)
        lng = float(longitude)
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError('Invalid coordinate range')
    except ValueError as e:
        return Response(
            {'error': f'Invalid coordinates: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use service to find nearby drivers
    from .services import get_nearby_drivers
    nearby_drivers = get_nearby_drivers(
        latitude=lat,
        longitude=lng,
        radius_km=radius_km,
        vehicle_type=vehicle_type
    )
    
    # Format results
    results = []
    for item in nearby_drivers:
        driver = item['driver']
        results.append({
            'driver_id': driver.id,
            'driver_name': driver.user.get_full_name() or driver.user.phone_number,
            'latitude': item['latitude'],
            'longitude': item['longitude'],
            'distance_km': item['distance_km'],
            'rating': float(driver.rating) if driver.rating else 0,
            'vehicle_type': driver.vehicle_type,
            'vehicle_make': driver.vehicle_make,
            'vehicle_model': driver.vehicle_model,
            'license_plate': driver.license_plate_number
        })
    
    return Response({
        'success': True,
        'count': len(results),
        'drivers': results
    })


# ========================================
# Ride Tracking (during active ride)
# ========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_ride_location_api(request):
    """
    Track ride location during active ride (called by driver)
    This is DIFFERENT from regular location updates
    """
    try:
        driver = request.user.driver_profile
    except:
        return Response(
            {'error': 'Only drivers can track rides'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    ride_id = request.data.get('ride_id')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not all([ride_id, latitude, longitude]):
        return Response(
            {'error': 'ride_id, latitude, and longitude required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify ride belongs to driver
    try:
        from rides.models import Ride
        ride = Ride.objects.get(id=ride_id, driver=driver, status__in=['accepted', 'picked_up'])
    except Ride.DoesNotExist:
        return Response(
            {'error': 'Active ride not found or not assigned to you'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Track location for this ride
    tracking_point = track_ride_location(
        ride=ride,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=request.data.get('speed_kmh'),
        bearing=request.data.get('bearing'),
        accuracy_meters=request.data.get('accuracy_meters')
    )
    
    if tracking_point:
        return Response({
            'success': True,
            'message': 'Ride location tracked'
        })
    
    return Response(
        {'error': 'Failed to track location'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ride_route_api(request, ride_id):
    """Get full tracking route for a completed/active ride"""
    try:
        from rides.models import Ride
        ride = Ride.objects.get(id=ride_id)
        
        # Check authorization
        if ride.user != request.user and (
            not hasattr(request.user, 'driver_profile') or 
            ride.driver != request.user.driver_profile
        ):
            return Response(
                {'error': 'Not authorized to view this ride'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get tracking points
        tracking_points = RideTracking.objects.filter(ride=ride).order_by('timestamp')
        
        route = [{
            'latitude': float(point.latitude),
            'longitude': float(point.longitude),
            'speed_kmh': float(point.speed_kmh) if point.speed_kmh else 0,
            'bearing': float(point.bearing) if point.bearing else 0,
            'timestamp': point.timestamp.isoformat()
        } for point in tracking_points]
        
        return Response({
            'success': True,
            'ride_id': ride_id,
            'route': route,
            'total_points': len(route)
        })
        
    except Ride.DoesNotExist:
        return Response(
            {'error': 'Ride not found'},
            status=status.HTTP_404_NOT_FOUND
        )