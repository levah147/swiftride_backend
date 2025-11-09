"""
FILE LOCATION: notifications/models.py

Notification system for SwiftRide.
Handles push notifications (FCM), SMS, email, and in-app notifications.

Models:
- PushToken: Store user device FCM tokens
- Notification: In-app notifications
- NotificationPreference: User notification settings
- SMSLog: SMS delivery tracking
- EmailLog: Email delivery tracking
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PushToken(models.Model):
    """
    Store FCM (Firebase Cloud Messaging) tokens for push notifications.
    Each user can have multiple tokens (multiple devices).
    """
    
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_tokens',
        help_text="User who owns this device"
    )
    
    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="FCM device registration token"
    )
    
    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        default='android'
    )
    
    device_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Unique device identifier"
    )
    
    device_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Device model name (e.g., iPhone 13, Samsung Galaxy S21)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this token is still valid"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(
        default=timezone.now,
        help_text="Last time a notification was sent to this token"
    )
    
    class Meta:
        db_table = 'notifications_push_token'
        ordering = ['-last_used']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]
        verbose_name = 'Push Token'
        verbose_name_plural = 'Push Tokens'
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.get_platform_display()} - {self.token[:20]}..."
    
    def deactivate(self):
        """Deactivate this token (e.g., if FCM returns invalid token error)"""
        self.is_active = False
        self.save(update_fields=['is_active'])


class Notification(models.Model):
    """
    In-app notifications for users.
    Stores notification history and read status.
    """
    
    NOTIFICATION_TYPES = [
        # Ride notifications
        ('ride_matched', 'Ride Matched'),
        ('ride_accepted', 'Ride Accepted'),
        ('ride_started', 'Ride Started'),
        ('ride_completed', 'Ride Completed'),
        ('ride_cancelled', 'Ride Cancelled'),
        ('driver_arrived', 'Driver Arrived'),
        ('driver_nearby', 'Driver Nearby'),
        
        # Payment notifications
        ('payment_received', 'Payment Received'),
        ('payment_failed', 'Payment Failed'),
        ('wallet_credited', 'Wallet Credited'),
        ('wallet_debited', 'Wallet Debited'),
        ('withdrawal_approved', 'Withdrawal Approved'),
        ('withdrawal_rejected', 'Withdrawal Rejected'),
        
        # Driver notifications
        ('document_approved', 'Document Approved'),
        ('document_rejected', 'Document Rejected'),
        ('new_ride_request', 'New Ride Request'),
        ('rating_received', 'Rating Received'),
        ('driver_approved', 'Driver Account Approved'),
        
        # System notifications
        ('promo_available', 'Promotion Available'),
        ('referral_bonus', 'Referral Bonus'),
        ('account_verified', 'Account Verified'),
        ('maintenance_alert', 'Maintenance Alert'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        db_index=True
    )
    
    title = models.CharField(max_length=200)
    body = models.TextField()
    
    # Optional data payload (JSON)
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data like ride_id, transaction_id, etc."
    )
    
    # Related models (optional foreign keys)
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    transaction = models.ForeignKey(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Read status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    sent_via_push = models.BooleanField(default=False)
    sent_via_sms = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.title}"
    
    def mark_as_read(self):
        """Mark this notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def mark_all_as_read(cls, user):
        """Mark all unread notifications for a user as read"""
        return cls.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread notifications for a user"""
        return cls.objects.filter(user=user, is_read=False).count()


class NotificationPreference(models.Model):
    """
    User preferences for notifications.
    Controls which channels (push/SMS/email) to use for different notification types.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Push notification preferences
    push_ride_updates = models.BooleanField(
        default=True,
        help_text="Receive push notifications for ride status updates"
    )
    push_payment_updates = models.BooleanField(
        default=True,
        help_text="Receive push notifications for payment updates"
    )
    push_promotional = models.BooleanField(
        default=True,
        help_text="Receive push notifications for promotions and offers"
    )
    push_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for all push notifications"
    )
    
    # SMS notification preferences
    sms_ride_updates = models.BooleanField(
        default=True,
        help_text="Receive SMS for critical ride updates"
    )
    sms_payment_updates = models.BooleanField(
        default=True,
        help_text="Receive SMS for payment confirmations"
    )
    sms_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for all SMS notifications"
    )
    
    # Email notification preferences
    email_ride_updates = models.BooleanField(
        default=True,
        help_text="Receive email receipts for completed rides"
    )
    email_payment_updates = models.BooleanField(
        default=True,
        help_text="Receive email for payment updates"
    )
    email_promotional = models.BooleanField(
        default=True,
        help_text="Receive promotional emails"
    )
    email_weekly_summary = models.BooleanField(
        default=True,
        help_text="Receive weekly activity summary email"
    )
    email_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for all emails"
    )
    
    # In-app notification preference
    inapp_enabled = models.BooleanField(
        default=True,
        help_text="Show in-app notifications"
    )
    
    # Quiet hours (do not disturb)
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="Enable quiet hours (no notifications during specified times)"
    )
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for quiet hours (e.g., 22:00)"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for quiet hours (e.g., 07:00)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications_notification_preference'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.phone_number}"
    
    def should_send_push(self, notification_type):
        """Check if push notification should be sent for given type"""
        if not self.push_enabled:
            return False
        
        if notification_type in ['ride_matched', 'ride_accepted', 'ride_started', 'driver_arrived']:
            return self.push_ride_updates
        elif notification_type in ['payment_received', 'wallet_credited']:
            return self.push_payment_updates
        elif notification_type == 'promo_available':
            return self.push_promotional
        
        return True  # Default: send
    
    def should_send_sms(self, notification_type):
        """Check if SMS should be sent for given type"""
        if not self.sms_enabled:
            return False
        
        if notification_type in ['ride_accepted', 'ride_completed']:
            return self.sms_ride_updates
        elif notification_type in ['payment_received', 'withdrawal_approved']:
            return self.sms_payment_updates
        
        return False  # Default: don't send SMS (costs money)
    
    def should_send_email(self, notification_type):
        """Check if email should be sent for given type"""
        if not self.email_enabled:
            return False
        
        if notification_type == 'ride_completed':
            return self.email_ride_updates
        elif notification_type in ['payment_received', 'withdrawal_approved']:
            return self.email_payment_updates
        elif notification_type == 'promo_available':
            return self.email_promotional
        
        return False


class SMSLog(models.Model):
    """
    Log of all SMS messages sent through the system.
    Tracks delivery status and costs.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sms_logs'
    )
    
    phone_number = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    provider = models.CharField(
        max_length=50,
        help_text="SMS provider used (africastalking, twilio, termii)"
    )
    
    provider_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Message ID from SMS provider"
    )
    
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cost in Naira or credits"
    )
    
    error_message = models.TextField(null=True, blank=True)
    
    # Related notification (optional)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications_sms_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['provider']),
        ]
        verbose_name = 'SMS Log'
        verbose_name_plural = 'SMS Logs'
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status}"


class EmailLog(models.Model):
    """
    Log of all emails sent through the system.
    Tracks delivery status.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_logs'
    )
    
    recipient_email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    
    # HTML version (optional)
    html_body = models.TextField(
        null=True,
        blank=True,
        help_text="HTML version of the email"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    error_message = models.TextField(null=True, blank=True)
    
    # Related notification (optional)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications_email_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.subject}"