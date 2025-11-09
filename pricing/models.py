from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone


class City(models.Model):
    """Cities where SwiftRide operates"""
    
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Nigeria')
    
    # Geographic data
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="City center latitude"
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="City center longitude"
    )
    radius_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('50.00'),
        help_text="Service radius from city center in km"
    )
    
    # Service availability
    is_active = models.BooleanField(
        default=True, 
        help_text="Is service available in this city?"
    )
    has_bike = models.BooleanField(default=True)
    has_keke = models.BooleanField(default=True)
    has_car = models.BooleanField(default=True)
    has_suv = models.BooleanField(default=True)
    
    # Settings
    timezone = models.CharField(max_length=50, default='Africa/Lagos')
    currency = models.CharField(max_length=10, default='NGN')
    currency_symbol = models.CharField(max_length=5, default='₦')
    
    # Operational settings
    minimum_driver_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Search radius for nearby drivers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_city'
        verbose_name_plural = "Cities"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def clean(self):
        """Validate city data"""
        super().clean()
        
        # Validate coordinates
        if self.latitude:
            if not (-90 <= self.latitude <= 90):
                raise ValidationError({
                    'latitude': 'Latitude must be between -90 and 90'
                })
        
        if self.longitude:
            if not (-180 <= self.longitude <= 180):
                raise ValidationError({
                    'longitude': 'Longitude must be between -180 and 180'
                })
        
        # Validate at least one vehicle type is enabled
        if not any([self.has_bike, self.has_keke, self.has_car, self.has_suv]):
            raise ValidationError(
                'At least one vehicle type must be enabled for the city'
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name}, {self.state}"
    
    def get_available_vehicles(self):
        """Get list of available vehicle types in this city"""
        available = []
        if self.has_bike:
            available.append('bike')
        if self.has_keke:
            available.append('keke')
        if self.has_car:
            available.append('car')
        if self.has_suv:
            available.append('suv')
        return available
    
    def is_within_service_area(self, latitude, longitude):
        """Check if coordinates are within service area"""
        if not self.latitude or not self.longitude:
            return True  # No boundary defined, allow all
        
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        lat1, lon1 = radians(float(self.latitude)), radians(float(self.longitude))
        lat2, lon2 = radians(float(latitude)), radians(float(longitude))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return distance <= float(self.radius_km)


class VehicleType(models.Model):
    """Vehicle types available on the platform"""
    
    VEHICLE_CHOICES = [
        ('bike', 'Bike (Okada)'),
        ('keke', 'Keke (Tricycle)'),
        ('car', 'Car (Standard)'),
        ('suv', 'SUV (Premium)'),
    ]
    
    id = models.CharField(
        max_length=20,
        primary_key=True,
        choices=VEHICLE_CHOICES,
        help_text="Unique identifier for vehicle type"
    )
    name = models.CharField(max_length=50)
    description = models.TextField()
    
    # Visual
    icon_name = models.CharField(
        max_length=50,
        default='directions_car',
        help_text="Material icon name for Flutter"
    )
    color = models.CharField(
        max_length=7,
        default='#0066FF',
        help_text="Hex color code"
    )
    
    # Capacity
    max_passengers = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    has_luggage_space = models.BooleanField(default=False)
    
    # Platform commission
    platform_commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Platform commission percentage"
    )
    
    # Availability
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_type'
        ordering = ['display_order', 'name']
        verbose_name = 'Vehicle Type'
        verbose_name_plural = 'Vehicle Types'
    
    def __str__(self):
        return self.name
    
    def get_base_pricing(self, city=None):
        """Get base pricing for this vehicle type in a city"""
        if city:
            try:
                return VehiclePricing.objects.get(
                    vehicle_type=self, 
                    city=city,
                    is_active=True
                )
            except VehiclePricing.DoesNotExist:
                pass
        
        # Return default pricing
        return VehiclePricing.objects.filter(
            vehicle_type=self,
            is_default=True,
            is_active=True
        ).first()


