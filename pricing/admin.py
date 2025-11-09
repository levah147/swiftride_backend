from django.contrib import admin
from .models import City, VehicleType, VehiclePricing, SurgePricing, FuelPriceAdjustment


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'is_active', 'has_bike', 'has_keke', 'has_car', 'has_suv']
    list_filter = ['is_active', 'state']
    search_fields = ['name', 'state']
    list_editable = ['is_active', 'has_bike', 'has_keke', 'has_car', 'has_suv']


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'display_order', 'max_passengers']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'name']


@admin.register(VehiclePricing)
class VehiclePricingAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle_type', 'city', 'base_fare', 'price_per_km',
        'price_per_minute', 'minimum_fare', 'is_active'
    ]
    list_filter = ['vehicle_type', 'city', 'is_active']
    search_fields = ['vehicle_type__name', 'city__name']
    list_editable = ['is_active']


@admin.register(SurgePricing)
class SurgePricingAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'surge_level', 'multiplier', 'is_active', 'priority']
    list_filter = ['surge_level', 'is_active', 'city']
    list_editable = ['is_active', 'priority']


@admin.register(FuelPriceAdjustment)
class FuelPriceAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'city', 'fuel_price_per_litre', 'baseline_fuel_price',
        'adjustment_per_100_naira', 'is_active', 'effective_date'
    ]
    list_filter = ['is_active', 'city']
    list_editable = ['is_active']