"""
FILE LOCATION: analytics/models.py

Analytics and reporting models for SwiftRide.
Track metrics, generate insights, and create reports.

Models:
- DriverEarnings: Daily driver earnings tracking
- RideAnalytics: Ride statistics and metrics
- RevenueReport: Financial reports
- UserActivity: User engagement metrics
- PopularLocation: Heat map data
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Q
from decimal import Decimal

User = get_user_model()


class DriverEarnings(models.Model):
    """Daily earnings tracking for drivers"""
    
    driver = models.ForeignKey(
        'drivers.Driver',
        on_delete=models.CASCADE,
        related_name='earnings_records'
    )
    
    date = models.DateField(db_index=True)
    
    # Ride counts
    total_rides = models.IntegerField(default=0)
    completed_rides = models.IntegerField(default=0)
    cancelled_rides = models.IntegerField(default=0)
    
    # Earnings
    gross_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total fare before platform fee"
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    net_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Earnings after platform fee"
    )
    
    # Tips and bonuses
    tips_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    bonuses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Performance
    total_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_duration_minutes = models.IntegerField(default=0)
    online_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_driver_earnings'
        unique_together = [['driver', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['driver', '-date']),
            models.Index(fields=['date']),
        ]
        verbose_name = 'Driver Earnings'
        verbose_name_plural = 'Driver Earnings'
    
    def __str__(self):
        return f"{self.driver.user.phone_number} - {self.date}"
    
    @property
    def earnings_per_ride(self):
        """Calculate average earnings per ride"""
        if self.completed_rides > 0:
            return self.net_earnings / self.completed_rides
        return Decimal('0.00')
    
    @property
    def earnings_per_hour(self):
        """Calculate earnings per hour online"""
        if self.online_hours > 0:
            return self.net_earnings / self.online_hours
        return Decimal('0.00')


class RideAnalytics(models.Model):
    """Daily ride statistics and metrics"""
    
    date = models.DateField(unique=True, db_index=True)
    
    # Ride counts
    total_rides = models.IntegerField(default=0)
    completed_rides = models.IntegerField(default=0)
    cancelled_by_rider = models.IntegerField(default=0)
    cancelled_by_driver = models.IntegerField(default=0)
    no_driver_found = models.IntegerField(default=0)
    
    # User metrics
    active_riders = models.IntegerField(default=0)
    new_riders = models.IntegerField(default=0)
    active_drivers = models.IntegerField(default=0)
    new_drivers = models.IntegerField(default=0)
    
    # Financial
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    platform_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    driver_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Distance and time
    total_distance_km = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_duration_minutes = models.IntegerField(default=0)
    average_ride_distance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    average_ride_duration = models.IntegerField(default=0)
    
    # Performance
    average_wait_time_minutes = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    average_rider_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )
    average_driver_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Peak hours (JSON field storing hourly data)
    hourly_rides = models.JSONField(
        default=dict,
        help_text="Rides per hour {0: 5, 1: 3, ...}"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_ride_analytics'
        ordering = ['-date']
        verbose_name = 'Ride Analytics'
        verbose_name_plural = 'Ride Analytics'
    
    def __str__(self):
        return f"Analytics for {self.date}"
    
    @property
    def completion_rate(self):
        """Calculate ride completion rate percentage"""
        if self.total_rides > 0:
            return (self.completed_rides / self.total_rides) * 100
        return 0
    
    @property
    def cancellation_rate(self):
        """Calculate cancellation rate percentage"""
        if self.total_rides > 0:
            cancelled = self.cancelled_by_rider + self.cancelled_by_driver
            return (cancelled / self.total_rides) * 100
        return 0


class RevenueReport(models.Model):
    """Monthly/weekly revenue reports"""
    
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    
    # Revenue breakdown
    gross_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    platform_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    driver_payouts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    net_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Transaction counts
    total_transactions = models.IntegerField(default=0)
    successful_transactions = models.IntegerField(default=0)
    failed_transactions = models.IntegerField(default=0)
    refund_count = models.IntegerField(default=0)
    
    # Payment methods breakdown
    payment_breakdown = models.JSONField(
        default=dict,
        help_text="Revenue by payment method"
    )
    
    # Additional metrics
    average_transaction_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_revenue_report'
        ordering = ['-start_date']
        unique_together = [['period_type', 'start_date', 'end_date']]
        verbose_name = 'Revenue Report'
        verbose_name_plural = 'Revenue Reports'
    
    def __str__(self):
        return f"{self.get_period_type_display()} Report: {self.start_date} to {self.end_date}"


class UserActivity(models.Model):
    """Track user engagement and activity"""
    
    USER_TYPE_CHOICES = [
        ('rider', 'Rider'),
        ('driver', 'Driver'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    date = models.DateField(db_index=True)
    
    # Session data
    session_count = models.IntegerField(default=0)
    total_session_duration = models.IntegerField(
        default=0,
        help_text="Total minutes active"
    )
    
    # Activity counts
    rides_count = models.IntegerField(default=0)
    searches_count = models.IntegerField(default=0)
    bookings_count = models.IntegerField(default=0)
    
    # Engagement
    app_opens = models.IntegerField(default=0)
    notifications_received = models.IntegerField(default=0)
    notifications_clicked = models.IntegerField(default=0)
    
    # For drivers
    online_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    ride_requests_received = models.IntegerField(default=0)
    ride_requests_accepted = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_user_activity'
        unique_together = [['user', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user_type', 'date']),
        ]
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.date}"
    
    @property
    def engagement_score(self):
        """Calculate user engagement score (0-100)"""
        score = 0
        score += min(self.app_opens * 5, 20)  # Max 20 points
        score += min(self.session_count * 10, 30)  # Max 30 points
        score += min(self.rides_count * 10, 30)  # Max 30 points
        
        if self.notifications_received > 0:
            click_rate = (self.notifications_clicked / self.notifications_received) * 100
            score += min(click_rate / 5, 20)  # Max 20 points
        
        return min(score, 100)


class PopularLocation(models.Model):
    """Track popular pickup and dropoff locations for heat maps"""
    
    LOCATION_TYPE_CHOICES = [
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
    ]
    
    location_type = models.CharField(max_length=10, choices=LOCATION_TYPE_CHOICES)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Grid cell for grouping nearby locations
    grid_cell = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Grid cell identifier (lat_lng rounded)"
    )
    
    # Address info
    address = models.CharField(max_length=500, blank=True)
    area = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Statistics
    ride_count = models.IntegerField(default=0)
    date = models.DateField(db_index=True)
    
    # Time-based breakdown
    hourly_distribution = models.JSONField(
        default=dict,
        help_text="Rides per hour"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_popular_location'
        ordering = ['-ride_count']
        indexes = [
            models.Index(fields=['location_type', 'date']),
            models.Index(fields=['grid_cell', 'date']),
            models.Index(fields=['-ride_count']),
        ]
        verbose_name = 'Popular Location'
        verbose_name_plural = 'Popular Locations'
    
    def __str__(self):
        return f"{self.get_location_type_display()} - {self.area} ({self.ride_count} rides)"
    
    @classmethod
    def get_grid_cell(cls, latitude, longitude, precision=2):
        """Generate grid cell identifier from coordinates"""
        lat_rounded = round(float(latitude), precision)
        lng_rounded = round(float(longitude), precision)
        return f"{lat_rounded}_{lng_rounded}"