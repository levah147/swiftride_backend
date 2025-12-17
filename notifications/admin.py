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
    
    list_per_page = 30
    actions = ['export_tokens_csv', 'deactivate_tokens']
    
    def user_display(self, obj):
        """Display user phone number"""
        return obj.user.phone_number
    user_display.short_description = 'User'
    
    def export_tokens_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="push_tokens_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Phone', 'Platform', 'Device Name', 'Is Active', 'Last Used', 'Created At'])
        
        for token in queryset.select_related('user'):
            writer.writerow([
                token.user.get_full_name(), token.user.phone_number,
                token.get_platform_display(), token.device_name,
                'Yes' if token.is_active else 'No',
                token.last_used, token.created_at
            ])
        return response
    export_tokens_csv.short_description = '📥 Export to CSV'
    
    def deactivate_tokens(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} push token(s) deactivated.')
    deactivate_tokens.short_description = 'Deactivate selected tokens'
    
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
    list_per_page = 40
    actions = ['export_notifications_csv', 'mark_as_read']
    
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
    
    def export_notifications_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="notifications_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Phone', 'Type', 'Title', 'Body', 
            'Is Read', 'Push', 'SMS', 'Email', 'Created At'
        ])
        
        for notif in queryset.select_related('user'):
            writer.writerow([
                notif.user.get_full_name(), notif.user.phone_number,
                notif.notification_type, notif.title, notif.body,
                'Yes' if notif.is_read else 'No',
                'Yes' if notif.sent_via_push else 'No',
                'Yes' if notif.sent_via_sms else 'No',
                'Yes' if notif.sent_via_email else 'No',
                notif.created_at
            ])
        return response
    export_notifications_csv.short_description = '📥 Export to CSV'
    
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = '✓ Mark as read'
    
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
    list_per_page = 30
    actions = ['export_preferences_csv', 'enable_all_push', 'disable_all_push']
    
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
    
    def export_preferences_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="notification_preferences_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Phone', 'Push Enabled', 'SMS Enabled', 'Email Enabled', 'In-App Enabled'
        ])
        
        for pref in queryset.select_related('user'):
            writer.writerow([
                pref.user.get_full_name(), pref.user.phone_number,
                'Yes' if pref.push_enabled else 'No',
                'Yes' if pref.sms_enabled else 'No',
                'Yes' if pref.email_enabled else 'No',
                'Yes' if pref.inapp_enabled else 'No'
            ])
        return response
    export_preferences_csv.short_description = '📥 Export to CSV'
    
    def enable_all_push(self, request, queryset):
        updated = queryset.update(push_enabled=True)
        self.message_user(request, f'{updated} user(s) push notifications enabled.')
    enable_all_push.short_description = '🔔 Enable push for selected'
    
    def disable_all_push(self, request, queryset):
        updated = queryset.update(push_enabled=False)
        self.message_user(request, f'{updated} user(s) push notifications disabled.')
    disable_all_push.short_description = '🔕 Disable push for selected'


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
    list_per_page = 40
    actions = ['export_sms_logs_csv']
    
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
    
    def export_sms_logs_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sms_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Phone Number', 'Message', 'Status', 'Provider', 
            'Cost', 'Error', 'Created At', 'Delivered At'
        ])
        
        for sms in queryset:
            writer.writerow([
                sms.phone_number, sms.message, sms.get_status_display(),
                sms.provider, f"₦{sms.cost}" if sms.cost else '0',
                sms.error_message or '', sms.created_at,
                sms.delivered_at if sms.delivered_at else 'Not delivered'
            ])
        return response
    export_sms_logs_csv.short_description = '📥 Export to CSV'
    
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
    list_per_page = 40
    actions = ['export_email_logs_csv']
    
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
    
    def export_email_logs_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="email_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Recipient', 'Subject', 'Status', 'Error', 
            'Created At', 'Sent At', 'Delivered At'
        ])
        
        for email in queryset:
            writer.writerow([
                email.recipient_email, email.subject, email.get_status_display(),
                email.error_message or '', email.created_at,
                email.sent_at if email.sent_at else 'Not sent',
                email.delivered_at if email.delivered_at else 'Not delivered'
            ])
        return response
    export_email_logs_csv.short_description = '📥 Export to CSV'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False