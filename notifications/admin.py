"""
FILE LOCATION: notifications/admin.py

Django admin configuration for notifications app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PushToken,
    Notification,
    NotificationPreference,
    SMSLog,
    EmailLog
)


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    """Admin interface for push tokens"""
    
    list_display = [
        'id',
        'user_display',
        'platform',
        'device_name',
        'is_active',
        'last_used',
        'created_at'
    ]
    
    list_filter = [
        'platform',
        'is_active',
        'created_at'
    ]
    
    search_fields = [
        'user__phone_number',
        'user__email',
        'token',
        'device_id'
    ]
    
    readonly_fields = [
        'token',
        'created_at',
        'updated_at',
        'last_used'
    ]
    
    def user_display(self, obj):
        """Display user phone number"""
        return obj.user.phone_number
    user_display.short_description = 'User'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for notifications"""
    
    list_display = [
        'id',
        'user_display',
        'notification_type',
        'title',
        'is_read_display',
        'delivery_status',
        'created_at'
    ]
    
    list_filter = [
        'notification_type',
        'is_read',
        'sent_via_push',
        'sent_via_sms',
        'sent_via_email',
        'created_at'
    ]
    
    search_fields = [
        'user__phone_number',
        'title',
        'body'
    ]
    
    readonly_fields = [
        'user',
        'notification_type',
        'title',
        'body',
        'data',
        'ride',
        'transaction',
        'sent_via_push',
        'sent_via_sms',
        'sent_via_email',
        'created_at',
        'read_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def user_display(self, obj):
        """Display user phone number"""
        return obj.user.phone_number
    user_display.short_description = 'User'
    
    def is_read_display(self, obj):
        """Display read status with color"""
        if obj.is_read:
            return format_html(
                '<span style="color: green;">✓ Read</span>'
            )
        return format_html(
            '<span style="color: orange;">⊗ Unread</span>'
        )
    is_read_display.short_description = 'Status'
    
    def delivery_status(self, obj):
        """Display delivery methods"""
        methods = []
        if obj.sent_via_push:
            methods.append('📱 Push')
        if obj.sent_via_sms:
            methods.append('💬 SMS')
        if obj.sent_via_email:
            methods.append('📧 Email')
        return ' | '.join(methods) if methods else '-'
    delivery_status.short_description = 'Delivered Via'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for notification preferences"""
    
    list_display = [
        'id',
        'user_display',
        'push_status',
        'sms_status',
        'email_status',
        'updated_at'
    ]
    
    list_filter = [
        'push_enabled',
        'sms_enabled',
        'email_enabled',
        'created_at'
    ]
    
    search_fields = [
        'user__phone_number',
        'user__email'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Push Notifications', {
            'fields': (
                'push_enabled',
                'push_ride_updates',
                'push_payment_updates',
                'push_promotional'
            )
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_enabled',
                'sms_ride_updates',
                'sms_payment_updates'
            )
        }),
        ('Email Notifications', {
            'fields': (
                'email_enabled',
                'email_ride_updates',
                'email_payment_updates',
                'email_promotional'
            )
        }),
        ('In-App', {
            'fields': ('inapp_enabled',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def user_display(self, obj):
        """Display user phone number"""
        return obj.user.phone_number
    user_display.short_description = 'User'
    
    def push_status(self, obj):
        """Display push notification status"""
        if obj.push_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    push_status.short_description = 'Push'
    
    def sms_status(self, obj):
        """Display SMS notification status"""
        if obj.sms_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    sms_status.short_description = 'SMS'
    
    def email_status(self, obj):
        """Display email notification status"""
        if obj.email_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: red;">✗ Disabled</span>')
    email_status.short_description = 'Email'


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    """Admin interface for SMS logs"""
    
    list_display = [
        'id',
        'phone_number',
        'message_preview',
        'status_display',
        'provider',
        'cost',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'provider',
        'created_at'
    ]
    
    search_fields = [
        'phone_number',
        'message',
        'provider_message_id'
    ]
    
    readonly_fields = [
        'user',
        'phone_number',
        'message',
        'status',
        'provider',
        'provider_message_id',
        'cost',
        'error_message',
        'notification',
        'created_at',
        'updated_at',
        'delivered_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        """Display message preview"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'sent': 'blue',
            'delivered': 'green',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Admin interface for email logs"""
    
    list_display = [
        'id',
        'recipient_email',
        'subject',
        'status_display',
        'created_at',
        'sent_at'
    ]
    
    list_filter = [
        'status',
        'created_at'
    ]
    
    search_fields = [
        'recipient_email',
        'subject',
        'body'
    ]
    
    readonly_fields = [
        'user',
        'recipient_email',
        'subject',
        'body',
        'html_body',
        'status',
        'error_message',
        'notification',
        'created_at',
        'sent_at',
        'delivered_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'sent': 'blue',
            'delivered': 'green',
            'bounced': 'purple',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False