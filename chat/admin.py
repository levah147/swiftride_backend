"""
FILE LOCATION: chat/admin.py

Django admin interface for chat app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Conversation, Message, MessageAttachment, TypingIndicator


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin interface for conversations"""
    
    list_display = [
        'id',
        'conversation_id',
        'rider_display',
        'driver_display',
        'ride_link',
        'status',
        'message_count',
        'last_message_at',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'last_message_at'
    ]
    
    search_fields = [
        'conversation_id',
        'rider__phone_number',
        'driver__phone_number',
        'ride__id'
    ]
    
    readonly_fields = [
        'conversation_id',
        'rider',
        'driver',
        'ride',
        'last_message',
        'last_message_at',
        'created_at',
        'updated_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def rider_display(self, obj):
        """Display rider info"""
        return obj.rider.phone_number
    rider_display.short_description = 'Rider'
    
    def driver_display(self, obj):
        """Display driver info"""
        return obj.driver.phone_number
    driver_display.short_description = 'Driver'
    
    def ride_link(self, obj):
        """Link to ride"""
        if obj.ride:
            return format_html(
                '<a href="/admin/rides/ride/{}/change/">Ride #{}</a>',
                obj.ride.id,
                obj.ride.id
            )
        return '-'
    ride_link.short_description = 'Ride'
    
    def message_count(self, obj):
        """Count of messages in conversation"""
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for messages"""
    
    list_display = [
        'id',
        'conversation_link',
        'sender_display',
        'message_preview',
        'message_type',
        'status_display',
        'has_attachments',
        'created_at'
    ]
    
    list_filter = [
        'message_type',
        'is_read',
        'is_delivered',
        'is_deleted',
        'created_at'
    ]
    
    search_fields = [
        'content',
        'sender__phone_number',
        'conversation__conversation_id'
    ]
    
    readonly_fields = [
        'conversation',
        'sender',
        'content',
        'message_type',
        'metadata',
        'reply_to',
        'is_read',
        'read_at',
        'is_delivered',
        'delivered_at',
        'is_edited',
        'edited_at',
        'is_deleted',
        'deleted_at',
        'created_at',
        'updated_at'
    ]
    
    date_hierarchy = 'created_at'
    
    def conversation_link(self, obj):
        """Link to conversation"""
        return format_html(
            '<a href="/admin/chat/conversation/{}/change/">{}</a>',
            obj.conversation.id,
            obj.conversation.conversation_id
        )
    conversation_link.short_description = 'Conversation'
    
    def sender_display(self, obj):
        """Display sender info"""
        return obj.sender.phone_number
    sender_display.short_description = 'Sender'
    
    def message_preview(self, obj):
        """Preview of message content"""
        if obj.is_deleted:
            return format_html('<em style="color: gray;">Deleted</em>')
        content = obj.content[:50]
        if len(obj.content) > 50:
            content += '...'
        return content
    message_preview.short_description = 'Content'
    
    def status_display(self, obj):
        """Display message status"""
        statuses = []
        if obj.is_read:
            statuses.append('✓ Read')
        elif obj.is_delivered:
            statuses.append('✓ Delivered')
        else:
            statuses.append('⊙ Sent')
        
        if obj.is_edited:
            statuses.append('✎ Edited')
        if obj.is_deleted:
            statuses.append('✗ Deleted')
        
        return ' | '.join(statuses)
    status_display.short_description = 'Status'
    
    def has_attachments(self, obj):
        """Check if message has attachments"""
        count = obj.attachments.count()
        if count > 0:
            return format_html(
                '<span style="color: green;">✓ ({})</span>',
                count
            )
        return '-'
    has_attachments.short_description = 'Attachments'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for message attachments"""
    
    list_display = [
        'id',
        'message_link',
        'attachment_type',
        'file_name',
        'file_size_display',
        'preview',
        'uploaded_at'
    ]
    
    list_filter = [
        'attachment_type',
        'uploaded_at'
    ]
    
    search_fields = [
        'file_name',
        'message__content'
    ]
    
    readonly_fields = [
        'message',
        'attachment_type',
        'file',
        'file_name',
        'file_size',
        'file_type',
        'thumbnail',
        'width',
        'height',
        'uploaded_at'
    ]
    
    def message_link(self, obj):
        """Link to message"""
        return format_html(
            '<a href="/admin/chat/message/{}/change/">Message #{}</a>',
            obj.message.id,
            obj.message.id
        )
    message_link.short_description = 'Message'
    
    def file_size_display(self, obj):
        """Human-readable file size"""
        return obj.file_size_formatted
    file_size_display.short_description = 'Size'
    
    def preview(self, obj):
        """Show preview for images"""
        if obj.is_image and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.file.url
            )
        return '-'
    preview.short_description = 'Preview'
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    """Admin interface for typing indicators"""
    
    list_display = [
        'id',
        'conversation',
        'user',
        'is_typing',
        'updated_at'
    ]
    
    list_filter = [
        'is_typing',
        'updated_at'
    ]
    
    readonly_fields = [
        'conversation',
        'user',
        'is_typing',
        'started_at',
        'updated_at'
    ]
    
    def has_add_permission(self, request):
        """Disable manual addition"""
        return False