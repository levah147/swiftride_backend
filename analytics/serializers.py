"""
FILE LOCATION: analytics/serializers.py

Serializers for analytics app.
"""
from rest_framework import serializers
from .models import (
    DriverEarnings,
    RideAnalytics,
    RevenueReport,
    UserActivity,
    PopularLocation
)
from django.contrib.auth import get_user_model

User = get_user_model()


class DriverEarningsSerializer(serializers.ModelSerializer):
    """Serializer for driver earnings"""
    
    driver_name = serializers.SerializerMethodField()
    earnings_per_ride = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    earnings_per_hour = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = DriverEarnings
        fields = [
            'id',
            'driver',
            'driver_name',
            'date',
            'total_rides',
            'completed_rides',
            'cancelled_rides',
            'gross_earnings',
            'platform_fee',
            'net_earnings',
            'tips_received',
            'bonuses',
            'total_distance_km',
            'total_duration_minutes',
            'online_hours',
            'average_rating',
            'earnings_per_ride',
            'earnings_per_hour',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_driver_name(self, obj):
        """Get driver's display name"""
        user = obj.driver.user
        if user.first_name:
            return f"{user.first_name} {user.last_name}".strip()
        return user.phone_number


class DriverEarningsSummarySerializer(serializers.Serializer):
    """Summary of driver earnings over a period"""
    
    total_rides = serializers.IntegerField()
    completed_rides = serializers.IntegerField()
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_tips = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_bonuses = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_daily_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_distance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)


class RideAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for ride analytics"""
    
    completion_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    cancellation_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = RideAnalytics
        fields = [
            'id',
            'date',
            'total_rides',
            'completed_rides',
            'cancelled_by_rider',
            'cancelled_by_driver',
            'no_driver_found',
            'active_riders',
            'new_riders',
            'active_drivers',
            'new_drivers',
            'total_revenue',
            'platform_revenue',
            'driver_earnings',
            'total_distance_km',
            'total_duration_minutes',
            'average_ride_distance',
            'average_ride_duration',
            'average_wait_time_minutes',
            'average_rider_rating',
            'average_driver_rating',
            'hourly_rides',
            'completion_rate',
            'cancellation_rate',
            'created_at'
        ]
        read_only_fields = fields


class RevenueReportSerializer(serializers.ModelSerializer):
    """Serializer for revenue reports"""
    
    period_display = serializers.CharField(
        source='get_period_type_display',
        read_only=True
    )
    
    class Meta:
        model = RevenueReport
        fields = [
            'id',
            'period_type',
            'period_display',
            'start_date',
            'end_date',
            'gross_revenue',
            'platform_revenue',
            'driver_payouts',
            'refunds',
            'net_revenue',
            'total_transactions',
            'successful_transactions',
            'failed_transactions',
            'refund_count',
            'payment_breakdown',
            'average_transaction_value',
            'generated_at'
        ]
        read_only_fields = fields


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activity"""
    
    user_name = serializers.SerializerMethodField()
    engagement_score = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id',
            'user',
            'user_name',
            'user_type',
            'date',
            'session_count',
            'total_session_duration',
            'rides_count',
            'searches_count',
            'bookings_count',
            'app_opens',
            'notifications_received',
            'notifications_clicked',
            'online_hours',
            'ride_requests_received',
            'ride_requests_accepted',
            'engagement_score',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_user_name(self, obj):
        """Get user's display name"""
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.phone_number


class PopularLocationSerializer(serializers.ModelSerializer):
    """Serializer for popular locations"""
    
    location_type_display = serializers.CharField(
        source='get_location_type_display',
        read_only=True
    )
    
    class Meta:
        model = PopularLocation
        fields = [
            'id',
            'location_type',
            'location_type_display',
            'latitude',
            'longitude',
            'address',
            'area',
            'city',
            'ride_count',
            'date',
            'hourly_distribution',
            'created_at'
        ]
        read_only_fields = fields


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard overview statistics"""
    
    # Today's stats
    today_rides = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_active_drivers = serializers.IntegerField()
    today_active_riders = serializers.IntegerField()
    
    # This week
    week_rides = serializers.IntegerField()
    week_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # This month
    month_rides = serializers.IntegerField()
    month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Totals
    total_riders = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_rides_all_time = serializers.IntegerField()
    
    # Growth rates
    rides_growth_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    revenue_growth_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class PeakHoursSerializer(serializers.Serializer):
    """Serializer for peak hours analysis"""
    
    hour = serializers.IntegerField()
    ride_count = serializers.IntegerField()
    average_fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    demand_level = serializers.CharField()  # low, medium, high, peak


class TopDriverSerializer(serializers.Serializer):
    """Serializer for top performing drivers"""
    
    driver_id = serializers.IntegerField()
    driver_name = serializers.CharField()
    phone_number = serializers.CharField()
    total_rides = serializers.IntegerField()
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class RevenueBreakdownSerializer(serializers.Serializer):
    """Serializer for revenue breakdown by category"""
    
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    count = serializers.IntegerField()


class RidesTrendSerializer(serializers.Serializer):
    """Serializer for rides trend over time"""
    
    date = serializers.DateField()
    rides_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_fare = serializers.DecimalField(max_digits=10, decimal_places=2)


class PerformanceMetricsSerializer(serializers.Serializer):
    """Serializer for performance metrics"""
    
    metric_name = serializers.CharField()
    current_value = serializers.FloatField()
    previous_value = serializers.FloatField()
    change_percentage = serializers.FloatField()
    trend = serializers.CharField()  # up, down, stable


class HeatMapDataSerializer(serializers.Serializer):
    """Serializer for heat map data"""
    
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    intensity = serializers.IntegerField()
    area = serializers.CharField()