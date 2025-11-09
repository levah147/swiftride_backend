"""
FILE LOCATION: chat/tasks.py

Celery tasks for chat app.
Background tasks for cleanup and maintenance.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Conversation, Message, MessageAttachment, TypingIndicator
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_conversations():
    """
    Archive conversations for completed rides older than 7 days.
    Run this task daily via Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # Get conversations for completed rides
        conversations = Conversation.objects.filter(
            status='active',
            ride__status='completed',
            ride__completed_at__lt=cutoff_date
        )
        
        archived_count = 0
        for conversation in conversations:
            conversation.archive()
            archived_count += 1
        
        logger.info(f"Archived {archived_count} old conversations")
        
        return {
            'success': True,
            'archived_count': archived_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_conversations: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_deleted_messages():
    """
    Permanently delete messages that were soft-deleted more than 30 days ago.
    Run this task weekly via Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = Message.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Permanently deleted {deleted_count} old messages")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_deleted_messages: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_orphaned_attachments():
    """
    Delete file attachments for deleted messages.
    Run this task weekly via Celery Beat.
    """
    try:
        import os
        
        # Get attachments for deleted messages
        attachments = MessageAttachment.objects.filter(
            message__is_deleted=True,
            message__deleted_at__lt=timezone.now() - timedelta(days=30)
        )
        
        deleted_count = 0
        for attachment in attachments:
            # Delete file from storage
            try:
                if attachment.file:
                    attachment.file.delete(save=False)
                if attachment.thumbnail:
                    attachment.thumbnail.delete(save=False)
            except Exception as e:
                logger.warning(f"Error deleting file for attachment {attachment.id}: {str(e)}")
            
            # Delete attachment record
            attachment.delete()
            deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} orphaned attachments")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_orphaned_attachments: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_typing_indicators():
    """
    Remove stale typing indicators (older than 10 seconds).
    Run this task every minute via Celery Beat.
    """
    try:
        deleted_count = TypingIndicator.cleanup_old_indicators()[0]
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} stale typing indicators")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_typing_indicators: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_chat_statistics():
    """
    Generate daily chat statistics.
    Run this task daily via Celery Beat.
    """
    try:
        from datetime import date
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get statistics for yesterday
        conversations_created = Conversation.objects.filter(
            created_at__date=yesterday
        ).count()
        
        messages_sent = Message.objects.filter(
            created_at__date=yesterday
        ).count()
        
        attachments_uploaded = MessageAttachment.objects.filter(
            uploaded_at__date=yesterday
        ).count()
        
        logger.info(
            f"Daily stats - Conversations: {conversations_created}, "
            f"Messages: {messages_sent}, Attachments: {attachments_uploaded}"
        )
        
        return {
            'success': True,
            'date': str(yesterday),
            'conversations_created': conversations_created,
            'messages_sent': messages_sent,
            'attachments_uploaded': attachments_uploaded
        }
        
    except Exception as e:
        logger.error(f"Error in generate_chat_statistics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_unread_message_notifications():
    """
    Send push notifications for unread messages.
    Run this task every 15 minutes via Celery Beat.
    """
    try:
        from notifications.tasks import send_push_notification_task
        
        # Get conversations with unread messages
        conversations = Conversation.objects.filter(
            status='active',
            messages__is_read=False
        ).distinct()
        
        notification_count = 0
        for conversation in conversations:
            # Get unread messages for rider
            rider_unread = conversation.messages.filter(
                is_read=False,
                sender=conversation.driver
            ).count()
            
            if rider_unread > 0:
                send_push_notification_task.delay(
                    user_ids=[conversation.rider.id],
                    title=f'{rider_unread} New Message(s)',
                    body='You have unread messages from your driver',
                    notification_type='general',
                    data_payload={'conversation_id': conversation.conversation_id}
                )
                notification_count += 1
            
            # Get unread messages for driver
            driver_unread = conversation.messages.filter(
                is_read=False,
                sender=conversation.rider
            ).count()
            
            if driver_unread > 0:
                send_push_notification_task.delay(
                    user_ids=[conversation.driver.id],
                    title=f'{driver_unread} New Message(s)',
                    body='You have unread messages from your rider',
                    notification_type='general',
                    data_payload={'conversation_id': conversation.conversation_id}
                )
                notification_count += 1
        
        logger.info(f"Sent {notification_count} unread message notifications")
        
        return {
            'success': True,
            'notifications_sent': notification_count
        }
        
    except Exception as e:
        logger.error(f"Error in send_unread_message_notifications: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }