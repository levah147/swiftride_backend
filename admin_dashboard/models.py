"""
FILE LOCATION: admin_dashboard/models.py

===========================================
ADMIN DASHBOARD MODELS - EXPLAINED
===========================================

This file contains database models for admin operations.
These models help track what admins do and store platform settings.

WHAT THIS FILE DOES:
- Tracks admin actions (who did what, when)
- Stores platform-wide settings
- Logs important events for audit trail
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AdminActionLog(models.Model):
    """
    WHAT IT DOES:
    - Records every action an admin performs
    - Creates audit trail for accountability
    - Helps track who banned users, approved drivers, etc.
    
    EXAMPLE USE CASE:
    When admin bans a user, we create a log entry:
    AdminActionLog.objects.create(
        admin=request.user,
        action_type='user_ban',
        target_user_id=123,
        reason='Spam account'
    )
    """
    
    # List of possible admin actions
    ACTION_TYPES = [
        ('user_ban', 'Ban User'),
        ('user_unban', 'Unban User'),
        ('driver_approve', 'Approve Driver'),
        ('driver_reject', 'Reject Driver'),
        ('driver_suspend', 'Suspend Driver'),
        ('ride_cancel', 'Cancel Ride'),
        ('refund_issue', 'Issue Refund'),
        ('refund_reject', 'Reject Refund'),
        ('promo_create', 'Create Promo Code'),
        ('promo_disable', 'Disable Promo Code'),
        ('settings_update', 'Update Settings'),
        ('fare_adjust', 'Adjust Fare'),
    ]
    
    # Who performed the action
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
        help_text="Admin who performed this action"
    )
    
    # What action was performed
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        db_index=True,
        help_text="Type of action performed"
    )
    
    # Who/what was affected
    target_type = models.CharField(
        max_length=50,
        help_text="Type of object affected (user, driver, ride, etc.)"
    )
    target_id = models.IntegerField(
        help_text="ID of the affected object"
    )
    
    # Why was this done
    reason = models.TextField(
        blank=True,
        help_text="Reason for this action"
    )
    
    # Additional data (stored as JSON)
    metadata = models.JSONField(
        default=dict,
        help_text="Extra information about this action"
    )
    
    # When did this happen
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        db_table = 'admin_action_log'
        ordering = ['-created_at']  # Newest first
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'
        indexes = [
            models.Index(fields=['admin', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
    
    def __str__(self):
        admin_name = self.admin.phone_number if self.admin else 'Unknown'
        return f"{admin_name} - {self.get_action_type_display()} - {self.created_at.date()}"


class PlatformSettings(models.Model):
    """
    WHAT IT DOES:
    - Stores platform-wide configuration
    - Allows admins to change settings without code changes
    
    EXAMPLE SETTINGS:
    - base_fare: 500
    - price_per_km: 150
    - max_search_radius: 5
    - maintenance_mode: false
    
    EXAMPLE USE:
    # Get a setting
    setting = PlatformSettings.objects.get(key='base_fare')
    fare = float(setting.value)
    
    # Update a setting
    setting.value = '600'
    setting.save()
    """
    
    # Setting name (unique identifier)
    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Setting identifier (e.g., 'base_fare')"
    )
    
    # Setting value (stored as text, convert as needed)
    value = models.TextField(
        help_text="Setting value"
    )
    
    # Data type hint
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('number', 'Number'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string',
        help_text="Type of value for validation"
    )
    
    # What this setting does
    description = models.TextField(
        blank=True,
        help_text="What this setting controls"
    )
    
    # Category for organization
    category = models.CharField(
        max_length=50,
        default='general',
        help_text="Setting category (pricing, features, etc.)"
    )
    
    # Is this setting active
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this setting is currently in use"
    )
    
    # Who last changed it
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin who last updated this setting"
    )
    
    # When it was last changed
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        db_table = 'platform_settings'
        ordering = ['category', 'key']
        verbose_name = 'Platform Setting'
        verbose_name_plural = 'Platform Settings'
    
    def __str__(self):
        return f"{self.key} = {self.value}"
    
    def get_value(self):
        """
        Convert value to proper type
        
        USAGE:
        setting = PlatformSettings.objects.get(key='base_fare')
        fare = setting.get_value()  # Returns as number
        """
        if self.value_type == 'number':
            try:
                return float(self.value)
            except ValueError:
                return 0
        elif self.value_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except:
                return {}
        return self.value


class SystemNotification(models.Model):
    """
    WHAT IT DOES:
    - Allows admins to send announcements to all users
    - Notify users about maintenance, updates, etc.
    
    EXAMPLE:
    SystemNotification.objects.create(
        title='Scheduled Maintenance',
        message='App will be down from 2-3 AM',
        notification_type='maintenance',
        target_audience='all'
    )
    """
    
    NOTIFICATION_TYPES = [
        ('maintenance', 'Maintenance'),
        ('update', 'App Update'),
        ('promotion', 'Promotion'),
        ('announcement', 'General Announcement'),
        ('warning', 'Warning'),
    ]
    
    AUDIENCE_TYPES = [
        ('all', 'All Users'),
        ('riders', 'Riders Only'),
        ('drivers', 'Drivers Only'),
    ]
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Who should see this
    target_audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_TYPES,
        default='all'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Scheduling
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to send (blank = send immediately)"
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"


class UserReport(models.Model):
    """
    WHAT IT DOES:
    - Tracks user reports/complaints
    - Helps admins review and take action
    
    EXAMPLE:
    User reports another user for bad behavior
    Admin reviews and takes appropriate action
    """
    
    REPORT_TYPES = [
        ('harassment', 'Harassment'),
        ('unsafe_driving', 'Unsafe Driving'),
        ('fraud', 'Fraud'),
        ('inappropriate', 'Inappropriate Behavior'),
        ('other', 'Other'),
    ]
    
    STATUS_TYPES = [
        ('pending', 'Pending Review'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Who reported
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    
    # Who is being reported
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_received'
    )
    
    # Report details
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField()
    
    # Related ride (if applicable)
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_TYPES,
        default='pending'
    )
    
    # Admin handling
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reports',
        limit_choices_to={'is_staff': True}
    )
    
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_report'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report: {self.report_type} - {self.reporter.phone_number}"