"""
FILE LOCATION: audit_logging/admin.py
Admin interface for audit logging.
"""
from django.contrib import admin
from django.utils import timezone
from .models import AuditLog, SecurityEvent


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog"""
    
    list_display = [
        'id', 'user', 'action_type', 'severity', 'description',
        'ip_address', 'timestamp', 'success'
    ]
    list_filter = [
        'action_type', 'severity', 'success', 'timestamp',
        'content_type'
    ]
    search_fields = [
        'user__phone_number', 'description', 'ip_address',
        'request_path', 'error_message'
    ]
    readonly_fields = [
        'user', 'action_type', 'severity', 'content_type', 'object_id',
        'description', 'ip_address', 'user_agent', 'request_path',
        'request_method', 'metadata', 'timestamp', 'success', 'error_message'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action_type', 'severity', 'description')
        }),
        ('Target Object', {
            'fields': ('content_type', 'object_id')
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method')
        }),
        ('Additional Data', {
            'fields': ('metadata',)
        }),
        ('Status', {
            'fields': ('success', 'error_message', 'timestamp')
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make audit logs read-only"""
        return False


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Admin interface for SecurityEvent"""
    
    list_display = [
        'id', 'event_type', 'severity', 'user', 'ip_address',
        'timestamp', 'resolved'
    ]
    list_filter = [
        'event_type', 'severity', 'resolved', 'timestamp'
    ]
    search_fields = [
        'user__phone_number', 'ip_address', 'description',
        'request_path'
    ]
    readonly_fields = [
        'user', 'event_type', 'severity', 'ip_address', 'user_agent',
        'request_path', 'request_method', 'description', 'metadata',
        'timestamp', 'resolved', 'resolved_at', 'resolved_by'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Event Details', {
            'fields': ('user', 'event_type', 'severity', 'description')
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method')
        }),
        ('Additional Data', {
            'fields': ('metadata',)
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_at', 'resolved_by', 'resolution_notes')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected security events as resolved"""
        from django.utils import timezone
        updated = queryset.update(
            resolved=True,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{updated} security events marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected events as resolved'
    
    def has_add_permission(self, request):
        """Prevent manual creation of security events"""
        return False
