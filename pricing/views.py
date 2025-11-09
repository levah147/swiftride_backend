#   views.py for priceing app

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import Q
from django.conf import settings
import math
from decimal import Decimal
import hashlib

from .models import City, VehicleType, VehiclePricing, SurgePricing, FuelPriceAdjustment
from .serializers import (
    CitySerializer, VehicleTypeListSerializer,
    FareCalculationSerializer, FareCalculationResponseSerializer
)


class CityListView(generics.ListAPIView):
    """Get all active cities where service is available"""
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Cache cities for 1 hour
        cache_key = 'active_cities'
        cached_cities = cache.get(cache_key)
        
        if cached_cities is None:
            cities = City.objects.filter(is_active=True)
            cache.set(cache_key, list(cities), 3600)  # 1 hour
            return cities
        
        return City.objects.filter(id__in=[c.id for c in cached_cities])
    
    queryset = City.objects.filter(is_active=True)


@api_view(['POST'])
@permission_classes([AllowAny])
def detect_city(request):
    """Detect city from coordinates"""
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response(
            {'error': 'latitude and longitude are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid latitude or longitude format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate coordinate ranges
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return Response(
            {'error': 'Invalid coordinate values'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check cache first
    cache_key = f'city_detect_{lat}_{lon}'
    cached_city = cache.get(cache_key)
    
    if cached_city:
        return Response(cached_city)
    
    # Find nearest city
    cities = City.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    nearest_city = None
    min_distance = float('inf')
    
    for city in cities:
        distance = calculate_distance(
            lat, lon,
            float(city.latitude), 
            float(city.longitude)
        )
        
        if distance < min_distance:
            min_distance = distance
            nearest_city = city
    
    if nearest_city:
        # Check if within service radius
        if nearest_city.is_within_service_area(lat, lon):
            serializer = CitySerializer(nearest_city)
            result = {
                **serializer.data,
                'distance_from_center_km': round(min_distance, 2)
            }
            cache.set(cache_key, result, 1800)  # Cache for 30 minutes
            return Response(result)
        else:
            return Response(
                {
                    'error': 'Location is outside service area',
                    'nearest_city': nearest_city.name,
                    'distance_km': round(min_distance, 2),
                    'service_radius_km': float(nearest_city.radius_km)
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(
        {'error': 'No service available in your area'},
        status=status.HTTP_404_NOT_FOUND
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_vehicles(request):
    """Get available vehicle types for a city"""
    city_name = request.query_params.get('city')
    
    if not city_name:
        return Response(
            {'error': 'city parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check cache
    cache_key = f'vehicles_{city_name.lower()}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    try:
        city = City.objects.get(name__iexact=city_name, is_active=True)
    except City.DoesNotExist:
        return Response(
            {'error': f'City "{city_name}" not found or service not available'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Filter vehicles by city availability
    vehicle_ids = city.get_available_vehicles()
    
    if not vehicle_ids:
        return Response(
            {'error': f'No vehicles available in {city.name}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    vehicles = VehicleType.objects.filter(
        id__in=vehicle_ids,
        is_active=True
    ).prefetch_related('pricing')
    
    serializer = VehicleTypeListSerializer(
        vehicles,
        many=True,
        context={'city': city, 'request': request}
    )
    
    result = {
        'city': {
            'id': city.id,
            'name': city.name,
            'state': city.state,
            'currency': city.currency,
            'currency_symbol': city.currency_symbol,
        },
        'vehicles': serializer.data,
        'surge_multiplier': SurgePricing.get_current_multiplier(city)
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, result, 300)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Require authentication
def calculate_fare(request):
    """
    Calculate fare for a ride.
    Returns fare estimate with verification hash.
    """
    serializer = FareCalculationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    
    # Extract coordinates
    pickup_lat = float(data['pickup_latitude'])
    pickup_lon = float(data['pickup_longitude'])
    dest_lat = float(data['destination_latitude'])
    dest_lon = float(data['destination_longitude'])
    
    # Calculate distance using Haversine
    # TODO: Integrate with Google Maps Distance Matrix API for accurate road distance
    distance_km = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
    
    # Validate distance (must be at least 0.1 km)
    if distance_km < 0.1:
        return Response(
            {
                'error': 'Pickup and destination are too close',
                'minimum_distance_km': 0.1
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Estimate duration (average speed varies by vehicle type)
    vehicle_type_id = data['vehicle_type']
    avg_speeds = {
        'bike': 35,  # km/h
        'keke': 30,
        'car': 40,
        'suv': 40
    }
    avg_speed = avg_speeds.get(vehicle_type_id, 30)
    duration_minutes = max(int((distance_km / avg_speed) * 60), 1)
    
    # Get or detect city
    city = None
    if data.get('city_name'):
        try:
            city = City.objects.get(name__iexact=data['city_name'], is_active=True)
        except City.DoesNotExist:
            return Response(
                {'error': f'City "{data["city_name"]}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Detect city from coordinates - find the closest city
        cities = City.objects.filter(is_active=True)
        if not cities.exists():
            return Response(
                {'error': 'No active cities available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Find city with coordinates within service area
        city = None
        for c in cities:
            if c.is_within_service_area(pickup_lat, pickup_lon):
                city = c
                break
        
        if not city:
            return Response(
                {'error': 'Service not available in this area'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Get vehicle type and pricing
    try:
        vehicle_type = VehicleType.objects.get(id=vehicle_type_id, is_active=True)
    except VehicleType.DoesNotExist:
        return Response(
            {'error': f'Vehicle type "{vehicle_type_id}" not available'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    pricing = vehicle_type.get_base_pricing(city)
    
    if not pricing:
        return Response(
            {'error': 'Pricing not available for this vehicle in your city'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Calculate base fare components
    base_fare = pricing.base_fare
    distance_fare = pricing.price_per_km * Decimal(str(distance_km))
    time_fare = pricing.price_per_minute * Decimal(str(duration_minutes))
    
    # Get surge multiplier
    surge_multiplier = Decimal(str(SurgePricing.get_current_multiplier(city)))
    
    # Get fuel adjustment
    fuel_adjustment_per_km = Decimal('0.00')
    fuel_adjustment_total = Decimal('0.00')
    
    if city:
        fuel_adj = FuelPriceAdjustment.objects.filter(
            city=city,
            is_active=True
        ).order_by('-effective_date').first()
        
        if not fuel_adj:
            # Check for global adjustment
            fuel_adj = FuelPriceAdjustment.objects.filter(
                city__isnull=True,
                is_active=True
            ).order_by('-effective_date').first()
        
        if fuel_adj:
            fuel_adjustment_per_km = fuel_adj.calculate_adjustment()
            fuel_adjustment_total = fuel_adjustment_per_km * Decimal(str(distance_km))
    
    # Calculate subtotal
    subtotal = base_fare + distance_fare + time_fare + fuel_adjustment_total
    
    # Apply surge
    total_fare = subtotal * surge_multiplier
    
    # Apply minimum fare
    total_fare = max(total_fare, pricing.minimum_fare)
    
    # Apply maximum fare if set
    if pricing.maximum_fare:
        total_fare = min(total_fare, pricing.maximum_fare)
    
    # Round to 2 decimal places
    total_fare = round(total_fare, 2)
    
    # Calculate driver earnings
    earnings = pricing.calculate_driver_earnings(total_fare)
    
    # Generate verification hash (to prevent tampering)
    fare_hash = generate_fare_hash(
        vehicle_type_id,
        distance_km,
        duration_minutes,
        float(total_fare),
        request.user.id
    )
    
    # Prepare response
    response_data = {
        'vehicle_type': vehicle_type.name,
        'vehicle_type_id': vehicle_type_id,
        'distance_km': round(distance_km, 2),
        'estimated_duration_minutes': duration_minutes,
        'base_fare': float(base_fare),
        'distance_fare': float(distance_fare),
        'time_fare': float(time_fare),
        'surge_multiplier': float(surge_multiplier),
        'fuel_adjustment_per_km': float(fuel_adjustment_per_km),
        'fuel_adjustment_total': float(fuel_adjustment_total),
        'subtotal': float(subtotal),
        'total_fare': float(total_fare),
        'minimum_fare': float(pricing.minimum_fare),
        'currency': city.currency if city else 'NGN',
        'currency_symbol': city.currency_symbol if city else '₦',
        'fare_hash': fare_hash,  # For verification when creating ride
        'breakdown': {
            'base': f'₦{base_fare}',
            'distance': f'₦{distance_fare:.2f} ({distance_km:.1f} km × ₦{pricing.price_per_km}/km)',
            'time': f'₦{time_fare:.2f} ({duration_minutes} min × ₦{pricing.price_per_minute}/min)',
            'surge': f'{surge_multiplier}x' if surge_multiplier > 1 else 'No surge',
            'fuel_adjustment': f'₦{fuel_adjustment_total:.2f}' if fuel_adjustment_total > 0 else 'None',
            'total': f'₦{total_fare:.2f}'
        },
        'driver_earnings': earnings,
        'cancellation_fee': float(pricing.cancellation_fee)
    }
    
    # Cache fare calculation for 5 minutes (for ride creation verification)
    cache_key = f'fare_{fare_hash}'
    cache.set(cache_key, response_data, 300)
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_fare(request):
    """
    Verify a fare calculation hash.
    Used when creating a ride to ensure fare hasn't been tampered with.
    """
    fare_hash = request.data.get('fare_hash')
    
    if not fare_hash:
        return Response(
            {'error': 'fare_hash is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check cache
    cache_key = f'fare_{fare_hash}'
    cached_fare = cache.get(cache_key)
    
    if cached_fare:
        return Response({
            'valid': True,
            'fare_data': cached_fare
        })
    
    return Response({
        'valid': False,
        'error': 'Fare calculation expired or invalid. Please recalculate fare.'
    }, status=status.HTTP_400_BAD_REQUEST)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.
    Returns distance in kilometers.
    
    Note: This is straight-line distance. In production, use Google Maps
    Distance Matrix API for actual road distance.
    """
    R = 6371  # Earth radius in km
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance


def generate_fare_hash(vehicle_type, distance, duration, fare, user_id):
    """
    Generate a hash for fare verification.
    Prevents clients from tampering with fare amounts.
    """
    # Get secret key from settings
    secret = getattr(settings, 'SECRET_KEY', 'default-secret')
    
    # Create hash string
    hash_string = f"{vehicle_type}:{distance:.2f}:{duration}:{fare:.2f}:{user_id}:{secret}"
    
    # Generate SHA256 hash
    return hashlib.sha256(hash_string.encode()).hexdigest()[:32]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_surge_info(request):
    """Get current surge pricing information for a city"""
    city_name = request.query_params.get('city')
    
    city = None
    if city_name:
        try:
            city = City.objects.get(name__iexact=city_name, is_active=True)
        except City.DoesNotExist:
            return Response(
                {'error': f'City "{city_name}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    multiplier = SurgePricing.get_current_multiplier(city)
    
    # Get active surge rules
    query = Q(is_active=True)
    if city:
        query &= (Q(city=city) | Q(city__isnull=True))
    
    active_rules = SurgePricing.objects.filter(query).order_by('-priority')
    
    active_rule = None
    for rule in active_rules:
        if rule.is_active_now():
            active_rule = rule
            break
    
    return Response({
        'city': city.name if city else 'All Cities',
        'current_multiplier': multiplier,
        'is_surge_active': multiplier > 1.0,
        'surge_level': active_rule.surge_level if active_rule else 'normal',
        'surge_message': f'{multiplier}x surge pricing in effect' if multiplier > 1.0 else 'Normal pricing',
        'active_rule': {
            'name': active_rule.name,
            'description': active_rule.description,
            'multiplier': float(active_rule.multiplier)
        } if active_rule else None
    })
    city = None
    if data.get('city_name'):
        try:
            city = City.objects.get(name__iexact=data['city_name'], is_active=True)
            
            # Validate pickup is within service area
            if not city.is_within_service_area(pickup_lat, pickup_lon):
                return Response(
                    {
                        'error': 'Pickup location is outside service area',
                        'city': city.name
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except City.DoesNotExist:
            return Response(
                {'error': f'City "{data["city_name"]}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Get