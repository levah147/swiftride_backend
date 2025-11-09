from django.contrib import admin
from django.utils.html import format_html
from .models import (
    EmergencySOS,
    TripShare,
    EmergencyContact,
    SafetyCheck,
    SafeZone,
    IncidentReport,
    SafetySettings,
)
from django.utils import timezone


# ================================
# 1️⃣ EMERGENCY SOS ADMIN
# ================================
@admin.register(EmergencySOS)
class EmergencySOSAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'ride', 'status_colored', 'priority_colored',
        'created_at', 'resolved_at', 'admin_notified', 'police_notified'
    )
    list_filter = (
        'status', 'priority', 'admin_notified', 'police_notified', 'created_at'
    )
    search_fields = ('user__phone_number', 'address', 'notes')
    readonly_fields = ('created_at', 'resolved_at', 'response_time')
    ordering = ('-created_at',)
    actions = ['mark_as_resolved', 'mark_as_false_alarm']

    def status_colored(self, obj):
        color_map = {
            'active': 'red',
            'responding': 'orange',
            'resolved': 'green',
            'false_alarm': 'gray',
        }
        color = color_map.get(obj.status, 'black')
        return format_html(f"<b style='color:{color}'>{obj.get_status_display()}</b>")
    status_colored.short_description = 'Status'

    def priority_colored(self, obj):
        color_map = {
            'low': 'gray',
            'medium': 'blue',
            'high': 'orange',
            'critical': 'red',
        }
        color = color_map.get(obj.priority, 'black')
        return format_html(f"<b style='color:{color}'>{obj.get_priority_display()}</b>")
    priority_colored.short_description = 'Priority'

    @admin.action(description="Mark selected SOS alerts as resolved")
    def mark_as_resolved(self, request, queryset):
        for sos in queryset:
            sos.resolve(resolved_by=request.user)
        self.message_user(request, f"{queryset.count()} SOS alerts marked as resolved.")

    @admin.action(description="Mark selected SOS alerts as false alarm")
    def mark_as_false_alarm(self, request, queryset):
        updated = queryset.update(status='false_alarm', resolved_at=timezone.now())
        self.message_user(request, f"{updated} SOS alerts marked as false alarms.")


# ================================
# 2️⃣ TRIP SHARE ADMIN
# ================================
@admin.register(TripShare)
class TripShareAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ride', 'user', 'is_active', 'views_count', 'created_at', 'expires_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__phone_number', 'ride__id', 'share_link')
    readonly_fields = ('created_at', 'last_accessed', 'share_token')
    ordering = ('-created_at',)
    actions = ['deactivate_shares']

    @admin.action(description="Deactivate selected Trip Shares")
    def deactivate_shares(self, request, queryset):
        count = 0
        for share in queryset:
            if share.is_active:
                share.deactivate()
                count += 1
        self.message_user(request, f"{count} trip shares deactivated.")


# ================================
# 3️⃣ EMERGENCY CONTACT ADMIN
# ================================
@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'name', 'phone_number', 'is_primary',
        'is_verified', 'is_active', 'created_at'
    )
    list_filter = ('is_primary', 'is_verified', 'is_active', 'created_at')
    search_fields = ('user__phone_number', 'name', 'phone_number')
    readonly_fields = ('created_at',)
    ordering = ('-is_primary', 'name')


# ================================
# 4️⃣ SAFETY CHECK ADMIN
# ================================
@admin.register(SafetyCheck)
class SafetyCheckAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ride', 'check_time', 'response', 'reminder_sent',
        'sos_triggered', 'contacts_notified'
    )
    list_filter = ('response', 'reminder_sent', 'sos_triggered')
    search_fields = ('ride__id',)
    readonly_fields = ('created_at', 'responded_at')
    ordering = ('-check_time',)


# ================================
# 5️⃣ SAFE ZONE ADMIN
# ================================
@admin.register(SafeZone)
class SafeZoneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'name', 'zone_type', 'latitude', 'longitude',
        'radius', 'notify_on_arrival', 'is_active'
    )
    list_filter = ('zone_type', 'is_active', 'notify_on_arrival')
    search_fields = ('user__phone_number', 'name', 'address')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# ================================
# 6️⃣ INCIDENT REPORT ADMIN
# ================================
@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'incident_type', 'severity', 'status_colored',
        'driver_suspended', 'created_at', 'resolved_at'
    )
    list_filter = ('status', 'severity', 'driver_suspended', 'created_at')
    search_fields = ('user__phone_number', 'description', 'admin_notes')
    readonly_fields = ('created_at', 'resolved_at')
    ordering = ('-created_at',)
    actions = ['mark_resolved', 'dismiss_incident']

    def status_colored(self, obj):
        color_map = {
            'submitted': 'gray',
            'reviewing': 'blue',
            'investigating': 'orange',
            'resolved': 'green',
            'dismissed': 'red',
        }
        color = color_map.get(obj.status, 'black')
        return format_html(f"<b style='color:{color}'>{obj.get_status_display()}</b>")
    status_colored.short_description = 'Status'

    @admin.action(description="Mark selected incidents as resolved")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"{updated} incident reports marked as resolved.")

    @admin.action(description="Dismiss selected incidents")
    def dismiss_incident(self, request, queryset):
        updated = queryset.update(status='dismissed', resolved_at=timezone.now())
        self.message_user(request, f"{updated} incident reports dismissed.")


# ================================
# 7️⃣ SAFETY SETTINGS ADMIN
# ================================
@admin.register(SafetySettings)
class SafetySettingsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'auto_share_trips', 'enable_safety_checks',
        'quick_sos', 'silent_sos', 'notify_contacts_on_ride_end',
        'created_at', 'updated_at'
    )
    list_filter = (
        'auto_share_trips', 'enable_safety_checks', 'quick_sos',
        'silent_sos', 'notify_contacts_on_ride_end'
    )
    search_fields = ('user__phone_number',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
