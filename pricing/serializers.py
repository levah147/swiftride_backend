from rest_framework import serializers
from .models import City, VehicleType, VehiclePricing, SurgePricing, FuelPriceAdjustment


class CitySerializer(serializers.ModelSerializer):
    available_vehicles = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = [
            'id', 'name', 'state', 'country',
            'latitude', 'longitude', 'timezone',
            'is_active', 'has_bike', 'has_keke', 'has_car', 'has_suv',
            'available_vehicles'
        ]
    
    def get_available_vehicles(self, obj):
        return obj.get_available_vehicles()


class VehiclePricingSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = VehiclePricing
        fields = [
            'id', 'city', 'city_name',
            'base_fare', 'price_per_km', 'price_per_minute',
            'minimum_fare', 'estimated_arrival_time',
            'is_active'
        ]


class VehicleTypeSerializer(serializers.ModelSerializer):
    """Detailed vehicle type with pricing"""
    
    pricing = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleType
        fields = [
            'id', 'name', 'description', 'icon_name', 'color',
            'max_passengers', 'has_luggage_space',
            'is_active', 'pricing'
        ]
    
    def get_pricing(self, obj):
        # Get city from context if provided
        city = self.context.get('city')
        pricing = obj.get_base_pricing(city)
        
        if pricing:
            return VehiclePricingSerializer(pricing).data
        return None


class VehicleTypeListSerializer(serializers.ModelSerializer):
    """Simplified vehicle type for listing (used in home screen)"""
    
    base_price = serializers.SerializerMethodField()
    price_per_km = serializers.SerializerMethodField()
    price_per_minute = serializers.SerializerMethodField()
    minimum_fare = serializers.SerializerMethodField()
    estimated_time = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleType
        fields = [
            'id', 'name', 'description', 'icon_name', 'color',
            'base_price', 'price_per_km', 'price_per_minute',
            'minimum_fare', 'estimated_time', 'available'
        ]
    
    def get_base_price(self, obj):
        pricing = self._get_pricing(obj)
        return float(pricing.base_fare) if pricing else 0.0
    
    def get_price_per_km(self, obj):
        pricing = self._get_pricing(obj)
        return float(pricing.price_per_km) if pricing else 0.0
    
    def get_price_per_minute(self, obj):
        pricing = self._get_pricing(obj)
        return float(pricing.price_per_minute) if pricing else 0.0
    
    def get_minimum_fare(self, obj):
        pricing = self._get_pricing(obj)
        return float(pricing.minimum_fare) if pricing else 0.0
    
    def get_estimated_time(self, obj):
        pricing = self._get_pricing(obj)
        return pricing.estimated_arrival_time if pricing else '5 min'
    
    def get_available(self, obj):
        return obj.is_active
    
    def _get_pricing(self, obj):
        """Helper to get pricing from context"""
        if not hasattr(self, '_pricing_cache'):
            self._pricing_cache = {}
        
        if obj.id not in self._pricing_cache:
            city = self.context.get('city')
            self._pricing_cache[obj.id] = obj.get_base_pricing(city)
        
        return self._pricing_cache[obj.id]


class FareCalculationSerializer(serializers.Serializer):
    """Serializer for fare calculation requests"""
    
    vehicle_type = serializers.ChoiceField(
        choices=['bike', 'keke', 'car', 'suv']
    )
    pickup_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    pickup_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    city_name = serializers.CharField(required=False, allow_blank=True)


class FareCalculationResponseSerializer(serializers.Serializer):
    """Response for fare calculation"""
    
    vehicle_type = serializers.CharField()
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2)
    estimated_duration_minutes = serializers.IntegerField()
    base_fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    distance_fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    time_fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    surge_multiplier = serializers.DecimalField(max_digits=3, decimal_places=2)
    fuel_adjustment = serializers.DecimalField(max_digits=5, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    
    # Breakdown for display
    breakdown = serializers.DictField(child=serializers.CharField())


class SurgePricingSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    surge_level_display = serializers.CharField(source='get_surge_level_display', read_only=True)
    
    class Meta:
        model = SurgePricing
        fields = [
            'id', 'name', 'description', 'city', 'city_name',
            'surge_level', 'surge_level_display', 'multiplier',
            'start_time', 'end_time', 'is_active'
        ]


class FuelPriceAdjustmentSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    current_adjustment = serializers.SerializerMethodField()
    
    class Meta:
        model = FuelPriceAdjustment
        fields = [
            'id', 'city', 'city_name',
            'fuel_price_per_litre', 'baseline_fuel_price',
            'adjustment_per_100_naira', 'current_adjustment',
            'is_active', 'effective_date'
        ]
    
    def get_current_adjustment(self, obj):
        return float(obj.calculate_adjustment())