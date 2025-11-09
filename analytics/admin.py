
"""
FILE LOCATION: analytics/admin.py
"""
from django.contrib import admin
from .models import DriverEarnings, RideAnalytics, RevenueReport, UserActivity, PopularLocation

@admin.register(DriverEarnings)
class DriverEarningsAdmin(admin.ModelAdmin):
    list_display = ['driver', 'date', 'completed_rides', 'net_earnings', 'average_rating']
    list_filter = ['date', 'driver']
    search_fields = ['driver__user__phone_number']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(RideAnalytics)
class RideAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_rides', 'completed_rides', 'total_revenue', 'completion_rate']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(RevenueReport)
class RevenueReportAdmin(admin.ModelAdmin):
    list_display = ['period_type', 'start_date', 'end_date', 'gross_revenue', 'net_revenue']
    list_filter = ['period_type', 'start_date']
    readonly_fields = ['generated_at']

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'date', 'rides_count', 'engagement_score']
    list_filter = ['user_type', 'date']
    search_fields = ['user__phone_number']

@admin.register(PopularLocation)
class PopularLocationAdmin(admin.ModelAdmin):
    list_display = ['location_type', 'area', 'ride_count', 'date']
    list_filter = ['location_type', 'date']
    search_fields = ['area', 'address']


