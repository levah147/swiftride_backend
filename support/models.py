"""
FILE LOCATION: support/models.py

Support/Help Desk models for SwiftRide.
Ticketing system for user support requests.

Models:
- SupportTicket: User support tickets
- TicketMessage: Messages within tickets
- TicketAttachment: File attachments
- FAQ: Frequently Asked Questions
- SupportCategory: Ticket categories
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from common_utils import generate_reference_code

User = get_user_model()


class SupportCategory(models.Model):
    """Categories for support tickets"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name/emoji")
    
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_category'
        ordering = ['sort_order', 'name']
        verbose_name = 'Support Category'
        verbose_name_plural = 'Support Categories'
    
    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    """Support tickets for user issues"""
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_user', 'Waiting for User'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Ticket identification
    ticket_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique ticket reference"
    )
    
    # User info
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    
    # Ticket details
    category = models.ForeignKey(
        SupportCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets'
    )
    
    subject = models.CharField(max_length=255)
    description = models.TextField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True
    )
    
    # Related objects
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        help_text="Related ride (if applicable)"
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        limit_choices_to={'is_staff': True}
    )
    
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Ratings
    rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="User rating (1-5)"
    )
    feedback = models.TextField(blank=True, help_text="User feedback")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-response
    first_response_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'support_ticket'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['ticket_id']),
        ]
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
    
    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        # Generate ticket ID if not exists
        if not self.ticket_id:
            self.ticket_id = generate_reference_code('TKT')
        super().save(*args, **kwargs)
    
    def mark_resolved(self):
        """Mark ticket as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])
    
    def mark_closed(self):
        """Mark ticket as closed"""
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])
    
    def assign_to(self, staff_user):
        """Assign ticket to staff member"""
        self.assigned_to = staff_user
        self.assigned_at = timezone.now()
        self.status = 'in_progress'
        self.save(update_fields=['assigned_to', 'assigned_at', 'status'])
    
    @property
    def response_time(self):
        """Calculate time to first response"""
        if self.first_response_at:
            return self.first_response_at - self.created_at
        return None
    
    @property
    def resolution_time(self):
        """Calculate time to resolution"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None


class TicketMessage(models.Model):
    """Messages within support tickets"""
    
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_messages'
    )
    
    message = models.TextField()
    
    is_staff_reply = models.BooleanField(
        default=False,
        help_text="Is this from support staff?"
    )
    
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal note (not visible to user)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_ticket_message'
        ordering = ['created_at']
        verbose_name = 'Ticket Message'
        verbose_name_plural = 'Ticket Messages'
    
    def __str__(self):
        return f"Message on {self.ticket.ticket_id}"
    
    def save(self, *args, **kwargs):
        # Check if sender is staff
        if self.sender.is_staff:
            self.is_staff_reply = True
            
            # Update first response time if this is first staff reply
            if not self.ticket.first_response_at:
                self.ticket.first_response_at = timezone.now()
                self.ticket.save(update_fields=['first_response_at'])
        
        super().save(*args, **kwargs)


class TicketAttachment(models.Model):
    """File attachments for support tickets"""
    
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    message = models.ForeignKey(
        TicketMessage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )
    
    file = models.FileField(upload_to='support_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'support_ticket_attachment'
        ordering = ['uploaded_at']
        verbose_name = 'Ticket Attachment'
        verbose_name_plural = 'Ticket Attachments'
    
    def __str__(self):
        return self.file_name
    
    @property
    def file_size_formatted(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class FAQ(models.Model):
    """Frequently Asked Questions"""
    
    category = models.ForeignKey(
        SupportCategory,
        on_delete=models.CASCADE,
        related_name='faqs'
    )
    
    question = models.CharField(max_length=255)
    answer = models.TextField()
    
    is_published = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Analytics
    view_count = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'support_faq'
        ordering = ['category', 'sort_order', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question
    
    def increment_views(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def mark_helpful(self):
        """Mark as helpful"""
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    def mark_not_helpful(self):
        """Mark as not helpful"""
        self.not_helpful_count += 1
        self.save(update_fields=['not_helpful_count'])