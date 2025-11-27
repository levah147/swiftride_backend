from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from drivers.models import Driver
# Add to imports
from django.core.cache import cache

User = get_user_model()


class Ride(models.Model):
    """Main ride model - connects rider with driver"""
    
    RIDE_STATUS_CHOICES = [
        ('pending', 'Pending'),           # Waiting for driver
        ('accepted', 'Accepted'),         # Driver accepted
        ('arriving', 'Driver Arriving'),  # Driver on the way to pickup
        ('in_progress', 'In Progress'),   # Ride started
        ('completed', 'Completed'),       # Ride finished
        ('cancelled', 'Cancelled'),       # Cancelled by rider or driver
    ]
    
    RIDE_TYPE_CHOICES = [
        ('immediate', 'Immediate'),
        ('scheduled', 'Scheduled'),
    ]
    
    CANCELLATION_BY_CHOICES = [
        ('rider', 'Rider'),
        ('driver', 'Driver'),
        ('system', 'System'),
    ]
    
    
    
    
     # ADD these fields:
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rides'
    )
    vehicle_type = models.ForeignKey(
        'pricing.VehicleType',
        on_delete=models.PROTECT,
        related_name='rides',
        null=True,
        blank=True
    )
    city = models.ForeignKey(
        'pricing.City',
        on_delete=models.PROTECT,
        related_name='rides',
        null=True,  # Nullable for backward compatibility
        blank=True
    )
    
    # Fare breakdown (from pricing calculation)
    fare_hash = models.CharField(max_length=32, blank=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    time_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    surge_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)
    fuel_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cancellation_fee_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    
    # Rider Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides')
    
    # Driver Information (NEW - connects to Driver model)
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rides',
        help_text="Driver assigned to this ride"
    )
    
    # Location Information
    pickup_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    destination_location = models.CharField(max_length=255)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Ride Details
    ride_type = models.CharField(max_length=20, choices=RIDE_TYPE_CHOICES, default='immediate')
    status = models.CharField(max_length=20, choices=RIDE_STATUS_CHOICES, default='pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    # Pricing & Distance
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    # Legacy fields (KEEP for backward compatibility with existing data)
    # driver_name = models.CharField(max_length=100, null=True, blank=True)
    # driver_phone = models.CharField(max_length=20, null=True, blank=True)
    # vehicle_info = models.CharField(max_length=100, null=True, blank=True)
    
    # Cancellation Information
    cancelled_by = models.CharField(
        max_length=10,
        choices=CANCELLATION_BY_CHOICES,
        null=True,
        blank=True
    )
    cancellation_reason = models.TextField(null=True, blank=True)
    
    # Rating & Feedback
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Rider's rating of the driver (1-5)"
    )
    feedback = models.TextField(null=True, blank=True)
    
    # Timestamps
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Ride #{self.id} - {self.user.phone_number} - {self.status}"
    
    @property
    def driver_full_name(self):
        """Get driver's full name from Driver model or legacy field"""
        if self.driver:
            return self.driver.user.get_full_name()
        return "Not Assigned"
    
    @property
    def driver_phone_number(self):
        """Get driver's phone from Driver model or legacy field"""
        if self.driver:
            return self.driver.user.phone_number
        return "N/A"
    
    @property
    def vehicle_details(self):
        """Get vehicle info from Driver model or legacy field"""
        if self.driver and self.driver.current_vehicle:
            v = self.driver.current_vehicle
            return f"{v.vehicle_type.name} - {v.color} - {v.license_plate}"
        return "N/A"


class RideRequest(models.Model):
    """Tracks available rides and driver responses"""
    
    REQUEST_STATUS_CHOICES = [
        ('available', 'Available'),       # Waiting for drivers
        ('accepted', 'Accepted'),         # Driver accepted
        ('expired', 'Expired'),           # No response timeout
        ('cancelled', 'Cancelled'),       # Rider cancelled
    ]
    
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    
    # Drivers who saw this request
    notified_drivers = models.ManyToManyField(
        Driver,
        related_name='notified_rides',
        blank=True,
        help_text="Drivers who received this ride request"
    )
    
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='available')
    expires_at = models.DateTimeField(help_text="Request expires if no driver accepts")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Request for Ride #{self.ride.id} - {self.status}"


class DriverRideResponse(models.Model):
    """Individual driver responses to ride requests"""
    
    RESPONSE_CHOICES = [
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('timeout', 'Timeout'),
    ]
    
    ride_request = models.ForeignKey(
        RideRequest,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='ride_responses'
    )
    response = models.CharField(max_length=20, choices=RESPONSE_CHOICES)
    decline_reason = models.CharField(max_length=100, null=True, blank=True)
    response_time_seconds = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('ride_request', 'driver')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.driver.user.phone_number} - {self.response} - Ride #{self.ride_request.ride.id}"


# class RideTracking(models.Model):
#     """Real-time GPS tracking during ride"""
    
#     ride = models.ForeignKey(
#         Ride,
#         on_delete=models.CASCADE,
#         related_name='tracking_points'
#     )
    
#     # Current location
#     latitude = models.DecimalField(max_digits=10, decimal_places=8)
#     longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
#     # Additional data
#     speed_kmh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     bearing = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     accuracy_meters = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
#     timestamp = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         ordering = ['timestamp']
#         indexes = [
#             models.Index(fields=['ride', 'timestamp']),
#         ]
    
#     def __str__(self):
#         return f"Tracking for Ride #{self.ride.id} at {self.timestamp}"


class MutualRating(models.Model):
    """Ratings system - both rider and driver can rate each other"""
    
    ride = models.OneToOneField(
        Ride,
        on_delete=models.CASCADE,
        related_name='mutual_rating'
    )
    
    # Rider rates Driver
    rider_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Rider's rating of driver (1-5)"
    )
    rider_comment = models.TextField(null=True, blank=True)
    rider_rated_at = models.DateTimeField(null=True, blank=True)
    
    # Driver rates Rider
    driver_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Driver's rating of rider (1-5)"
    )
    driver_comment = models.TextField(null=True, blank=True)
    driver_rated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Rating for Ride #{self.ride.id}"
    
    @property
    def is_complete(self):
        """Both parties have rated"""
        return self.rider_rating is not None and self.driver_rating is not None


class Promotion(models.Model):
    """Promotional discounts and offers"""
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    discount_percentage = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    max_rides = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.discount_percentage}% off"