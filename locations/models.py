
"""
FILE LOCATION: locations/models.py

Database models for locations app.
Handles GPS tracking, saved locations, and ride routes.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class SavedLocation(models.Model):
    """
    User's saved/favorite locations (home, work, etc.)
    """
    LOCATION_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_locations'
    )
    location_type = models.CharField(
        max_length=10,
        choices=LOCATION_TYPE_CHOICES
    )
    # ✅ ADD THIS FIELD (after location_type)
    label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Custom label (e.g., 'Gym', 'Mom's House', 'Favorite Restaurant')"
    )
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-90')),
            MaxValueValidator(Decimal('90'))
        ]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-180')),
            MaxValueValidator(Decimal('180'))
        ]
    )
    
    # Additional details
    landmark = models.CharField(max_length=255, blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'locations_saved_location'
        unique_together = ['user', 'location_type']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['location_type']),
        ]
    
    def __str__(self):
        display_name = self.label or self.get_location_type_display()
        return f"{self.user.phone_number} - {self.location_type}: {self.address}"


class RecentLocation(models.Model):
    """
    User's recently used locations for auto-suggestions
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recent_locations'
    )
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-90')),
            MaxValueValidator(Decimal('90'))
        ]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-180')),
            MaxValueValidator(Decimal('180'))
        ]
    )
    
    # Usage tracking
    search_count = models.IntegerField(default=1)
    last_used = models.DateTimeField(auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'locations_recent_location'
        ordering = ['-last_used']
        unique_together = ['user', 'address']
        indexes = [
            models.Index(fields=['user', '-last_used']),
            models.Index(fields=['-search_count']),
        ]
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.address} (Used {self.search_count}x)"


class DriverLocation(models.Model):
    """
    Real-time driver location tracking.
    OneToOne with Driver - stores current position.
    """
    driver = models.OneToOneField(
        'drivers.Driver',
        on_delete=models.CASCADE,
        related_name='current_location'
    )
    
    # GPS coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-90')),
            MaxValueValidator(Decimal('90'))
        ]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-180')),
            MaxValueValidator(Decimal('180'))
        ]
    )
    
    # Movement data
    bearing = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Direction of travel in degrees (0-360)"
    )
    speed_kmh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Speed in kilometers per hour"
    )
    
    # Accuracy
    accuracy_meters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS accuracy radius in meters"
    )
    
    # Timestamp
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'locations_driver_location'
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['driver', 'last_updated']),
        ]
        verbose_name = 'Driver Location'
        verbose_name_plural = 'Driver Locations'
    
    def __str__(self):
        driver_name = self.driver.user.get_full_name() or self.driver.user.phone_number
        return f"{driver_name} - ({self.latitude}, {self.longitude}) - {self.last_updated}"
    
    @property
    def coordinates(self):
        """Return coordinates as tuple"""
        return (float(self.latitude), float(self.longitude))
    
    @property
    def is_stale(self):
        """Check if location is older than 5 minutes"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(minutes=5)
        return self.last_updated < cutoff


class RideTracking(models.Model):
    """
    GPS tracking points during active rides.
    Creates a breadcrumb trail of the ride route.
    """
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='tracking_points'
    )
    
    # GPS coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-90')),
            MaxValueValidator(Decimal('90'))
        ]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        validators=[
            MinValueValidator(Decimal('-180')),
            MaxValueValidator(Decimal('180'))
        ]
    )
    
    # Movement data
    speed_kmh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Speed at this point in km/h"
    )
    bearing = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Direction of travel in degrees"
    )
    
    # Accuracy
    accuracy_meters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS accuracy in meters"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'locations_ride_tracking'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['ride', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = 'Ride Tracking Point'
        verbose_name_plural = 'Ride Tracking Points'
    
    def __str__(self):
        return f"Ride #{self.ride.id} - Point at {self.timestamp}"
    
    @property
    def coordinates(self):
        """Return coordinates as tuple"""
        return (float(self.latitude), float(self.longitude))