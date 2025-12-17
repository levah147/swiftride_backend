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
    list_per_page = 25  # Pagination
    date_hierarchy = 'created_at'  # Date drill-down
    actions = ['export_as_csv', 'activate_vehicles', 'deactivate_vehicles', 'verify_vehicles']
    
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
    
    def export_as_csv(self, request, queryset):
        """Export selected vehicles to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vehicles_export.csv"'
        
        writer = csv.writer(response)
        # Write header
        writer.writerow([
            'License Plate', 'Driver Name', 'Driver Phone', 'Vehicle Type',
            'Make', 'Model', 'Year', 'Color', 'Registration Number',
            'Registration Expiry', 'Insurance Company', 'Insurance Expiry',
            'Is Active', 'Is Verified', 'Is Roadworthy', 'Total Rides',
            'Total Distance (km)', 'Created At'
        ])
        
        # Write data
        for vehicle in queryset.select_related('driver__user', 'vehicle_type'):
            writer.writerow([
                vehicle.license_plate,
                vehicle.driver.user.get_full_name(),
                vehicle.driver.user.phone_number,
                vehicle.vehicle_type.name,
                vehicle.make,
                vehicle.model,
                vehicle.year,
                vehicle.color,
                vehicle.registration_number,
                vehicle.registration_expiry,
                vehicle.insurance_company,
                vehicle.insurance_expiry,
                'Yes' if vehicle.is_active else 'No',
                'Yes' if vehicle.is_verified else 'No',
                'Yes' if vehicle.is_roadworthy else 'No',
                vehicle.total_rides,
                vehicle.total_distance_km if vehicle.total_distance_km else 0,
                vehicle.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_as_csv.short_description = '📥 Export selected vehicles to CSV'
    
    def activate_vehicles(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vehicle(s) activated.')
    activate_vehicles.short_description = 'Activate selected vehicles'
    
    def deactivate_vehicles(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vehicle(s) deactivated.')
    deactivate_vehicles.short_description = 'Deactivate selected vehicles'
    
    def verify_vehicles(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} vehicle(s) verified.')
    verify_vehicles.short_description = 'Verify selected vehicles'


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