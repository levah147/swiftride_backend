     
"""
FILE LOCATION: admin_dashboard/admin.py

Django admin interface for admin dashboard models.

WHAT THIS DOES:
- Registers models in Django admin panel
- Admin can view/edit data at /admin/
"""

from django.contrib import admin
from .models import AdminActionLog, PlatformSettings, SystemNotification, UserReport


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    """Display admin actions in admin panel"""
    list_display = ['admin', 'action_type', 'target_type', 'target_id', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['admin__phone_number', 'target_type', 'reason']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        # Don't allow manual creation
        return False


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    """Manage platform settings"""
    list_display = ['key', 'value', 'value_type', 'category', 'is_active', 'updated_at']
    list_filter = ['category', 'value_type', 'is_active']
    search_fields = ['key', 'description']
    readonly_fields = ['updated_at', 'created_at']


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    """Manage system notifications"""
    list_display = ['title', 'notification_type', 'target_audience', 'is_active', 'created_at']
    list_filter = ['notification_type', 'target_audience', 'is_active']
    search_fields = ['title', 'message']


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    """Manage user reports"""
    list_display = ['reporter', 'reported_user', 'report_type', 'status', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['reporter__phone_number', 'reported_user__phone_number']
    readonly_fields = ['created_at']

