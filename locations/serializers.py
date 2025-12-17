"""
FILE LOCATION: locations/serializers.py

Serializers for locations app.
"""
from rest_framework import serializers
from .models import SavedLocation, RecentLocation, DriverLocation, RideTracking


class SavedLocationSerializer(serializers.ModelSerializer):
    """Serializer for saved locations"""
    
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    
    class Meta:
        model = SavedLocation
        fields = [
            'id',
            'user_phone',
            'label',
            'location_type',
            'location_type_display',
            'address',
            'latitude',
            'longitude',
            'landmark',
            'instructions',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user_phone', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate coordinates"""
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        
        if longitude and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        return data


class RecentLocationSerializer(serializers.ModelSerializer):
    """Serializer for recent locations"""
    
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = RecentLocation
        fields = [
            'id',
            'user_phone',
            'address',
            'latitude',
            'longitude',
            'search_count',
            'last_used',
            'created_at'
        ]
        read_only_fields = ['id', 'user_phone', 'search_count', 'last_used', 'created_at']


class DriverLocationSerializer(serializers.ModelSerializer):
    """Serializer for driver locations"""
    
    driver_id = serializers.IntegerField(source='driver.id', read_only=True)
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.CharField(source='driver.user.phone_number', read_only=True)
    driver_rating = serializers.DecimalField(
        source='driver.rating',
        max_digits=3,
        decimal_places=2,
        read_only=True
    )
    is_stale = serializers.BooleanField(read_only=True)
    coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = DriverLocation
        fields = [
            'id',
            'driver_id',
            'driver_name',
            'driver_phone',
            'driver_rating',
            'latitude',
            'longitude',
            'coordinates',
            'bearing',
            'speed_kmh',
            'accuracy_meters',
            'last_updated',
            'is_stale'
        ]
        read_only_fields = [
            'id',
            'driver_id',
            'driver_name',
            'driver_phone',
            'driver_rating',
            'last_updated',
            'is_stale'
        ]
    
    def get_driver_name(self, obj):
        """Get driver's full name"""
        return obj.driver.user.get_full_name() or obj.driver.user.phone_number
    
    def get_coordinates(self, obj):
        """Get coordinates as [lat, lng] array"""
        return [float(obj.latitude), float(obj.longitude)]


class DriverLocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating driver location"""
    
    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        min_value=-90,
        max_value=90,
        required=True
    )
    longitude = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        min_value=-180,
        max_value=180,
        required=True
    )
    bearing = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=360,
        required=False,
        allow_null=True
    )
    speed_kmh = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True
    )
    accuracy_meters = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True
    )


class RideTrackingSerializer(serializers.ModelSerializer):
    """Serializer for ride tracking points"""
    
    ride_id = serializers.IntegerField(source='ride.id', read_only=True)
    coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = RideTracking
        fields = [
            'id',
            'ride_id',
            'latitude',
            'longitude',
            'coordinates',
            'speed_kmh',
            'bearing',
            'accuracy_meters',
            'timestamp'
        ]
        read_only_fields = ['id', 'ride_id', 'timestamp']
    
    def get_coordinates(self, obj):
        """Get coordinates as [lat, lng] array"""
        return [float(obj.latitude), float(obj.longitude)]


class RideRouteSerializer(serializers.Serializer):
    """Serializer for complete ride route"""
    
    ride_id = serializers.IntegerField()
    total_points = serializers.IntegerField()
    total_distance_km = serializers.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = serializers.IntegerField()
    route = RideTrackingSerializer(many=True)
    pickup_location = serializers.DictField()
    destination_location = serializers.DictField()


class NearbyDriverSerializer(serializers.Serializer):
    """Serializer for nearby driver search results"""
    
    driver_id = serializers.IntegerField()
    driver_name = serializers.CharField()
    driver_phone = serializers.CharField()
    driver_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    vehicle_type = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    distance_km = serializers.DecimalField(max_digits=10, decimal_places=2)
    eta_minutes = serializers.IntegerField()
    is_available = serializers.BooleanField()


class CoordinatesSerializer(serializers.Serializer):
    """Generic coordinates serializer"""
    
    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        min_value=-90,
        max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        min_value=-180,
        max_value=180
    )


class AddressSerializer(serializers.Serializer):
    """Serializer for address with coordinates"""
    
    address = serializers.CharField(max_length=255)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    landmark = serializers.CharField(max_length=255, required=False, allow_blank=True)



