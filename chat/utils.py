"""
FILE LOCATION: chat/utils.py

Utility functions for chat app.
Helper functions for message formatting, attachments, etc.
"""
import os
import logging
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

logger = logging.getLogger(__name__)


def generate_thumbnail(image_file, size=(150, 150)):
    """
    Generate thumbnail for uploaded image.
    
    Args:
        image_file: Uploaded image file
        size: Thumbnail size (width, height)
    
    Returns:
        InMemoryUploadedFile: Thumbnail file
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Create thumbnail
        img.thumbnail(size, Image.LANCZOS)
        
        # Save to BytesIO
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        
        # Create InMemoryUploadedFile
        thumbnail = InMemoryUploadedFile(
            thumb_io,
            None,
            f'thumb_{image_file.name}',
            'image/jpeg',
            sys.getsizeof(thumb_io),
            None
        )
        
        return thumbnail
        
    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        return None


def validate_file_upload(file, max_size_mb=10, allowed_types=None):
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file
        max_size_mb: Maximum file size in MB
        allowed_types: List of allowed MIME types
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if allowed_types is None:
        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        return False, f"File size exceeds {max_size_mb}MB limit"
    
    # Check file type
    if file.content_type not in allowed_types:
        return False, "File type not supported"
    
    return True, None


def format_message_time(created_at):
    """
    Format message timestamp for display.
    
    Args:
        created_at: Message creation datetime
    
    Returns:
        str: Formatted time string
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    diff = now - created_at
    
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days}d ago"
    else:
        return created_at.strftime("%b %d, %Y")


def get_conversation_preview(conversation):
    """
    Get preview data for a conversation.
    
    Args:
        conversation: Conversation object
    
    Returns:
        dict: Preview data
    """
    last_message = conversation.last_message
    
    preview = {
        'conversation_id': conversation.conversation_id,
        'last_message': None,
        'last_message_time': None,
        'unread_count': 0
    }
    
    if last_message:
        preview['last_message'] = (
            last_message.content[:50] + '...'
            if len(last_message.content) > 50
            else last_message.content
        )
        preview['last_message_time'] = format_message_time(last_message.created_at)
    
    return preview


def sanitize_message_content(content, max_length=1000):
    """
    Sanitize message content.
    
    Args:
        content: Message content
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized content
    """
    if not content:
        return ""
    
    # Strip whitespace
    content = content.strip()
    
    # Limit length
    if len(content) > max_length:
        content = content[:max_length]
    
    # Remove potentially harmful characters
    # (Add more sanitization as needed)
    content = content.replace('\x00', '')
    
    return content


def check_profanity(text):
    """
    Check if text contains profanity.
    
    Args:
        text: Text to check
    
    Returns:
        tuple: (contains_profanity: bool, filtered_text: str)
    """
    # Simple profanity filter (expand as needed)
    profanity_words = [
        # Add your list of profanity words
        # This is just a placeholder
    ]
    
    text_lower = text.lower()
    for word in profanity_words:
        if word in text_lower:
            return True, text.replace(word, '*' * len(word))
    
    return False, text


def create_system_message(conversation, content):
    """
    Create a system message in a conversation.
    
    Args:
        conversation: Conversation object
        content: Message content
    
    Returns:
        Message: Created message object
    """
    from .models import Message
    
    message = Message.objects.create(
        conversation=conversation,
        sender=conversation.rider,  # System messages from rider's account
        message_type='system',
        content=content,
        is_read=True  # System messages are automatically read
    )
    
    return message


def get_attachment_icon(file_type):
    """
    Get icon for file attachment type.
    
    Args:
        file_type: MIME type
    
    Returns:
        str: Icon name/emoji
    """
    icons = {
        'image/jpeg': '🖼️',
        'image/png': '🖼️',
        'image/gif': '🖼️',
        'image/webp': '🖼️',
        'application/pdf': '📄',
        'application/msword': '📝',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝',
        'application/zip': '📦',
        'audio/mpeg': '🎵',
        'audio/wav': '🎵',
        'video/mp4': '🎬',
        'video/mpeg': '🎬',
    }
    
    return icons.get(file_type, '📎')


def compress_image(image_file, max_width=1920, max_height=1080, quality=85):
    """
    Compress and resize image.
    
    Args:
        image_file: Image file
        max_width: Maximum width
        max_height: Maximum height
        quality: JPEG quality (1-100)
    
    Returns:
        InMemoryUploadedFile: Compressed image
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)
        
        # Save compressed
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Create file
        compressed = InMemoryUploadedFile(
            output,
            None,
            image_file.name,
            'image/jpeg',
            sys.getsizeof(output),
            None
        )
        
        return compressed
        
    except Exception as e:
        logger.error(f"Error compressing image: {str(e)}")
        return image_file


def get_message_delivery_status(message):
    """
    Get human-readable delivery status for message.
    
    Args:
        message: Message object
    
    Returns:
        str: Status string
    """
    if message.is_deleted:
        return "Deleted"
    elif message.is_read:
        return "Read"
    elif message.is_delivered:
        return "Delivered"
    else:
        return "Sent"


def should_send_notification(conversation, user):
    """
    Check if notification should be sent for new message.
    
    Args:
        conversation: Conversation object
        user: User to notify
    
    Returns:
        bool: Whether to send notification
    """
    try:
        # Check if user has notification preferences
        prefs = user.notification_preferences
        if not prefs.push_enabled or not prefs.push_ride_updates:
            return False
    except:
        pass
    
    # Check if ride is still active
    if conversation.ride.status not in ['pending', 'accepted', 'arrived', 'started']:
        return False
    
    return True


def extract_mentions(content):
    """
    Extract @mentions from message content.
    
    Args:
        content: Message content
    
    Returns:
        list: List of mentioned usernames
    """
    import re
    
    # Find all @mentions
    mentions = re.findall(r'@(\w+)', content)
    
    return list(set(mentions))  # Remove duplicates


def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
    
    Returns:
        str: Formatted size
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"