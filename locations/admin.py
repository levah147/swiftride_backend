from django.contrib import admin
from .models import SavedLocation, RecentLocation, DriverLocation, RideTracking


# -----------------------------
# Saved Location Admin
# -----------------------------
@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'location_type', 'address', 'latitude', 'longitude', 'is_active', 'created_at')
    list_filter = ('location_type', 'is_active', 'created_at')
    search_fields = ('user__phone_number', 'address')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_per_page = 25


# -----------------------------
# Recent Location Admin
# -----------------------------
@admin.register(RecentLocation)
class RecentLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'search_count', 'last_used', 'created_at')
    search_fields = ('user__phone_number', 'address')
    readonly_fields = ('created_at', 'last_used')
    date_hierarchy = 'last_used'
    list_per_page = 25


# -----------------------------
# Driver Location Admin
# -----------------------------
@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = (
        'driver',
        'latitude',
        'longitude',
        'speed_kmh',
        'bearing',
        'accuracy_meters',
        'last_updated',
    )
    search_fields = ('driver__user__phone_number', 'driver__user__first_name', 'driver__user__last_name')
    readonly_fields = ('last_updated',)
    date_hierarchy = 'last_updated'
    list_per_page = 25


# -----------------------------
# Ride Tracking Admin
# -----------------------------
@admin.register(RideTracking)
class RideTrackingAdmin(admin.ModelAdmin):
    list_display = (
        'ride',
        'latitude',
        'longitude',
        'speed_kmh',
        'bearing',
        'accuracy_meters',
        'timestamp',
    )
    list_filter = ('ride__status',)
    search_fields = ('ride__id', 'ride__user__phone_number', 'ride__driver__user__phone_number')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 25
