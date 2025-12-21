


"""
FILE LOCATION: chat/signals.py

Signal handlers for chat app.
Connects chat to rides, notifications, and other apps.

CRITICAL INTEGRATIONS:
- Auto-create conversation when ride is accepted
- Send notifications when new messages arrive
- Update conversation metadata
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Conversation, Message
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='rides.Ride')
def create_conversation_for_ride(sender, instance, created, **kwargs):
    """
    Auto-create conversation when ride is accepted.
    
    When: Ride.status changes to 'accepted'
    Action: Create Conversation linking rider and driver
    """
    if instance.status == 'accepted' and instance.driver:
        try:
            # Check if conversation already exists
            conversation, created = Conversation.objects.get_or_create(
                ride=instance,
                defaults={
                    'rider': instance.user,  # The rider
                    'driver': instance.driver.user,  # The driver
                    'status': 'active'
                }
            )
            
            if created:
                logger.info(f" Conversation created for Ride #{instance.id}")
                
                # Create welcome system message
                Message.objects.create(
                    conversation=conversation,
                    sender=instance.user,  # From rider
                    message_type='system',
                    content=f'Chat started! You can now message your driver.',
                    is_read=True
                )
                
                # Send notification to driver
                try:
                    from notifications.tasks import send_notification_all_channels
                    send_notification_all_channels.delay(
                        user_id=instance.driver.user.id,
                        notification_type='chat_available',
                        title='Chat Available 💬',
                        body=f'You can now chat with {instance.user.get_full_name() or instance.user.phone_number}',
                        send_push=True,
                        data={'conversation_id': conversation.conversation_id}
                    )
                except ImportError:
                    pass
            
        except Exception as e:
            logger.error(f"Error creating conversation for ride {instance.id}: {str(e)}")


@receiver(post_save, sender=Message)
def message_sent_handler(sender, instance, created, **kwargs):
    """
    Handle new message creation.
    
    Actions:
    - Update conversation last_message
    - Send notification to recipient
    - Mark message as delivered
    """
    if created and instance.message_type != 'system':
        conversation = instance.conversation
        
        # Update conversation's last message
        conversation.update_last_message(instance)
        
        # Get recipient (the other participant)
        recipient = conversation.get_other_participant(instance.sender)
        
        # Send notification to recipient
        try:
            from notifications.tasks import send_notification_all_channels
            
            # Check if recipient wants chat notifications
            send_notification_all_channels.delay(
                user_id=recipient.id,
                notification_type='new_message',
                title='New Message 💬',
                body=f'{instance.sender.get_full_name() or instance.sender.phone_number}: {instance.content[:50]}',
                send_push=True,
                send_sms=False,
                data={
                    'conversation_id': conversation.conversation_id,
                    'message_id': instance.id
                }
            )
            
            logger.info(f" Notification sent for message #{instance.id}")
            
        except ImportError:
            logger.warning("Notifications app not available")
        except Exception as e:
            logger.error(f"Error sending notification for message {instance.id}: {str(e)}")
        
        # Mark as delivered
        instance.mark_as_delivered()


@receiver(post_save, sender='rides.Ride')
def archive_conversation_on_ride_complete(sender, instance, **kwargs):
    """
    Archive conversation when ride is completed or cancelled.
    
    When: Ride.status = 'completed' or 'cancelled'
    Action: Keep conversation active but mark for archival
    """
    if instance.status in ['completed', 'cancelled']:
        try:
            conversation = Conversation.objects.get(ride=instance)
            
            # Don't archive immediately, but create system message
            if instance.status == 'completed':
                Message.objects.create(
                    conversation=conversation,
                    sender=instance.user,
                    message_type='system',
                    content='Ride completed! This chat will be archived in 24 hours.',
                    is_read=True
                )
            elif instance.status == 'cancelled':
                Message.objects.create(
                    conversation=conversation,
                    sender=instance.user,
                    message_type='system',
                    content='Ride was cancelled. This chat will be archived.',
                    is_read=True
                )
            
            logger.info(f" System message added to conversation for Ride #{instance.id}")
            
        except Conversation.DoesNotExist:
            # No conversation exists, that's fine
            pass
        except Exception as e:
            logger.error(f"Error archiving conversation for ride {instance.id}: {str(e)}")


@receiver(pre_save, sender=Message)
def validate_message_before_save(sender, instance, **kwargs):
    """
    Validate message before saving.
    
    Checks:
    - Sender is participant in conversation
    - Content is not empty (for text messages)
    - Conversation is active
    """
    if instance.pk is None:  # Only for new messages
        conversation = instance.conversation
        
        # Check sender is participant
        if instance.sender not in [conversation.rider, conversation.driver]:
            raise ValueError("Sender must be a participant in the conversation")
        
        # Check conversation is active
        if conversation.status != 'active':
            raise ValueError("Cannot send messages to inactive conversation")
        
        # Check content for text messages
        if instance.message_type == 'text' and not instance.content.strip():
            raise ValueError("Text message content cannot be empty")


