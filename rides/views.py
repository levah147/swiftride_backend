#   views.py for rides app
from django.db import models
from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils import timezone
from django.db.models import Q, Avg
from django.db import transaction
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

# ✅ WebSocket imports for real-time updates
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# ADD at top:
from pricing.models import VehicleType, City
from django.core.cache import cache


# ==================== Rider Endpoints ====================

class RideListCreateView(generics.ListCreateAPIView):
    """List and create rides (Riders)"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Ride.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RideCreateSerializer
        return RideSerializer
    
    def create(self, request, *args, **kwargs):
        """Create ride with strict fare verification - OVERRIDE to return proper response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Fare hash is required and validated in serializer
        fare_hash = serializer.validated_data.get('fare_hash')
        
        if not fare_hash:
            raise DRFValidationError({
                'fare_hash': 'Fare hash is required. Please calculate fare first.'
            })
        
        # Get fare data from cache (already validated in serializer)
        fare_data = cache.get(f'fare_{fare_hash}')
        if not fare_data:
            raise DRFValidationError({
                'fare_hash': 'Invalid or expired fare hash. Please recalculate fare.'
            })
        
        # Extract vehicle_type and city from fare_data
        vehicle_type_id = fare_data.get('vehicle_type_id')
        city_id = fare_data.get('city_id')
        
        # Get VehicleType and City objects
        vehicle_type = None
        city = None
        
        if vehicle_type_id:
            try:
                vehicle_type = VehicleType.objects.get(id=vehicle_type_id, is_active=True)
            except VehicleType.DoesNotExist:
                raise DRFValidationError({
                    'fare_hash': f'Vehicle type "{vehicle_type_id}" from fare calculation is no longer available.'
                })
        
        if city_id:
            try:
                city = City.objects.get(id=city_id, is_active=True)
            except City.DoesNotExist:
                raise DRFValidationError({
                    'fare_hash': f'City "{city_id}" from fare calculation is no longer available.'
                })
        
        # Create ride with verified fare data
        ride = serializer.save(
            user=self.request.user,
            status='pending',
            vehicle_type=vehicle_type,
            city=city,
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
        
        # Create ride request for drivers
        from django.conf import settings
        expiry_minutes = settings.RIDE_SETTINGS.get('RIDE_REQUEST_EXPIRY_MINUTES', 5)
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        RideRequest.objects.create(
            ride=ride,
            status='available',
            expires_at=expires_at
        )
        
        # ✅ Return the created ride with proper serializer
        output_serializer = RideSerializer(ride, context={'request': request})
        headers = self.get_success_headers(output_serializer.data)
        
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
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
    
    # ✅ ADD: Broadcast cancellation to driver (if assigned)
    if ride.driver:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'ride_{ride.id}',
            {
                'type': 'ride_status_update',
                'status': 'cancelled',
                'message': 'Ride has been cancelled by rider',
                'reason': ride.cancellation_reason
            }
        )
    
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ride_rating(request, ride_id):
    """Get rating for a completed ride"""
    try:
        ride = Ride.objects.get(id=ride_id)
        
        # Check if user is rider or driver
        if ride.user != request.user and (not hasattr(request.user, 'driver_profile') or ride.driver != request.user.driver_profile):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get mutual rating if exists
    try:
        mutual_rating = MutualRating.objects.get(ride=ride)
        serializer = MutualRatingSerializer(mutual_rating)
        return Response(serializer.data)
    except MutualRating.DoesNotExist:
        return Response({
            'ride_id': ride_id,
            'rider_rating': None,
            'driver_rating': None,
            'is_complete': False,
            'message': 'No rating submitted yet'
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_location(request, ride_id):
    """Get driver's current location for an active ride"""
    try:
        ride = Ride.objects.get(id=ride_id)
        
        # Check if user is rider or driver
        if ride.user != request.user and (not hasattr(request.user, 'driver_profile') or ride.driver != request.user.driver_profile):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if not ride.driver:
        return Response({
            'error': 'No driver assigned to this ride',
            'driver_location': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get driver's current location from locations app
    try:
        from locations.models import DriverLocation
        driver_location = getattr(ride.driver, 'current_location', None)
        
        if driver_location:
            return Response({
                'driver_id': str(ride.driver.id),
                'latitude': float(driver_location.latitude),
                'longitude': float(driver_location.longitude),
                'bearing': float(driver_location.bearing) if driver_location.bearing else None,
                'speed_kmh': float(driver_location.speed_kmh) if driver_location.speed_kmh else None,
                'accuracy_meters': float(driver_location.accuracy_meters) if driver_location.accuracy_meters else None,
                'last_updated': driver_location.last_updated.isoformat(),
            })
        else:
            return Response({
                'driver_id': str(ride.driver.id),
                'latitude': None,
                'longitude': None,
                'message': 'Driver location not available',
                'last_updated': None,
            })
    except Exception as e:
        return Response({
            'error': f'Could not retrieve driver location: {str(e)}',
            'driver_location': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ride_receipt(request, ride_id):
    """Get ride receipt/summary"""
    try:
        ride = Ride.objects.get(id=ride_id, user=request.user)
    except Ride.DoesNotExist:
        return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if ride.status != 'completed':
        return Response(
            {'error': 'Receipt only available for completed rides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate duration if available
    duration_minutes = ride.duration_minutes
    if not duration_minutes and ride.started_at and ride.completed_at:
        duration_minutes = int((ride.completed_at - ride.started_at).total_seconds() / 60)
    
    receipt_data = {
        'ride_id': ride.id,
        'rider_name': ride.user.get_full_name() or ride.user.phone_number,
        'rider_phone': ride.user.phone_number,
        'driver_name': ride.driver_full_name if ride.driver else 'N/A',
        'driver_phone': ride.driver_phone_number if ride.driver else 'N/A',
        'vehicle_info': ride.vehicle_details if ride.driver else 'N/A',
        'pickup_location': ride.pickup_location,
        'destination_location': ride.destination_location,
        'distance_km': float(ride.distance_km) if ride.distance_km else None,
        'duration_minutes': duration_minutes,
        'fare_breakdown': {
            'base_fare': float(ride.base_fare),
            'distance_fare': float(ride.distance_fare),
            'time_fare': float(ride.time_fare),
            'surge_multiplier': float(ride.surge_multiplier),
            'fuel_adjustment': float(ride.fuel_adjustment),
            'cancellation_fee': float(ride.cancellation_fee_charged),
        },
        'total_fare': float(ride.fare_amount),
        'payment_method': 'cash',  # TODO: Get from payment model when implemented
        'created_at': ride.created_at.isoformat(),
        'accepted_at': ride.accepted_at.isoformat() if ride.accepted_at else None,
        'started_at': ride.started_at.isoformat() if ride.started_at else None,
        'completed_at': ride.completed_at.isoformat() if ride.completed_at else None,
    }
    
    return Response(receipt_data)


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
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    # Check driver can accept rides (includes vehicle check)
    if not driver.can_accept_rides:
        return Response(
            {'error': 'Driver account is not eligible to accept rides. Please check your account status.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get driver's current vehicle
    vehicle = driver.current_vehicle
    if not vehicle:
        return Response(
            {'error': 'No vehicle assigned. Please add a vehicle to your profile.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not vehicle.is_roadworthy:
        return Response(
            {'error': 'Your vehicle is not roadworthy. Please update vehicle documents.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use transaction.atomic for atomicity
    ride = ride_request.ride
    
    try:
        with transaction.atomic():
            # Lock the ride row to prevent race conditions
            ride = Ride.objects.select_for_update().get(id=ride.id)
            
            logger.info(f"Accepting ride {ride.id}. Current status: {ride.status}")
            
            # Assign ride to driver
            ride.driver = driver
            ride.vehicle = vehicle
            ride.status = 'accepted'
            ride.accepted_at = timezone.now()
            ride.save(update_fields=['driver', 'vehicle', 'status', 'accepted_at'])
            
            logger.info(f"Ride {ride.id} status updated to: {ride.status}")
            
            # Update ride request status
            ride_request.status = 'accepted'
            ride_request.save()
            
            # Record driver response
            DriverRideResponse.objects.create(
                ride_request=ride_request,
                driver=driver,
                response='accepted'
            )
            
            # Update driver stats (increment total rides)
            driver.total_rides += 1
            driver.is_available = False  # Mark driver as unavailable
            driver.save(update_fields=['total_rides', 'is_available'])
            
    except Exception as e:
        logger.error(f"Transaction error accepting ride {ride.id}: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to accept ride: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Calculate ETA using locations app
    from django.conf import settings
    default_eta = settings.RIDE_SETTINGS.get('DEFAULT_ETA_MINUTES', 5)
    eta_minutes = default_eta
    
    try:
        from locations.services import calculate_eta
        
        # Get driver's current location
        driver_location = getattr(driver, 'current_location', None)
        if driver_location:
            eta_data = calculate_eta(
                driver_location=driver_location,
                destination_lat=float(ride.pickup_latitude),
                destination_lng=float(ride.pickup_longitude),
                average_speed_kmh=30
            )
            if eta_data:
                eta_minutes = eta_data.get('eta_minutes', default_eta)
    except Exception as e:
        logger.warning(f"Could not calculate ETA for ride {ride.id}: {str(e)}")
    
    # Broadcast to rider via WebSocket
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'ride_{ride.id}',
            {
                'type': 'driver_matched_update',
                'driver_id': str(driver.id),
                'driver_name': driver.user.get_full_name() or driver.user.phone_number,
                'driver_phone': driver.user.phone_number,
                'driver_rating': float(driver.rating) if driver.rating else 0.0,
                'vehicle_type': vehicle.vehicle_type.name if vehicle and vehicle.vehicle_type else 'Unknown',
                'vehicle_model': f"{vehicle.make} {vehicle.model}" if vehicle else 'Unknown',
                'vehicle_color': vehicle.color if vehicle else 'Unknown',
                'license_plate': vehicle.license_plate if vehicle else 'Unknown',
                'eta': eta_minutes,
                'eta_minutes': eta_minutes,
            }
        )
    except Exception as e:
        logger.warning(f"WebSocket broadcast error: {str(e)}")
    
    # REFRESH the ride from database before serializing
    ride.refresh_from_db()
    
    logger.info(f"After refresh, ride {ride.id} status: {ride.status}")
    
    # Use select_related to load all related objects
    ride = Ride.objects.select_related(
        'driver',
        'driver__user', 
        'driver__current_vehicle',
        'driver__current_vehicle__vehicle_type',
        'vehicle',
        'vehicle__vehicle_type',
        'user'
    ).get(id=ride.id)
    
    try:
        serialized_ride = RideSerializer(ride, context={'request': request}).data
    except Exception as e:
        logger.error(f"Serialization error: {str(e)}", exc_info=True)
        return Response({
            'success': True,
            'message': 'Ride accepted successfully',
            'ride_id': ride.id,
            'status': ride.status
        })
    
    return Response({
        'success': True,
        'message': 'Ride accepted successfully',
        'ride': serialized_ride
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Only drivers can start rides'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Use select_related and get fresh data from database
    try:
        ride = Ride.objects.select_related('driver', 'user').get(
            id=ride_id, 
            driver=driver
        )
    except Ride.DoesNotExist:
        return Response(
            {'error': 'Ride not found or you are not assigned to this ride'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Refresh from database to ensure we have latest status
    ride.refresh_from_db()
    
    # Log current status for debugging
    logger.info(f"Attempting to start ride {ride_id}. Current status: {ride.status}")
    
    # Check if ride can be started - accept BOTH 'accepted' and 'arriving' statuses
    valid_statuses = ['accepted', 'arriving']
    if ride.status not in valid_statuses:
        return Response(
            {
                'error': f'Cannot start ride with status: {ride.status}',
                'detail': f'Current status is "{ride.status}". Ride must be in {valid_statuses} to start.',
                'current_status': ride.status,
                'allowed_statuses': valid_statuses
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Start the ride using transaction to prevent race conditions
    try:
        with transaction.atomic():
            # Lock the row to prevent concurrent updates
            ride = Ride.objects.select_for_update().get(id=ride_id)
            
            # Double-check status after locking
            if ride.status not in valid_statuses:
                return Response(
                    {
                        'error': f'Cannot start ride with status: {ride.status}',
                        'detail': 'Ride status changed during processing',
                        'current_status': ride.status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ride.status = 'in_progress'
            ride.started_at = timezone.now()
            ride.save(update_fields=['status', 'started_at'])
        
        logger.info(f"Ride {ride_id} started successfully")
        
        # ✅ FIX: Refresh the ride object AFTER the transaction
        ride.refresh_from_db()
        
    except Exception as e:
        logger.error(f"Error starting ride {ride_id}: {str(e)}")
        return Response(
            {'error': f'Failed to start ride: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Broadcast to rider via WebSocket
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'ride_{ride.id}',
            {
                'type': 'ride_status_update',
                'status': 'in_progress',
                'message': 'Your ride has started. Enjoy your trip!',
                'started_at': ride.started_at.isoformat()
            }
        )
    except Exception as e:
        logger.warning(f"WebSocket broadcast error: {str(e)}")
    
    return Response({
        'success': True,
        'message': 'Ride started successfully',
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
    
    # Get final location from request (optional)
    end_latitude = request.data.get('end_latitude')
    end_longitude = request.data.get('end_longitude')
    
    if end_latitude and end_longitude:
        ride.destination_latitude = end_latitude
        ride.destination_longitude = end_longitude
    
    ride.status = 'completed'
    ride.completed_at = timezone.now()
    ride.save()
    
    # Calculate duration
    if ride.started_at:
        duration = (ride.completed_at - ride.started_at).total_seconds() / 60
        ride.duration_minutes = int(duration)
        ride.save()
    
    # ✅ ADD: Broadcast to rider via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ride_{ride.id}',
        {
            'type': 'ride_status_update',
            'status': 'completed',
            'message': 'Ride completed. Thank you for riding with us!',
            'completed_at': ride.completed_at.isoformat(),
            'total_fare': float(ride.fare_amount) if ride.fare_amount else 0.0,
        }
    )
    
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
    
    # ✅ ADD: Broadcast cancellation to rider via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ride_{ride.id}',
        {
            'type': 'ride_status_update',
            'status': 'cancelled',
            'message': 'Ride has been cancelled by driver',
            'reason': ride.cancellation_reason
        }
    )
    
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