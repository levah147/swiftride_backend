#   views.py for rides app
from django.db import models
from django.forms import ValidationError
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Avg
from datetime import timedelta
from decimal import Decimal
import math
from locations.models import RideTracking
from .models import (
    Ride, Promotion, RideRequest, DriverRideResponse, MutualRating
)
from drivers.models import Driver
from .serializers import (
    RideSerializer, RideCreateSerializer, PromotionSerializer,
    RideRequestSerializer, AvailableRideSerializer, ActiveRideSerializer,
    MutualRatingSerializer, RateRideSerializer, RideTrackingSerializer
)


# ==================== Rider Endpoints ====================



# ADD at top:
from pricing.models import VehicleType, City
from django.core.cache import cache


class RideListCreateView(generics.ListCreateAPIView):
    """List and create rides (Riders)"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Ride.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RideCreateSerializer
        return RideSerializer
    
    def perform_create(self, serializer):
        """Create ride with optional fare verification"""
        # Get fare hash from request if provided (for fare verification)
        fare_hash = self.request.data.get('fare_hash')
        
        if fare_hash:
            # Verify fare from cache
            fare_data = cache.get(f'fare_{fare_hash}')
            
            if fare_data:
                # Create ride with fare breakdown from cache
                ride = serializer.save(
                    user=self.request.user,
                    status='pending',
                    # vehicle_type_id=fare_data.get('vehicle_type_id'),
                    vehicle_type = models.ForeignKey('pricing.VehicleType', ...),
                    city_id=fare_data.get('city_id'),
                    fare_hash=fare_hash,
                    base_fare=fare_data.get('base_fare', 0),
                    distance_fare=fare_data.get('distance_fare', 0),
                    time_fare=fare_data.get('time_fare', 0),
                    surge_multiplier=fare_data.get('surge_multiplier', 1.0),
                    fuel_adjustment=fare_data.get('fuel_adjustment_total', 0),
                    fare_amount=fare_data.get('total_fare', 0),
                    distance_km=fare_data.get('distance_km'),
                    duration_minutes=fare_data.get('estimated_duration_minutes')
                )
            else:
                # Fare hash provided but not found in cache - create ride without fare verification
                ride = serializer.save(user=self.request.user, status='pending')
        else:
            # No fare hash - create ride normally
            ride = serializer.save(user=self.request.user, status='pending')
        
        # Create ride request for drivers
        expires_at = timezone.now() + timedelta(minutes=5)  # 5 min to find driver
        RideRequest.objects.create(
            ride=ride,
            status='available',
            expires_at=expires_at
        )


class RideDetailView(generics.RetrieveUpdateAPIView):
    """Get and update ride details"""
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer
    
    def get_queryset(self):
        return Ride.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upcoming_rides(request):
    """Get upcoming scheduled rides"""
    rides = Ride.objects.filter(
        user=request.user,
        status__in=['pending', 'accepted', 'arriving'],
        ride_type='scheduled',
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')
    serializer = RideSerializer(rides, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def past_rides(request):
    """Get completed/cancelled rides"""
    rides = Ride.objects.filter(
        user=request.user,
        status__in=['completed', 'cancelled']
    ).order_by('-created_at')
    serializer = RideSerializer(rides, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_ride(request, ride_id):
    """Cancel a ride (Rider)"""
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'Cannot cancel {ride.status} ride'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ride.status = 'cancelled'
    ride.cancelled_by = 'rider'
    ride.cancellation_reason = request.data.get('reason', 'Cancelled by rider')
    ride.cancelled_at = timezone.now()
    ride.save()
    
    # Cancel ride request if exists
    RideRequest.objects.filter(ride=ride, status='available').update(status='cancelled')
    
    return Response({
        'success': True,
        'message': 'Ride cancelled successfully',
        'ride': RideSerializer(ride).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_ride(request, ride_id):
    """Rider rates driver after ride"""
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status != 'completed':
        return Response(
            {'error': 'Can only rate completed rides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = RateRideSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create or update mutual rating
    mutual_rating, created = MutualRating.objects.get_or_create(ride=ride)
    mutual_rating.rider_rating = serializer.validated_data['rating']
    mutual_rating.rider_comment = serializer.validated_data.get('comment', '')
    mutual_rating.rider_rated_at = timezone.now()
    mutual_rating.save()
    
    # Update driver's average rating
    if ride.driver:
        avg_rating = MutualRating.objects.filter(
            ride__driver=ride.driver,
            rider_rating__isnull=False
        ).aggregate(Avg('rider_rating'))['rider_rating__avg']
        
        if avg_rating:
            ride.driver.rating = round(avg_rating, 2)
            ride.driver.save()
    
    return Response({
        'success': True,
        'message': 'Rating submitted successfully',
        'rating': MutualRatingSerializer(mutual_rating).data
    })


# ==================== Driver Endpoints ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_rides(request):
    """Get available ride requests for drivers"""
    # Check if user is a driver
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Only drivers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if driver is approved
    if driver.status != 'approved':
        return Response(
            {'error': 'Driver account not approved'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get driver location from request
    driver_lat = request.query_params.get('latitude')
    driver_lon = request.query_params.get('longitude')
    max_distance = float(request.query_params.get('max_distance', 10))  # km
    
    # Get available ride requests
    ride_requests = RideRequest.objects.filter(
        status='available',
        expires_at__gt=timezone.now()
    ).select_related('ride', 'ride__user')
    
    # Filter by distance if driver location provided
    if driver_lat and driver_lon:
        driver_lat = float(driver_lat)
        driver_lon = float(driver_lon)
        
        filtered_requests = []
        for req in ride_requests:
            distance = calculate_distance(
                driver_lat, driver_lon,
                float(req.ride.pickup_latitude), float(req.ride.pickup_longitude)
            )
            if distance <= max_distance:
                filtered_requests.append(req)
        
        ride_requests = filtered_requests
    
    serializer = AvailableRideSerializer(ride_requests, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_ride(request, request_id):
    """Driver accepts a ride request"""
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Only drivers can accept rides'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        ride_request = RideRequest.objects.get(id=request_id)
    except RideRequest.DoesNotExist:
        return Response({'error': 'Ride request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if request is still available
    if ride_request.status != 'available':
        return Response(
            {'error': 'Ride request is no longer available'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if ride_request.expires_at <= timezone.now():
        ride_request.status = 'expired'
        ride_request.save()
        return Response(
            {'error': 'Ride request has expired'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if driver has another active ride
    active_rides = Ride.objects.filter(
        driver=driver,
        status__in=['accepted', 'arriving', 'in_progress']
    )
    if active_rides.exists():
        return Response(
            {'error': 'You already have an active ride'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Assign ride to driver
    ride = ride_request.ride
    ride.driver = driver
    # Assign driver's primary vehicle to ride
    vehicle = driver.primary_vehicle
    if vehicle and vehicle.is_roadworthy:
        ride.vehicle = vehicle
    ride.save()
    
    ride.status = 'accepted'
    ride.accepted_at = timezone.now()
    ride.save()
    
    # Update ride request
    ride_request.status = 'accepted'
    ride_request.save()
    
    # Record driver response
    DriverRideResponse.objects.create(
        ride_request=ride_request,
        driver=driver,
        response='accepted'
    )
    
    # Update driver stats
    driver.total_rides += 1
    driver.save()
    
    return Response({
        'success': True,
        'message': 'Ride accepted successfully',
        'ride': RideSerializer(ride).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_ride(request, request_id):
    """Driver declines a ride request"""
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Only drivers can decline rides'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        ride_request = RideRequest.objects.get(id=request_id)
    except RideRequest.DoesNotExist:
        return Response({'error': 'Ride request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Record decline
    DriverRideResponse.objects.create(
        ride_request=ride_request,
        driver=driver,
        response='declined',
        decline_reason=request.data.get('reason', 'No reason provided')
    )
    
    return Response({
        'success': True,
        'message': 'Ride declined'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def driver_active_rides(request):
    """Get driver's active rides"""
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Only drivers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    rides = Ride.objects.filter(
        driver=driver,
        status__in=['accepted', 'arriving', 'in_progress']
    ).order_by('-accepted_at')
    
    serializer = ActiveRideSerializer(rides, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_ride(request, ride_id):
    """Driver starts the ride (picked up rider)"""
    try:
        driver = request.user.driver_profile
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except (Driver.DoesNotExist, Ride.DoesNotExist):
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status not in ['accepted', 'arriving']:
        return Response(
            {'error': f'Cannot start ride with status: {ride.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ride.status = 'in_progress'
    ride.started_at = timezone.now()
    ride.save()
    
    return Response({
        'success': True,
        'message': 'Ride started',
        'ride': RideSerializer(ride).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_ride(request, ride_id):
    """Driver completes the ride (arrived at destination)"""
    try:
        driver = request.user.driver_profile
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except (Driver.DoesNotExist, Ride.DoesNotExist):
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status != 'in_progress':
        return Response(
            {'error': 'Can only complete rides that are in progress'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ride.status = 'completed'
    ride.completed_at = timezone.now()
    ride.save()
    
    # Calculate duration
    if ride.started_at:
        duration = (ride.completed_at - ride.started_at).total_seconds() / 60
        ride.duration_minutes = int(duration)
        ride.save()
    
    return Response({
        'success': True,
        'message': 'Ride completed',
        'ride': RideSerializer(ride).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def driver_cancel_ride(request, ride_id):
    """Driver cancels an accepted ride"""
    try:
        driver = request.user.driver_profile
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except (Driver.DoesNotExist, Ride.DoesNotExist):
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'Cannot cancel {ride.status} ride'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ride.status = 'cancelled'
    ride.cancelled_by = 'driver'
    ride.cancellation_reason = request.data.get('reason', 'Cancelled by driver')
    ride.cancelled_at = timezone.now()
    ride.save()
    
    return Response({
        'success': True,
        'message': 'Ride cancelled',
        'ride': RideSerializer(ride).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def driver_rate_rider(request, ride_id):
    """Driver rates rider after ride"""
    try:
        driver = request.user.driver_profile
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except (Driver.DoesNotExist, Ride.DoesNotExist):
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status != 'completed':
        return Response(
            {'error': 'Can only rate completed rides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = RateRideSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create or update mutual rating
    mutual_rating, created = MutualRating.objects.get_or_create(ride=ride)
    mutual_rating.driver_rating = serializer.validated_data['rating']
    mutual_rating.driver_comment = serializer.validated_data.get('comment', '')
    mutual_rating.driver_rated_at = timezone.now()
    mutual_rating.save()
    
    return Response({
        'success': True,
        'message': 'Rating submitted successfully',
        'rating': MutualRatingSerializer(mutual_rating).data
    })


# ==================== Location Tracking ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_location(request, ride_id):
    """Update driver's current location during ride"""
    try:
        driver = request.user.driver_profile
        ride = Ride.objects.get(id=ride_id, driver=driver)
    except (Driver.DoesNotExist, Ride.DoesNotExist):
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status not in ['accepted', 'arriving', 'in_progress']:
        return Response(
            {'error': 'Can only update location for active rides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = RideTrackingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    tracking = RideTracking.objects.create(
        ride=ride,
        **serializer.validated_data
    )
    
    return Response({
        'success': True,
        'tracking': RideTrackingSerializer(tracking).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ride_tracking(request, ride_id):
    """Get live tracking for a ride"""
    try:
        ride = Ride.objects.get(id=ride_id)
        
        # Check if user is rider or driver
        if ride.user != request.user and (not hasattr(request.user, 'driver_profile') or ride.driver != request.user.driver_profile):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get latest tracking points (last 50)
    tracking = RideTracking.objects.filter(ride=ride).order_by('-timestamp')[:50]
    serializer = RideTrackingSerializer(tracking, many=True)
    
    return Response(serializer.data)


# ==================== Promotions ====================

class ActivePromotionsView(generics.ListAPIView):
    """List active promotions"""
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Promotion.objects.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        )


# ==================== Helper Functions ====================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance