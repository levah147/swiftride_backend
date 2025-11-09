"""
FILE LOCATION: chat/models.py

Chat models for SwiftRide.
Enables real-time messaging between riders and drivers.

Models:
- Conversation: Chat session between rider and driver
- Message: Individual chat messages
- MessageAttachment: File attachments (images, documents)
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from common_utils import generate_reference_code

User = get_user_model()


class Conversation(models.Model):
    """
    Chat conversation between rider and driver.
    Linked to a specific ride.
    """
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ]
    
    # Participants
    rider = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rider_conversations'
    )
    
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='driver_conversations'
    )
    
    # Related ride
    ride = models.OneToOneField(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='conversation',
        help_text="The ride this conversation is about"
    )
    
    # Conversation info
    conversation_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique conversation identifier"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Last message info (for optimization)
    last_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Archive/Delete tracking
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_conversation'
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['rider', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['ride']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['-last_message_at']),
        ]
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
    
    def __str__(self):
        return f"Conversation {self.conversation_id} - Ride #{self.ride_id}"
    
    def save(self, *args, **kwargs):
        # Generate conversation ID if not exists
        if not self.conversation_id:
            self.conversation_id = generate_reference_code('CHAT')
        super().save(*args, **kwargs)
    
    def update_last_message(self, message):
        """Update last message info"""
        self.last_message = message
        self.last_message_at = message.created_at
        self.save(update_fields=['last_message', 'last_message_at', 'updated_at'])
    
    def archive(self):
        """Archive this conversation"""
        self.status = 'archived'
        self.archived_at = timezone.now()
        self.save(update_fields=['status', 'archived_at'])
    
    def delete_conversation(self):
        """Soft delete conversation"""
        self.status = 'deleted'
        self.deleted_at = timezone.now()
        self.save(update_fields=['status', 'deleted_at'])
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()
    
    def get_other_participant(self, user):
        """Get the other participant in conversation"""
        if user == self.rider:
            return self.driver
        return self.rider
    
    @classmethod
    def get_or_create_for_ride(cls, ride):
        """Get or create conversation for a ride"""
        conversation, created = cls.objects.get_or_create(
            ride=ride,
            defaults={
                'rider': ride.rider,
                'driver': ride.driver.user if ride.driver else None
            }
        )
        return conversation, created


class Message(models.Model):
    """
    Individual chat message in a conversation.
    """
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('location', 'Location'),
        ('system', 'System Message'),
    ]
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    
    # Message content
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text'
    )
    
    content = models.TextField(
        help_text="Message text content"
    )
    
    # Additional data (for location, system messages, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional message data (location coords, etc.)"
    )
    
    # Read status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery status
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Edit/Delete
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Reply to another message (optional)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_message'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['conversation', 'is_read']),
        ]
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
    
    def __str__(self):
        return f"Message from {self.sender.phone_number} - {self.content[:50]}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update conversation's last message
        if is_new:
            self.conversation.update_last_message(self)
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        if not self.is_delivered:
            self.is_delivered = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['is_delivered', 'delivered_at'])
    
    def edit_content(self, new_content):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at'])
    
    def soft_delete(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = "This message was deleted"
        self.save(update_fields=['is_deleted', 'deleted_at', 'content'])
    
    @property
    def is_sender_rider(self):
        """Check if sender is rider"""
        return self.sender == self.conversation.rider
    
    @property
    def is_sender_driver(self):
        """Check if sender is driver"""
        return self.sender == self.conversation.driver


class MessageAttachment(models.Model):
    """
    File attachments for messages (images, documents).
    """
    
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
    ]
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    attachment_type = models.CharField(
        max_length=20,
        choices=ATTACHMENT_TYPE_CHOICES,
        default='image'
    )
    
    file = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        help_text="Uploaded file"
    )
    
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100, help_text="MIME type")
    
    # Image-specific fields
    thumbnail = models.ImageField(
        upload_to='chat_thumbnails/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Thumbnail for images"
    )
    
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_message_attachment'
        ordering = ['uploaded_at']
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
    
    def __str__(self):
        return f"{self.file_name} - {self.get_attachment_type_display()}"
    
    @property
    def file_size_formatted(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self):
        """Check if attachment is an image"""
        return self.attachment_type == 'image'


class TypingIndicator(models.Model):
    """
    Track typing indicators for real-time chat.
    Temporary model - entries auto-expire.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    
    is_typing = models.BooleanField(default=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_typing_indicator'
        unique_together = [['conversation', 'user']]
        verbose_name = 'Typing Indicator'
        verbose_name_plural = 'Typing Indicators'
    
    def __str__(self):
        return f"{self.user.phone_number} typing in {self.conversation.conversation_id}"
    
    @classmethod
    def set_typing(cls, conversation, user, is_typing=True):
        """Set typing status for user in conversation"""
        indicator, created = cls.objects.update_or_create(
            conversation=conversation,
            user=user,
            defaults={'is_typing': is_typing}
        )
        return indicator
    
    @classmethod
    def cleanup_old_indicators(cls):
        """Remove typing indicators older than 10 seconds"""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(seconds=10)
        return cls.objects.filter(updated_at__lt=cutoff).delete()