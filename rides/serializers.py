from rest_framework import serializers

from django.db import models  # ✅ CORRECT
from .models import (
    Ride, Promotion, RideRequest, DriverRideResponse, MutualRating
)
# from locations.models import RideTracking

from drivers.models import Driver


class RideSerializer(serializers.ModelSerializer):
    """Serializer for ride with structured driver information"""
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()  # ✅ Return structured driver object
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Ride
        fields = [
            'id', 'pickup_location', 'pickup_latitude', 'pickup_longitude',
            'destination_location', 'destination_latitude', 'destination_longitude',
            'ride_type', 'status', 'status_display', 'scheduled_time',
            'fare_amount', 'distance_km', 'duration_minutes',
            'driver', 'driver_name', 'driver_phone', 'vehicle_info',
            'cancelled_by', 'cancellation_reason',
            'rating', 'feedback',
            'accepted_at', 'started_at', 'completed_at', 'cancelled_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'driver', 'status', 'accepted_at', 'started_at',
            'completed_at', 'cancelled_at', 'created_at', 'updated_at'
        ]
    
    def get_driver(self, obj):
        """Return structured driver object for frontend"""
        if not obj.driver:
            return None
        
        driver = obj.driver
        vehicle = driver.current_vehicle
        
        return {
            'id': str(driver.id),
            'name': driver.user.get_full_name() or driver.user.phone_number,
            'phone_number': driver.user.phone_number,
            'rating': float(driver.rating) if driver.rating else 0.0,
            'vehicle_model': f"{vehicle.make} {vehicle.model}" if vehicle else 'Unknown',
            'vehicle_color': vehicle.color if vehicle else 'Unknown',
            'license_plate': vehicle.license_plate if vehicle else 'Unknown',
            'vehicle_type': vehicle.vehicle_type.name if vehicle and vehicle.vehicle_type else 'Unknown',
        }
    
    def get_driver_name(self, obj):
        """Legacy field for backward compatibility"""
        return obj.driver_full_name
    
    def get_driver_phone(self, obj):
        return obj.driver_phone_number
    
    def get_vehicle_info(self, obj):
        return obj.vehicle_details


class RideCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new ride with fare verification"""
    fare_hash = serializers.CharField(required=True, write_only=True)
    payment_method = serializers.ChoiceField(
        choices=['cash', 'wallet'],
        default='cash',
        required=False
    )  # ✅ ADD THIS
    
    class Meta:
        model = Ride
        fields = [
            'pickup_location', 'pickup_latitude', 'pickup_longitude',
            'destination_location', 'destination_latitude', 'destination_longitude',
            'ride_type', 'scheduled_time', 'fare_amount',
            'fare_hash', 'payment_method',  # ✅ ADD payment_method HERE
        ]
        read_only_fields = ['fare_amount']  # Set from fare_hash validation
    
    def validate(self, data):
        # If scheduled ride, must have scheduled_time
        if data.get('ride_type') == 'scheduled' and not data.get('scheduled_time'):
            raise serializers.ValidationError({
                'scheduled_time': 'Scheduled time is required for scheduled rides'
            })
        
        # Validate coordinates
        if not (-90 <= data['pickup_latitude'] <= 90):
            raise serializers.ValidationError({'pickup_latitude': 'Invalid latitude'})
        if not (-180 <= data['pickup_longitude'] <= 180):
            raise serializers.ValidationError({'pickup_longitude': 'Invalid longitude'})
        if not (-90 <= data['destination_latitude'] <= 90):
            raise serializers.ValidationError({'destination_latitude': 'Invalid latitude'})
        if not (-180 <= data['destination_longitude'] <= 180):
            raise serializers.ValidationError({'destination_longitude': 'Invalid longitude'})
        
        # Validate fare_hash exists in cache
        fare_hash = data.get('fare_hash')
        if fare_hash:
            from django.core.cache import cache
            fare_data = cache.get(f'fare_{fare_hash}')
            if not fare_data:
                raise serializers.ValidationError({
                    'fare_hash': 'Invalid or expired fare hash. Please recalculate fare.'
                })
        
        return data


class RideRequestSerializer(serializers.ModelSerializer):
    ride = RideSerializer(read_only=True)
    pickup_location = serializers.CharField(source='ride.pickup_location', read_only=True)
    destination_location = serializers.CharField(source='ride.destination_location', read_only=True)
    fare_amount = serializers.DecimalField(source='ride.fare_amount', max_digits=10, decimal_places=2, read_only=True)
    distance_km = serializers.DecimalField(source='ride.distance_km', max_digits=8, decimal_places=2, read_only=True)
    rider_name = serializers.CharField(source='ride.user.get_full_name', read_only=True)
    rider_phone = serializers.CharField(source='ride.user.phone_number', read_only=True)
    rider_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = RideRequest
        fields = [
            'id', 'ride', 'status', 'expires_at',
            'pickup_location', 'destination_location',
            'fare_amount', 'distance_km',
            'rider_name', 'rider_phone', 'rider_rating',
            'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def get_rider_rating(self, obj):
        # Calculate average rider rating from driver ratings
        from .models import MutualRating
        ratings = MutualRating.objects.filter(
            ride__user=obj.ride.user,
            driver_rating__isnull=False
        )
        if ratings.exists():
            avg = ratings.aggregate(models.Avg('driver_rating'))['driver_rating__avg']
            return round(avg, 1) if avg else 5.0
        return 5.0  # Default rating


class DriverRideResponseSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    
    class Meta:
        model = DriverRideResponse
        fields = [
            'id', 'ride_request', 'driver', 'driver_name',
            'response', 'decline_reason', 'response_time_seconds',
            'created_at'
        ]
        read_only_fields = ['id', 'driver', 'response_time_seconds', 'created_at']


class RideTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        # model = RideTracking
        model = 'locations.RideTracking'
        fields = [
            'id', 'ride', 'latitude', 'longitude',
            'speed_kmh', 'bearing', 'accuracy_meters',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class MutualRatingSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source='ride.user.get_full_name', read_only=True)
    driver_name = serializers.SerializerMethodField()
    is_complete = serializers.ReadOnlyField()
    
    class Meta:
        model = MutualRating
        fields = [
            'id', 'ride', 'rider_name', 'driver_name',
            'rider_rating', 'rider_comment', 'rider_rated_at',
            'driver_rating', 'driver_comment', 'driver_rated_at',
            'is_complete', 'created_at'
        ]
        read_only_fields = ['id', 'ride', 'created_at']
    
    def get_driver_name(self, obj):
        if obj.ride.driver:
            return obj.ride.driver.user.get_full_name()
        return "Unknown"


class RateRideSerializer(serializers.Serializer):
    """Serializer for rating a ride"""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'title', 'description', 'discount_percentage', 'max_rides', 'valid_until']


# ==================== Driver-Specific Serializers ====================

class AvailableRideSerializer(serializers.ModelSerializer):
    """Simplified serializer for drivers to see available rides"""
    pickup_location = serializers.CharField(source='ride.pickup_location', read_only=True)
    destination_location = serializers.CharField(source='ride.destination_location', read_only=True)
    pickup_latitude = serializers.DecimalField(source='ride.pickup_latitude', max_digits=10, decimal_places=8, read_only=True)
    pickup_longitude = serializers.DecimalField(source='ride.pickup_longitude', max_digits=11, decimal_places=8, read_only=True)
    destination_latitude = serializers.DecimalField(source='ride.destination_latitude', max_digits=10, decimal_places=8, read_only=True)
    destination_longitude = serializers.DecimalField(source='ride.destination_longitude', max_digits=11, decimal_places=8, read_only=True)
    fare_amount = serializers.DecimalField(source='ride.fare_amount', max_digits=10, decimal_places=2, read_only=True)
    distance_km = serializers.DecimalField(source='ride.distance_km', max_digits=8, decimal_places=2, read_only=True)
    rider_name = serializers.CharField(source='ride.user.get_full_name', read_only=True)
    rider_rating = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = RideRequest
        fields = [
            'id', 'pickup_location', 'destination_location',
            'pickup_latitude', 'pickup_longitude',
            'destination_latitude', 'destination_longitude',
            'fare_amount', 'distance_km', 'rider_name', 'rider_rating',
            'expires_at', 'time_remaining', 'created_at'
        ]
    
    def get_rider_rating(self, obj):
        from django.db.models import Avg
        ratings = MutualRating.objects.filter(
            ride__user=obj.ride.user,
            driver_rating__isnull=False
        )
        if ratings.exists():
            avg = ratings.aggregate(Avg('driver_rating'))['driver_rating__avg']
            return round(avg, 1) if avg else 5.0
        return 5.0
    
    def get_time_remaining(self, obj):
        """Seconds until request expires"""
        from django.utils import timezone
        if obj.expires_at > timezone.now():
            return int((obj.expires_at - timezone.now()).total_seconds())
        return 0


class ActiveRideSerializer(serializers.ModelSerializer):
    """Serializer for driver's active rides"""
    rider_name = serializers.CharField(source='user.get_full_name', read_only=True)
    rider_phone = serializers.CharField(source='user.phone_number', read_only=True)
    rider_rating = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Ride
        fields = [
            'id', 'rider_name', 'rider_phone', 'rider_rating',
            'pickup_location', 'pickup_latitude', 'pickup_longitude',
            'destination_location', 'destination_latitude', 'destination_longitude',
            'status', 'status_display', 'fare_amount', 'distance_km',
            'accepted_at', 'started_at', 'created_at'
        ]
    
    def get_rider_rating(self, obj):
        from django.db.models import Avg
        ratings = MutualRating.objects.filter(
            ride__user=obj.user,
            driver_rating__isnull=False
        )
        if ratings.exists():
            avg = ratings.aggregate(Avg('driver_rating'))['driver_rating__avg']
            return round(avg, 1) if avg else 5.0
        return 5.0