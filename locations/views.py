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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_driver_location_api(request):
    """Update driver's current location"""
    try:
        driver = request.user.driver
    except:
        return Response(
            {'error': 'Only drivers can update location'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'latitude and longitude required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use service
    location = update_driver_location(
        driver=driver,
        latitude=latitude,
        longitude=longitude,
        bearing=request.data.get('bearing'),
        speed_kmh=request.data.get('speed_kmh'),
        accuracy_meters=request.data.get('accuracy_meters')
    )
    
    if location:
        return Response({
            'success': True,
            'message': 'Location updated',
            'data': {
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'last_updated': location.last_updated.isoformat()
            }
        })
    
    return Response(
        {'error': 'Failed to update location'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearby_drivers_api(request):
    """Get nearby online drivers"""
    latitude = request.query_params.get('latitude')
    longitude = request.query_params.get('longitude')
    radius_km = float(request.query_params.get('radius', 10))
    vehicle_type = request.query_params.get('vehicle_type')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'latitude and longitude required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use service
    nearby_drivers = get_nearby_drivers(
        latitude=float(latitude),
        longitude=float(longitude),
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
            'vehicle_type': driver.vehicles.first().vehicle_type.id if driver.vehicles.exists() else None
        })
    
    return Response({
        'success': True,
        'count': len(results),
        'drivers': results
    })


# ========================================
# Ride Tracking
# ========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_ride_location_api(request):
    """Track ride location (called by driver during ride)"""
    try:
        driver = request.user.driver
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
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except Ride.DoesNotExist:
        return Response(
            {'error': 'Ride not found or not assigned to you'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Track location
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
            'message': 'Location tracked'
        })
    
    return Response(
        {'error': 'Failed to track location'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ride_route_api(request, ride_id):
    """Get tracking route for a ride"""
    try:
        from rides.models import Ride
        ride = Ride.objects.get(id=ride_id)
        
        # Check if user is authorized
        if ride.user != request.user and (not hasattr(request.user, 'driver') or ride.driver != request.user.driver):
            return Response(
                {'error': 'Not authorized to view this ride'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get tracking points
        tracking_points = RideTracking.objects.filter(ride=ride).order_by('timestamp')
        
        route = []
        for point in tracking_points:
            route.append({
                'latitude': float(point.latitude),
                'longitude': float(point.longitude),
                'speed_kmh': float(point.speed_kmh) if point.speed_kmh else 0,
                'bearing': float(point.bearing) if point.bearing else 0,
                'timestamp': point.timestamp.isoformat()
            })
        
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