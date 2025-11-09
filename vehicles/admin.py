from django.contrib import admin
from django.utils.html import format_html
from .models import Vehicle, VehicleDocument, VehicleImage, VehicleInspection, VehicleMaintenance

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'license_plate', 'display_name', 'driver_name', 'vehicle_type',
        'is_primary', 'roadworthy_badge', 'total_rides', 'created_at'
    ]
    list_filter = ['vehicle_type', 'is_active', 'is_verified', 'is_primary']
    search_fields = ['license_plate', 'registration_number', 'driver__user__phone_number']
    readonly_fields = ['total_rides', 'total_distance_km', 'created_at', 'updated_at']
    
    def driver_name(self, obj):
        return obj.driver.user.get_full_name()
    driver_name.short_description = 'Driver'
    
    def roadworthy_badge(self, obj):
        if obj.is_roadworthy:
            return format_html(
                '<span style="background: green; color: white; padding: 3px 10px; border-radius: 3px;">✓ Roadworthy</span>'
            )
        return format_html(
            '<span style="background: red; color: white; padding: 3px 10px; border-radius: 3px;">✗ Not Roadworthy</span>'
        )
    roadworthy_badge.short_description = 'Status'


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'document_type', 'is_verified', 'expiry_date', 'is_expired', 'uploaded_at']
    list_filter = ['document_type', 'is_verified']
    search_fields = ['vehicle__license_plate']

@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'image_type', 'uploaded_at']
    list_filter = ['image_type']

@admin.register(VehicleInspection)
class VehicleInspectionAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'inspection_date', 'inspection_status', 'inspector', 'next_inspection_due']
    list_filter = ['inspection_status']

@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'maintenance_type', 'cost', 'maintenance_date']
    list_filter = ['maintenance_type']