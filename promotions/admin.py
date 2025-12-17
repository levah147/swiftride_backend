
"""
FILE LOCATION: promotions/admin.py
Enhanced admin interfaces for promotions app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import PromoCode, PromoUsage, ReferralProgram, Referral, Loyalty


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'discount_badge', 'usage_badge', 
        'validity_status', 'is_active', 'start_date', 'end_date'
    ]
    list_filter = ['discount_type', 'is_active', 'user_type', 'start_date']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['usage_count', 'created_at']
    list_per_page = 25
    date_hierarchy = 'start_date'
    actions = ['export_as_csv', 'activate_codes', 'deactivate_codes']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Discount Configuration', {
            'fields': ('discount_type', 'discount_value', 'max_discount', 'minimum_fare')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_per_user', 'user_type', 'usage_count')
        }),
        ('Validity', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )
    
    def discount_badge(self, obj):
        if obj.discount_type == 'percentage':
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">{} %</span>',
                obj.discount_value
            )
        else:
            return format_html(
                '<span style="background: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">₦{}</span>',
                obj.discount_value
            )
    discount_badge.short_description = 'Discount'
    
    def usage_badge(self, obj):
        if obj.usage_limit:
            percentage = (obj.usage_count / obj.usage_limit) * 100
            color = '#dc3545' if percentage > 80 else '#ffc107' if percentage > 50 else '#28a745'
        else:
            color = '#6c757d'
        
        usage_text = f"{obj.usage_count}"
        if obj.usage_limit:
            usage_text += f"/{obj.usage_limit}"
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, usage_text
        )
    usage_badge.short_description = 'Usage'
    
    def validity_status(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return format_html('<span style="color: #6c757d;">⊗ Inactive</span>')
        elif now < obj.start_date:
            return format_html('<span style="color: #ffc107;">⏳ Scheduled</span>')
        elif now > obj.end_date:
            return format_html('<span style="color: #dc3545;">⚠️ Expired</span>')
        elif obj.usage_limit and obj.usage_count >= obj.usage_limit:
            return format_html('<span style="color: #dc3545;">🚫 Limit Reached</span>')
        else:
            return format_html('<span style="color: #28a745;">✓ Valid</span>')
    validity_status.short_description = 'Status'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="promo_codes_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Code', 'Name', 'Discount Type', 'Discount Value', 'Max Discount',
            'Usage Limit', 'Usage Count', 'User Type', 'Min Fare',
            'Start Date', 'End Date', 'Is Active'
        ])
        
        for promo in queryset:
            writer.writerow([
                promo.code, promo.name, promo.get_discount_type_display(),
                float(promo.discount_value), float(promo.max_discount) if promo.max_discount else 'None',
                promo.usage_limit if promo.usage_limit else 'Unlimited', promo.usage_count,
                promo.get_user_type_display(), float(promo.minimum_fare),
                promo.start_date, promo.end_date, 'Yes' if promo.is_active else 'No'
            ])
        return response
    export_as_csv.short_description = '📥 Export to CSV'
    
    def activate_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promo code(s) activated.')
    activate_codes.short_description = 'Activate selected codes'
    
    def deactivate_codes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promo code(s) deactivated.')
    deactivate_codes.short_description = 'Deactivate selected codes'


@admin.register(PromoUsage)
class PromoUsageAdmin(admin.ModelAdmin):
    list_display = ['promo_code', 'user_phone', 'discount_amount', 'ride_id', 'used_at']
    list_filter = ['promo_code', 'used_at']
    search_fields = ['user__phone_number', 'promo_code__code', 'ride__id']
    readonly_fields = ['promo_code', 'user', 'ride', 'discount_amount', 'used_at']
    list_per_page = 30
    date_hierarchy = 'used_at'
    actions = ['export_usage_csv']
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    user_phone.admin_order_field = 'user__phone_number'
    
    def ride_id(self, obj):
        return f"#{obj.ride.id}"
    ride_id.short_description = 'Ride'
    
    def export_usage_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="promo_usage_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Promo Code', 'User', 'Discount Amount', 'Ride ID', 'Used At'])
        
        for usage in queryset.select_related('promo_code', 'user', 'ride'):
            writer.writerow([
                usage.promo_code.code, usage.user.phone_number,
                float(usage.discount_amount), usage.ride.id, usage.used_at
            ])
        return response
    export_usage_csv.short_description = '📥 Export to CSV'


@admin.register(ReferralProgram)
class ReferralProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'referrer_reward', 'referee_reward', 'minimum_rides', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    list_per_page = 20
    actions = ['activate_programs', 'deactivate_programs']
    
    def activate_programs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} referral program(s) activated.')
    activate_programs.short_description = 'Activate selected programs'
    
    def deactivate_programs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} referral program(s) deactivated.')
    deactivate_programs.short_description = 'Deactivate selected programs'


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'referral_code', 'referrer_phone', 'referee_phone', 
        'status_badge', 'rides_completed', 'referred_at'
    ]
    list_filter = ['status', 'referred_at', 'program']
    search_fields = ['referral_code', 'referrer__phone_number', 'referee__ phone_number']
    readonly_fields = ['referral_code', 'referred_at']
    list_per_page = 25
    date_hierarchy = 'referred_at'
    actions = ['export_referrals_csv', 'mark_as_completed', 'mark_as_rewarded']
    
    def referrer_phone(self, obj):
        return obj.referrer.phone_number
    referrer_phone.short_description = 'Referrer'
    referrer_phone.admin_order_field = 'referrer__phone_number'
    
    def referee_phone(self, obj):
        return obj.referee.phone_number
    referee_phone.short_description = 'Referee'
    referee_phone.admin_order_field = 'referee__phone_number'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'completed': '#28a745',
            'rewarded': '#007bff'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def rides_completed(self, obj):
        return f"{obj.referee_rides_completed}/{obj.program.minimum_rides}"
    rides_completed.short_description = 'Rides'
    
    def export_referrals_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="referrals_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Referral Code', 'Referrer', 'Referee', 'Status',
            'Rides Completed', 'Program', 'Referred At'
        ])
        
        for ref in queryset.select_related('referrer', 'referee', 'program'):
            writer.writerow([
                ref.referral_code, ref.referrer.phone_number, ref.referee.phone_number,
                ref.get_status_display(), ref.referee_rides_completed,
                ref.program.name, ref.referred_at
            ])
        return response
    export_referrals_csv.short_description = '📥 Export to CSV'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} referral(s) marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'
    
    def mark_as_rewarded(self, request, queryset):
        updated = queryset.update(status='rewarded')
        self.message_user(request, f'{updated} referral(s) marked as rewarded.')
    mark_as_rewarded.short_description = 'Mark as rewarded'


@admin.register(Loyalty)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ['user_phone', 'tier_badge', 'total_points', 'available_points', 'created_at']
    list_filter = ['tier', 'created_at']
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['user', 'total_points', 'available_points', 'created_at']
    list_per_page = 30
    actions = ['export_loyalty_csv', 'upgrade_to_silver', 'upgrade_to_gold', 'upgrade_to_platinum']
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    user_phone.admin_order_field = 'user__phone_number'
    
    def tier_badge(self, obj):
        colors = {
            'bronze': '#cd7f32',
            'silver': '#c0c0c0',
            'gold': '#ffd700',
            'platinum': '#e5e4e2'
        }
        text_colors = {
            'bronze': 'white',
            'silver': 'black',
            'gold': 'black',
            'platinum': 'black'
        }
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.tier, '#6c757d'),
            text_colors.get(obj.tier, 'white'),
            obj.get_tier_display().upper()
        )
    tier_badge.short_description = 'Tier'
    
    def export_loyalty_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="loyalty_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Phone', 'Tier', 'Total Points', 'Available Points', 'Created At'])
        
        for loyalty in queryset.select_related('user'):
            writer.writerow([
                loyalty.user.get_full_name(), loyalty.user.phone_number,
                loyalty.get_tier_display(), loyalty.total_points,
                loyalty.available_points, loyalty.created_at
            ])
        return response
    export_loyalty_csv.short_description = '📥 Export to CSV'
    
    def upgrade_to_silver(self, request, queryset):
        updated = queryset.update(tier='silver')
        self.message_user(request, f'{updated} user(s) upgraded to Silver.')
    upgrade_to_silver.short_description = '⬆️ Upgrade to Silver'
    
    def upgrade_to_gold(self, request, queryset):
        updated = queryset.update(tier='gold')
        self.message_user(request, f'{updated} user(s) upgraded to Gold.')
    upgrade_to_gold.short_description = '⬆️ Upgrade to Gold'
    
    def upgrade_to_platinum(self, request, queryset):
        updated = queryset.update(tier='platinum')
        self.message_user(request, f'{updated} user(s) upgraded to Platinum.')
    upgrade_to_platinum.short_description = '⬆️ Upgrade to Platinum'
