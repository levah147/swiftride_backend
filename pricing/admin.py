from django.contrib import admin
from .models import City, VehicleType, VehiclePricing, SurgePricing, FuelPriceAdjustment


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'is_active', 'has_bike', 'has_keke', 'has_car', 'has_suv']
    list_filter = ['is_active', 'state']
    search_fields = ['name', 'state']
    list_editable = ['is_active', 'has_bike', 'has_keke', 'has_car', 'has_suv']
    list_per_page = 25
    actions = ['export_as_csv', 'activate_cities', 'deactivate_cities']
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cities_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'State', 'Currency', 'Latitude', 'Longitude', 'Radius (km)', 'Is Active', 'Vehicle Types'])
        
        for city in queryset:
            vehicle_types = []
            if city.has_bike: vehicle_types.append('Bike')
            if city.has_keke: vehicle_types.append('Keke')
            if city.has_car: vehicle_types.append('Car')
            if city.has_suv: vehicle_types.append('SUV')
            
            writer.writerow([
                city.name, city.state, city.currency,
                city.latitude, city.longitude, city.radius_km,
                'Yes' if city.is_active else 'No',
                ', '.join(vehicle_types)
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'
    
    def activate_cities(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} city/cities activated.')
    activate_cities.short_description = 'Activate selected cities'
    
    def deactivate_cities(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} city/cities deactivated.')
    deactivate_cities.short_description = 'Deactivate selected cities'


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'display_order', 'max_passengers']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'name']
    list_per_page = 20
    actions = ['activate_types', 'deactivate_types']
    
    def activate_types(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vehicle type(s) activated.')
    activate_types.short_description = 'Activate selected vehicle types'
    
    def deactivate_types(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vehicle type(s) deactivated.')
    deactivate_types.short_description = 'Deactivate selected vehicle types'


@admin.register(VehiclePricing)
class VehiclePricingAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle_type', 'city', 'base_fare', 'price_per_km',
        'price_per_minute', 'minimum_fare', 'is_active'
    ]
    list_filter = ['vehicle_type', 'city', 'is_active']
    search_fields = ['vehicle_type__name', 'city__name']
    list_editable = ['is_active']
    list_per_page = 30
    date_hierarchy = 'created_at'
    actions = ['export_pricing_csv', 'activate_pricing', 'deactivate_pricing']
    
    def export_pricing_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pricing_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Vehicle Type', 'City', 'Base Fare', 'Price/km', 'Price/min',
            'Min Fare', 'Max Fare', 'Cancellation Fee', 'Commission %', 'Is Active'
        ])
        
        for pricing in queryset.select_related('vehicle_type', 'city'):
            writer.writerow([
                pricing.vehicle_type.name, pricing.city.name,
                float(pricing.base_fare), float(pricing.price_per_km),
                float(pricing.price_per_minute), float(pricing.minimum_fare),
                float(pricing.maximum_fare) if pricing.maximum_fare else 'None',
                float(pricing.cancellation_fee), float(pricing.platform_commission_percentage),
                'Yes' if pricing.is_active else 'No'
            ])
        return response
    export_pricing_csv.short_description = '📥 Export to CSV'
    
    def activate_pricing(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} pricing rule(s) activated.')
    activate_pricing.short_description = 'Activate selected pricing'
    
    def deactivate_pricing(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} pricing rule(s) deactivated.')
    deactivate_pricing.short_description = 'Deactivate selected pricing'


@admin.register(SurgePricing)
class SurgePricingAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'surge_level', 'multiplier', 'is_active', 'priority']
    list_filter = ['surge_level', 'is_active', 'city']
    list_editable = ['is_active', 'priority']
    list_per_page = 25
    actions = ['activate_surge', 'deactivate_surge']
    
    def activate_surge(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} surge rule(s) activated.')
    activate_surge.short_description = 'Activate selected surge rules'
    
    def deactivate_surge(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} surge rule(s) deactivated.')
    deactivate_surge.short_description = 'Deactivate selected surge rules'


@admin.register(FuelPriceAdjustment)
class FuelPriceAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'city', 'fuel_price_per_litre', 'baseline_fuel_price',
        'adjustment_per_100_naira', 'is_active', 'effective_date'
    ]
    list_filter = ['is_active', 'city']
    list_editable = ['is_active']
    list_per_page = 20
    date_hierarchy = 'effective_date'
    actions = ['activate_adjustments', 'deactivate_adjustments']
    
    def activate_adjustments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} fuel adjustment(s) activated.')
    activate_adjustments.short_description = 'Activate selected adjustments'
    
    def deactivate_adjustments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} fuel adjustment(s) deactivated.')
    deactivate_adjustments.short_description = 'Deactivate selected adjustments'