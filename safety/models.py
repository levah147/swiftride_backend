"""
FILE LOCATION: safety/models.py

===========================================
SAFETY FEATURES MODELS - COMPLETE
===========================================

WHAT THIS APP PROVIDES:
✅ Emergency SOS button
✅ Real-time trip sharing
✅ Emergency contacts
✅ Automatic safety checks
✅ Safe ride verification
✅ Incident reporting

These features protect users and provide peace of mind!
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class EmergencySOS(models.Model):
    """
    Emergency SOS Alert System
    
    When user presses SOS button:
    1. Create SOS record
    2. Capture current location
    3. Send SMS to emergency contacts
    4. Alert admin team
    5. Track until resolved
    """
    
    STATUS_CHOICES = [
        ('active', 'Active - Help Needed!'),
        ('responding', 'Help On The Way'),
        ('resolved', 'Resolved - User Safe'),
        ('false_alarm', 'False Alarm'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # Who triggered SOS
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sos_alerts'
    )
    
    # Related ride (if during ride)
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sos_alerts'
    )
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    address = models.CharField(max_length=500, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='high'
    )
    
    # User notes
    notes = models.TextField(
        blank=True,
        help_text="Optional context from user"
    )
    
    # Tracking
    contacts_notified = models.JSONField(
        default=list,
        help_text="Phone numbers that received alert"
    )
    
    admin_notified = models.BooleanField(default=False)
    police_notified = models.BooleanField(default=False)
    
    # Response
    response_time = models.DurationField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_sos_alerts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_emergency_sos'
        ordering = ['-created_at']
        verbose_name = 'Emergency SOS'
        verbose_name_plural = 'Emergency SOS Alerts'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"SOS - {self.user.phone_number} - {self.status}"
    
    def resolve(self, resolved_by=None):
        """Mark SOS as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        if self.created_at:
            self.response_time = self.resolved_at - self.created_at
        self.save()