class VehiclePricing(models.Model):
    """Pricing structure for vehicles per city"""
    
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        related_name='pricing'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='vehicle_pricing',
        null=True,
        blank=True,
        help_text="Leave blank for default pricing"
    )
    
    # Base pricing
    base_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base fare in Naira"
    )
    price_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per kilometer"
    )
    price_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per minute (for traffic)"
    )
    
    # Minimum/Maximum fare
    minimum_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum fare"
    )
    maximum_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum fare (optional cap)"
    )
    
    # Cancellation fee
    cancellation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fee charged for cancellation after driver accepts"
    )
    
    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    estimated_arrival_time = models.CharField(
        max_length=20,
        default='5 min',
        help_text="Typical driver arrival time"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_pricing'
        unique_together = ('vehicle_type', 'city')
        ordering = ['vehicle_type', 'city']
        indexes = [
            models.Index(fields=['vehicle_type', 'city', 'is_active']),
            models.Index(fields=['is_default', 'is_active']),
        ]
        verbose_name = 'Vehicle Pricing'
        verbose_name_plural = 'Vehicle Pricing'
    
    def clean(self):
        """Validate pricing data"""
        super().clean()
        
        # Validate maximum fare is greater than minimum
        if self.maximum_fare and self.maximum_fare < self.minimum_fare:
            raise ValidationError({
                'maximum_fare': 'Maximum fare must be greater than minimum fare'
            })
        
        # Ensure only one default pricing per vehicle type
        if self.is_default:
            existing = VehiclePricing.objects.filter(
                vehicle_type=self.vehicle_type,
                is_default=True
            ).exclude(pk=self.pk)
            
            if existing.exists():
                raise ValidationError({
                    'is_default': f'Default pricing already exists for {self.vehicle_type.name}'
                })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        city_name = self.city.name if self.city else "Default"
        return f"{self.vehicle_type.name} - {city_name}"
    
    def calculate_fare(self, distance_km, duration_minutes, surge_multiplier=1.0, fuel_adjustment=0.0):
        """Calculate total fare based on distance and time"""
        # Base calculation
        fare = (
            float(self.base_fare) +
            (float(self.price_per_km) * distance_km) +
            (float(self.price_per_minute) * duration_minutes)
        )
        
        # Add fuel adjustment
        fare += fuel_adjustment
        
        # Apply surge multiplier
        fare *= surge_multiplier
        
        # Apply minimum fare
        fare = max(fare, float(self.minimum_fare))
        
        # Apply maximum fare cap if set
        if self.maximum_fare:
            fare = min(fare, float(self.maximum_fare))
        
        return round(Decimal(str(fare)), 2)
    
    def calculate_driver_earnings(self, total_fare):
        """Calculate driver's earnings after platform commission"""
        commission_rate = self.vehicle_type.platform_commission_percentage / Decimal('100')
        platform_fee = total_fare * commission_rate
        driver_earnings = total_fare - platform_fee
        
        return {
            'total_fare': total_fare,
            'platform_fee': round(platform_fee, 2),
            'driver_earnings': round(driver_earnings, 2),
            'commission_percentage': float(self.vehicle_type.platform_commission_percentage)
        }


class SurgePricing(models.Model):
    """Dynamic surge pricing rules"""
    
    SURGE_LEVEL_CHOICES = [
        ('normal', 'Normal (1.0x)'),
        ('light', 'Light Surge (1.2x)'),
        ('moderate', 'Moderate Surge (1.5x)'),
        ('heavy', 'Heavy Surge (2.0x)'),
        ('extreme', 'Extreme Surge (3.0x)'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='surge_rules',
        null=True,
        blank=True,
        help_text="Specific city, or all cities if blank"
    )
    
    # Surge multiplier
    surge_level = models.CharField(
        max_length=20,
        choices=SURGE_LEVEL_CHOICES,
        default='normal'
    )
    multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.0'),
        validators=[
            MinValueValidator(Decimal('1.0')), 
            MaxValueValidator(Decimal('5.0'))
        ],
        help_text="Fare multiplier"
    )
    
    # Time-based rules
    start_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="Start time (leave blank for all day)"
    )
    end_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="End time (leave blank for all day)"
    )
    
    # Day-based rules
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)
    
    # Conditions
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority rules override lower ones"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_surge_pricing'
        ordering = ['-priority', '-multiplier']
        verbose_name = 'Surge Pricing Rule'
        verbose_name_plural = 'Surge Pricing Rules'
        indexes = [
            models.Index(fields=['city', 'is_active', '-priority']),
        ]
    
    def clean(self):
        """Validate surge pricing data"""
        super().clean()
        
        # Validate time range
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time'
                })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.multiplier}x"
    
    def is_active_now(self):
        """Check if this surge rule is currently active"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        current_time = now.time()
        current_day = now.strftime('%A').lower()
        
        # Check day
        day_active = getattr(self, current_day, False)
        if not day_active:
            return False
        
        # Check time
        if self.start_time and self.end_time:
            if not (self.start_time <= current_time <= self.end_time):
                return False
        
        return True
    
    @staticmethod
    def get_current_multiplier(city=None):
        """Get highest priority active surge multiplier"""
        query = models.Q(is_active=True)
        
        if city:
            query &= (models.Q(city=city) | models.Q(city__isnull=True))
        
        rules = SurgePricing.objects.filter(query).select_related('city')
        
        for rule in rules:
            if rule.is_active_now():
                return float(rule.multiplier)
        
        return 1.0  # No surge


class FuelPriceAdjustment(models.Model):
    """Dynamic pricing adjustment based on fuel prices"""
    
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='fuel_adjustments',
        null=True,
        blank=True
    )
    
    # Fuel price
    fuel_price_per_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Current fuel price per litre in Naira"
    )
    baseline_fuel_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('800.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Baseline price (no adjustment below this)"
    )
    
    # Adjustment
    adjustment_per_100_naira = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Add per km for every ₦100 fuel increase"
    )
    
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(auto_now_add=True)
    
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_fuel_price_adjustment'
        ordering = ['-effective_date']
        verbose_name = 'Fuel Price Adjustment'
        verbose_name_plural = 'Fuel Price Adjustments'
        indexes = [
            models.Index(fields=['city', 'is_active', '-effective_date']),
        ]
    
    def __str__(self):
        city_name = self.city.name if self.city else "All Cities"
        return f"{city_name} - ₦{self.fuel_price_per_litre}/L"
    
    def calculate_adjustment(self):
        """Calculate per-km adjustment based on fuel price"""
        if self.fuel_price_per_litre <= self.baseline_fuel_price:
            return Decimal('0.00')
        
        price_increase = self.fuel_price_per_litre - self.baseline_fuel_price
        increments = price_increase / Decimal('100.00')
        adjustment = increments * self.adjustment_per_100_naira
        
        return round(adjustment, 2)