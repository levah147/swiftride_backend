from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import User, OTPVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin configuration for the User model."""

    list_display = [
        'phone_number', 'get_full_name_link', 'email', 'is_driver',
        'is_phone_verified', 'rating', 'total_rides', 'created_at'
    ]
    list_filter = [
        'is_driver', 'is_phone_verified', 'is_staff',
        'is_superuser', 'is_active', 'created_at'
    ]
    search_fields = ['phone_number', 'first_name', 'last_name', 'email']
    ordering = ['-created_at']
    list_select_related = True  # ✅ Improves query performance

    fieldsets = (
        ('Personal Information', {
            'fields': ('phone_number', 'first_name', 'last_name', 'email', 'profile_picture')
        }),
        ('Account Status', {
            'fields': ('is_phone_verified', 'is_driver', 'is_active')
        }),
        ('Statistics', {
            'fields': ('rating', 'total_rides')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']

    def get_full_name_link(self, obj):
        """Display full name as a clickable link to the edit page."""
        url = f"/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.get_full_name())
    get_full_name_link.short_description = 'Full Name'
    get_full_name_link.admin_order_field = 'first_name'


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """Admin interface for managing OTP Verification records."""

    list_display = [
        'phone_number', 'otp_code', 'is_verified',
        'attempts', 'status_badge', 'created_at', 'expires_at'
    ]
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['phone_number', 'otp_code']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    list_per_page = 30  # ✅ Improves admin pagination performance

    def status_badge(self, obj):
        """Display a visually styled badge for OTP status."""
        if obj.is_verified:
            color, text = ('green', 'Verified')
        elif hasattr(obj, 'is_expired') and obj.is_expired():
            color, text = ('red', 'Expired')
        elif obj.attempts >= 5:
            color, text = ('orange', 'Max Attempts')
        else:
            color, text = ('blue', 'Pending')

        return format_html(
            '<span style="display:inline-block; background-color:{}; color:white; '
            'padding:3px 8px; border-radius:4px; font-weight:600;">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'

    actions = ['mark_as_verified', 'delete_expired_otps']

    def mark_as_verified(self, request, queryset):
        """Admin action: Mark selected OTPs as verified."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} OTP(s) marked as verified.')
    mark_as_verified.short_description = '✅ Mark selected as verified'

    def delete_expired_otps(self, request, queryset):
        """Admin action: Delete expired OTPs."""
        deleted = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted[0]} expired OTP(s) deleted.')
    delete_expired_otps.short_description = '🗑️ Delete expired OTPs'