class TripShare(models.Model):
    """
    Real-time trip sharing with trusted contacts
    
    User shares ride → Contacts get link → Track live location
    """
    
    # Trip details
    ride = models.OneToOneField(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='trip_share'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trip_shares'
    )
    
    # Shared with (phone numbers)
    shared_with = models.JSONField(
        default=list,
        help_text="['+2348011111111', '+2348022222222']"
    )
    
    # Shareable link
    share_link = models.CharField(max_length=200, unique=True)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Security
    access_code = models.CharField(
        max_length=6,
        blank=True,
        help_text="Optional PIN for tracking page"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_trip_share'
        verbose_name = 'Trip Share'
        verbose_name_plural = 'Trip Shares'
    
    def __str__(self):
        return f"Trip Share - Ride #{self.ride_id}"
    
    def deactivate(self):
        """Deactivate when ride ends"""
        self.is_active = False
        self.save()
    
    def increment_views(self):
        """Track link access"""
        self.views_count += 1
        self.last_accessed = timezone.now()
        self.save()


class EmergencyContact(models.Model):
    """
    User's trusted emergency contacts
    
    Get notified when:
    - SOS triggered
    - Ride shared (optional)
    - User doesn't respond to safety check
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    
    # Contact info
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    relationship = models.CharField(max_length=100, blank=True)
    
    # Priority
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary contact called first"
    )
    
    # Notification preferences
    notify_sos = models.BooleanField(default=True)
    notify_trip_share = models.BooleanField(default=True)
    notify_trip_start = models.BooleanField(default=False)
    notify_trip_end = models.BooleanField(default=False)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'safety_emergency_contact'
        ordering = ['-is_primary', 'name']
        unique_together = [['user', 'phone_number']]
        verbose_name = 'Emergency Contact'
        verbose_name_plural = 'Emergency Contacts'
    
    def __str__(self):
        return f"{self.name} - {self.phone_number}"


class SafetyCheck(models.Model):
    """
    Automatic safety check-ins during rides
    
    Long ride (>30 min) → App asks "Are you OK?"
    → No response → Alert emergency contacts
    """
    
    RESPONSE_CHOICES = [
        ('pending', 'Pending Response'),
        ('ok', 'User OK'),
        ('help', 'User Needs Help'),
        ('no_response', 'No Response'),
    ]
    
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='safety_checks'
    )
    
    # Scheduling
    check_time = models.DateTimeField()
    reminder_sent = models.BooleanField(default=False)
    
    # Response
    response = models.CharField(
        max_length=20,
        choices=RESPONSE_CHOICES,
        default='pending'
    )
    
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Actions taken
    sos_triggered = models.BooleanField(default=False)
    contacts_notified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'safety_check'
        ordering = ['check_time']
        verbose_name = 'Safety Check'
        verbose_name_plural = 'Safety Checks'
    
    def __str__(self):
        return f"Safety Check - Ride #{self.ride_id} - {self.response}"


class SafeZone(models.Model):
    """
    User-defined safe locations
    
    Home, office, friend's house
    App notifies contacts when user arrives safely
    """
    
    ZONE_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('friend', 'Friend/Family'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='safe_zones'
    )
    
    # Location
    name = models.CharField(max_length=200)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPE_CHOICES)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    radius = models.IntegerField(
        default=100,
        help_text="Radius in meters"
    )
    address = models.CharField(max_length=500, blank=True)
    
    # Notifications
    notify_on_arrival = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'safety_safe_zone'
        verbose_name = 'Safe Zone'
        verbose_name_plural = 'Safe Zones'
    
    def __str__(self):
        return f"{self.name} - {self.user.phone_number}"


class IncidentReport(models.Model):
    """
    Report safety incidents during rides
    
    Unsafe driving, harassment, route deviation, etc.
    """
    
    INCIDENT_TYPES = [
        ('unsafe_driving', 'Unsafe Driving'),
        ('harassment', 'Harassment'),
        ('route_deviation', 'Route Deviation'),
        ('vehicle_issue', 'Vehicle Issue'),
        ('accident', 'Accident'),
        ('threat', 'Threat/Violence'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing', 'Under Review'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Reporter
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='incident_reports'
    )
    
    # Ride
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        related_name='incident_reports'
    )
    
    # Incident details
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    description = models.TextField()
    severity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Minor, 5=Critical"
    )
    
    # Evidence
    evidence_images = models.JSONField(
        default=list,
        help_text="URLs to uploaded images"
    )
    
    # Location
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )
    
    # Admin handling
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_incidents'
    )
    admin_notes = models.TextField(blank=True)
    
    # Actions taken
    action_taken = models.TextField(blank=True)
    driver_suspended = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_incident_report'
        ordering = ['-created_at']
        verbose_name = 'Incident Report'
        verbose_name_plural = 'Incident Reports'
    
    def __str__(self):
        return f"Incident - {self.incident_type} - {self.created_at.date()}"


class SafetySettings(models.Model):
    """
    User's personal safety preferences
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='safety_settings'
    )
    
    # Auto features
    auto_share_trips = models.BooleanField(
        default=False,
        help_text="Share all rides automatically"
    )
    
    auto_safe_zone_notify = models.BooleanField(
        default=True,
        help_text="Notify when arriving at safe zone"
    )
    
    # Safety checks
    enable_safety_checks = models.BooleanField(default=True)
    safety_check_interval = models.IntegerField(
        default=30,
        help_text="Minutes between checks"
    )
    
    # Emergency
    quick_sos = models.BooleanField(
        default=True,
        help_text="Enable quick SOS button"
    )
    
    silent_sos = models.BooleanField(
        default=False,
        help_text="Trigger SOS without sound/vibration"
    )
    
    # Notifications
    notify_contacts_on_ride_start = models.BooleanField(default=False)
    notify_contacts_on_ride_end = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'safety_settings'
        verbose_name = 'Safety Settings'
        verbose_name_plural = 'Safety Settings'
    
    def __str__(self):
        return f"Safety Settings - {self.user.phone_number}"