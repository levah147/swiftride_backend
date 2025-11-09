
"""
FILE LOCATION: promotions/admin.py
"""
from django.contrib import admin
from .models import PromoCode, PromoUsage, ReferralProgram, Referral, Loyalty

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'discount_type', 'discount_value', 'usage_count', 'is_active']
    list_filter = ['discount_type', 'is_active', 'start_date']
    search_fields = ['code', 'name']

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referral_code', 'referrer', 'referee', 'status', 'referred_at']
    list_filter = ['status', 'referred_at']
    search_fields = ['referral_code', 'referrer__phone_number', 'referee__phone_number']

@admin.register(Loyalty)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'available_points', 'tier']
    list_filter = ['tier']
    search_fields = ['user__phone_number']


