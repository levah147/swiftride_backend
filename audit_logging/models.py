"""
FILE LOCATION: audit_logging/models.py

Audit logging models for tracking all critical actions in the system.
Essential for security, compliance, and debugging.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json

User = get_user_model()


class AuditLog(models.Model):
    """
    Comprehensive audit log for tracking all critical actions.
    
    Tracks:
    - User actions (login, logout, profile updates, etc.)
    - Admin actions (suspensions, approvals, refunds, etc.)
    - Payment operations (deposits, withdrawals, transactions)
    - Ride operations (creation, cancellation, completion)
    - Security events (failed logins, suspicious activity)
    """
    
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('suspend', 'Suspend'),
        ('activate', 'Activate'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
        ('cancel', 'Cancel'),
        ('complete', 'Complete'),
        ('rate', 'Rate'),
        ('security', 'Security Event'),
        ('admin', 'Admin Action'),
        ('system', 'System Event'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # User who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action (null for system events)"
    )
    
    # Action details
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        help_text="Type of action performed"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='medium',
        help_text="Severity level of the action"
    )
    
    # Target object (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Type of object affected"
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of object affected"
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action description
    description = models.TextField(
        help_text="Human-readable description of the action"
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="API endpoint or URL path"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method (GET, POST, etc.)"
    )
    
    # Additional data (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the action"
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the action occurred"
    )
    
    # Status
    success = models.BooleanField(
        default=True,
        help_text="Whether the action was successful"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if action failed"
    )
    
    class Meta:
        ordering = ['-timestamp']
        db_table = 'audit_log'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        user_str = self.user.phone_number if self.user else 'System'
        return f"{self.action_type} by {user_str} at {self.timestamp}"
    
    @classmethod
    def log_action(
        cls,
        user=None,
        action_type='system',
        content_object=None,
        description='',
        severity='medium',
        ip_address=None,
        user_agent=None,
        request_path=None,
        request_method=None,
        metadata=None,
        success=True,
        error_message=None
    ):
        """
        Convenience method to create an audit log entry.
        
        Usage:
            AuditLog.log_action(
                user=request.user,
                action_type='create',
                content_object=ride,
                description='Ride created',
                ip_address=get_client_ip(request),
                metadata={'ride_id': ride.id}
            )
        """
        content_type = None
        object_id = None
        
        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            object_id = content_object.pk
        
        return cls.objects.create(
            user=user,
            action_type=action_type,
            content_type=content_type,
            object_id=object_id,
            description=description,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent or '',
            request_path=request_path or '',
            request_method=request_method or '',
            metadata=metadata or {},
            success=success,
            error_message=error_message or ''
        )


class SecurityEvent(models.Model):
    """
    Security-specific events for monitoring threats and suspicious activity.
    
    Tracks:
    - Failed login attempts
    - Suspicious API usage
    - Rate limit violations
    - Unauthorized access attempts
    - Data breach attempts
    """
    
    EVENT_TYPES = [
        ('failed_login', 'Failed Login'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('data_breach_attempt', 'Data Breach Attempt'),
        ('sql_injection_attempt', 'SQL Injection Attempt'),
        ('xss_attempt', 'XSS Attempt'),
        ('csrf_violation', 'CSRF Violation'),
        ('account_locked', 'Account Locked'),
        ('password_reset_abuse', 'Password Reset Abuse'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # User (if applicable)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    
    # Event details
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        db_index=True
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='medium',
        db_index=True
    )
    
    # Request details
    ip_address = models.GenericIPAddressField(
        db_index=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True
    )
    request_path = models.CharField(
        max_length=500,
        blank=True
    )
    request_method = models.CharField(
        max_length=10,
        blank=True
    )
    
    # Event data
    description = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # Status
    resolved = models.BooleanField(
        default=False,
        help_text="Whether the security event has been resolved"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events'
    )
    resolution_notes = models.TextField(
        blank=True
    )
    
    class Meta:
        ordering = ['-timestamp']
        db_table = 'security_event'
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['resolved', 'timestamp']),
        ]
        verbose_name = 'Security Event'
        verbose_name_plural = 'Security Events'
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp} from {self.ip_address}"
    
    def resolve(self, resolved_by=None, notes=''):
        """Mark security event as resolved"""
        self.resolved = True
        self.resolved_at = timezone.now()
        if resolved_by:
            self.resolved_by = resolved_by
        if notes:
            self.resolution_notes = notes
        self.save()

