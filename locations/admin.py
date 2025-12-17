from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import SavedLocation, RecentLocation, DriverLocation, RideTracking


# -----------------------------
# Saved Location Admin
# -----------------------------
@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'location_type', 'address', 'coordinates', 'is_active', 'created_at')
    list_filter = ('location_type', 'is_active', 'created_at')
    search_fields = ('user__phone_number', 'address')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = ['export_as_csv', 'activate_locations', 'deactivate_locations']
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    user_phone.admin_order_field = 'user__phone_number'
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = 'Coordinates'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="saved_locations_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Phone', 'Type', 'Label', 'Address', 'Latitude', 'Longitude', 'Is Active'])
        
        for loc in queryset.select_related('user'):
            writer.writerow([
                loc.user.get_full_name(), loc.user.phone_number,
                loc.get_location_type_display(), loc.label or '',
                loc.address, float(loc.latitude), float(loc.longitude),
                'Yes' if loc.is_active else 'No'
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'
    
    def activate_locations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} location(s) activated.')
    activate_locations.short_description = 'Activate selected locations'
    
    def deactivate_locations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} location(s) deactivated.')
    deactivate_locations.short_description = 'Deactivate selected locations'


# -----------------------------
# Recent Location Admin
# -----------------------------
@admin.register(RecentLocation)
class RecentLocationAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'address_preview', 'search_count', 'last_used', 'created_at')
    search_fields = ('user__phone_number', 'address')
    readonly_fields = ('created_at', 'last_used')
    date_hierarchy = 'last_used'
    list_per_page = 25
    actions = ['export_as_csv']
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    user_phone.admin_order_field = 'user__phone_number'
    
    def address_preview(self, obj):
        return obj.address[:60] + '...' if len(obj.address) > 60 else obj.address
    address_preview.short_description = 'Address'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="recent_locations_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Phone', 'Address', 'Latitude', 'Longitude', 'Search Count', 'Last Used'])
        
        for loc in queryset.select_related('user'):
            writer.writerow([
                loc.user.get_full_name(), loc.user.phone_number,
                loc.address, float(loc.latitude), float(loc.longitude),
                loc.search_count, loc.last_used
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'


# -----------------------------
# Driver Location Admin
# -----------------------------
@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = (
        'driver_info',
        'coordinates',
        'speed_kmh',
        'bearing',
        'accuracy_meters',
        'staleness_indicator',
        'last_updated',
    )
    search_fields = ('driver__user__phone_number', 'driver__user__first_name', 'driver__user__last_name')
    readonly_fields = ('last_updated',)
    date_hierarchy = 'last_updated'
    list_per_page = 25
    actions = ['export_as_csv']
    
    def driver_info(self, obj):
        return f"{obj.driver.user.get_full_name()} ({obj.driver.user.phone_number})"
    driver_info.short_description = 'Driver'
    driver_info.admin_order_field = 'driver__user__phone_number'
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = 'Coordinates'
    
    def staleness_indicator(self, obj):
        if obj.is_stale:
            minutes_old = (timezone.now() - obj.last_updated).total_seconds() / 60
            return format_html(
                '<span style="color: red;">⚠️ Stale ({:.0f} min old)</span>',
                minutes_old
            )
        return format_html('<span style="color: green;">✓ Fresh</span>')
    staleness_indicator.short_description = 'Status'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="driver_locations_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Driver', 'Phone', 'Latitude', 'Longitude', 'Speed (km/h)',
            'Bearing', 'Accuracy (m)', 'Is Stale', 'Last Updated'
        ])
        
        for loc in queryset.select_related('driver__user'):
            writer.writerow([
                loc.driver.user.get_full_name(), loc.driver.user.phone_number,
                float(loc.latitude), float(loc.longitude), loc.speed_kmh or 0,
                loc.bearing or 0, loc.accuracy_meters or 0,
                'Yes' if loc.is_stale else 'No', loc.last_updated
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'


# -----------------------------
# Ride Tracking Admin
# -----------------------------
@admin.register(RideTracking)
class RideTrackingAdmin(admin.ModelAdmin):
    list_display = (
        'ride_id',
        'coordinates',
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
    actions = ['export_as_csv']
    
    def ride_id(self, obj):
        return f"#{obj.ride.id}"
    ride_id.short_description = 'Ride'
    ride_id.admin_order_field = 'ride__id'
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = 'Coordinates'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ride_tracking_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Ride ID', 'Latitude', 'Longitude', 'Speed (km/h)',
            'Bearing', 'Accuracy (m)', 'Timestamp'
        ])
        
        for track in queryset.select_related('ride'):
            writer.writerow([
                track.ride.id, float(track.latitude), float(track.longitude),
                track.speed_kmh or 0, track.bearing or 0,
                track.accuracy_meters or 0, track.timestamp
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'
