


"""
FILE LOCATION: chat/services.py

Service layer for chat business logic.
Separates business logic from views and models.
"""
from django.db import transaction
from django.utils import timezone
from .models import Conversation, Message, MessageAttachment
from .utils import generate_thumbnail, compress_image, validate_file_upload
import logging

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversations"""
    
    @staticmethod
    def get_or_create_conversation(ride):
        """
        Get or create conversation for a ride.
        
        Args:
            ride: Ride object
        
        Returns:
            tuple: (Conversation, created)
        """
        return Conversation.get_or_create_for_ride(ride)
    
    @staticmethod
    def get_user_conversations(user, status='active'):
        """
        Get all conversations for a user.
        
        Args:
            user: User object
            status: Conversation status filter
        
        Returns:
            QuerySet: Conversations
        """
        from django.db.models import Q
        
        conversations = Conversation.objects.filter(
            Q(rider=user) | Q(driver=user),
            status=status
        ).select_related(
            'rider',
            'driver',
            'ride',
            'last_message'
        ).order_by('-last_message_at')
        
        return conversations
    
    @staticmethod
    def archive_conversation(conversation):
        """Archive a conversation"""
        conversation.archive()
        logger.info(f"Archived conversation {conversation.conversation_id}")
    
    @staticmethod
    def get_unread_count(user):
        """
        Get total unread message count for user.
        
        Args:
            user: User object
        
        Returns:
            int: Unread count
        """
        from django.db.models import Q
        
        conversations = Conversation.objects.filter(
            Q(rider=user) | Q(driver=user),
            status='active'
        )
        
        unread_count = Message.objects.filter(
            conversation__in=conversations,
            is_read=False
        ).exclude(sender=user).count()
        
        return unread_count


class MessageService:
    """Service for managing messages"""
    
    @staticmethod
    @transaction.atomic
    def send_message(conversation, sender, content, message_type='text', 
                     metadata=None, reply_to=None):
        """
        Send a message in a conversation.
        
        Args:
            conversation: Conversation object
            sender: User sending the message
            content: Message content
            message_type: Type of message
            metadata: Additional metadata
            reply_to: Message being replied to
        
        Returns:
            Message: Created message
        """
        # Validate sender is participant
        if sender not in [conversation.rider, conversation.driver]:
            raise ValueError("Sender must be a participant")
        
        # Validate conversation is active
        if conversation.status != 'active':
            raise ValueError("Conversation is not active")
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            reply_to=reply_to
        )
        
        logger.info(f"Message sent: {message.id} in {conversation.conversation_id}")
        
        return message
    
    @staticmethod
    def mark_messages_read(conversation, user):
        """
        Mark all messages in conversation as read for user.
        
        Args:
            conversation: Conversation object
            user: User reading messages
        
        Returns:
            int: Number of messages marked as read
        """
        updated = Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        if updated > 0:
            logger.info(f"{updated} messages marked as read by {user.phone_number}")
        
        return updated
    
    @staticmethod
    def get_conversation_messages(conversation, limit=50, before_id=None):
        """
        Get messages for a conversation with pagination.
        
        Args:
            conversation: Conversation object
            limit: Number of messages to fetch
            before_id: Get messages before this ID (for pagination)
        
        Returns:
            QuerySet: Messages
        """
        messages = Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).select_related('sender').prefetch_related('attachments')
        
        if before_id:
            messages = messages.filter(id__lt=before_id)
        
        return messages.order_by('-created_at')[:limit]


class AttachmentService:
    """Service for managing message attachments"""
    
    @staticmethod
    @transaction.atomic
    def upload_attachment(message, file):
        """
        Upload file attachment for a message.
        
        Args:
            message: Message object
            file: Uploaded file
        
        Returns:
            MessageAttachment: Created attachment
        """
        # Validate file
        is_valid, error = validate_file_upload(file)
        if not is_valid:
            raise ValueError(error)
        
        # Determine attachment type
        if file.content_type.startswith('image/'):
            attachment_type = 'image'
        elif file.content_type.startswith('audio/'):
            attachment_type = 'audio'
        else:
            attachment_type = 'document'
        
        # Compress image if needed
        if attachment_type == 'image':
            file = compress_image(file)
        
        # Create attachment
        attachment = MessageAttachment.objects.create(
            message=message,
            attachment_type=attachment_type,
            file=file,
            file_name=file.name,
            file_size=file.size,
            file_type=file.content_type
        )
        
        # Generate thumbnail for images
        if attachment_type == 'image':
            thumbnail = generate_thumbnail(file)
            if thumbnail:
                attachment.thumbnail = thumbnail
                attachment.save()
        
        logger.info(f"Attachment uploaded: {attachment.id} for message {message.id}")
        
        return attachment
    
    @staticmethod
    def delete_attachment(attachment):
        """
        Delete an attachment and its files.
        
        Args:
            attachment: MessageAttachment object
        """
        # Delete files from storage
        if attachment.file:
            attachment.file.delete(save=False)
        if attachment.thumbnail:
            attachment.thumbnail.delete(save=False)
        
        # Delete record
        attachment.delete()
        logger.info(f"Attachment deleted: {attachment.id}")


class ChatNotificationService:
    """Service for chat-related notifications"""
    
    @staticmethod
    def send_new_message_notification(message):
        """
        Send notification for new message.
        
        Args:
            message: Message object
        """
        try:
            from notifications.tasks import send_notification_all_channels
            
            conversation = message.conversation
            recipient = conversation.get_other_participant(message.sender)
            
            send_notification_all_channels.delay(
                user_id=recipient.id,
                notification_type='new_message',
                title='New Message 💬',
                body=f'{message.sender.get_full_name() or message.sender.phone_number}: {message.content[:50]}',
                send_push=True,
                send_sms=False,
                data={
                    'conversation_id': conversation.conversation_id,
                    'message_id': message.id
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending message notification: {str(e)}")
    
    @staticmethod
    def send_typing_notification(conversation, user, is_typing=True):
        """
        Send typing indicator notification.
        
        Args:
            conversation: Conversation object
            user: User typing
            is_typing: Whether user is typing
        """
        # This is handled by WebSocket in consumers.py
        pass
