

"""
FILE LOCATION: support/signals.py

Signal handlers for support app.
Connects support tickets to rides, drivers, and notifications.

CRITICAL INTEGRATIONS:
- Send notifications when tickets are created/updated
- Auto-assign based on ticket category
- Track response times
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import SupportTicket, TicketMessage
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SupportTicket)
def ticket_created_handler(sender, instance, created, **kwargs):
    """
    Handle ticket creation.
    Send notification to user and notify support team.
    """
    if created:
        logger.info(f"🎫 New support ticket created: {instance.ticket_id}")
        
        # Send notification to user
        try:
            from notifications.tasks import send_notification_all_channels
            
            send_notification_all_channels.delay(
                user_id=instance.user.id,
                notification_type='support_ticket_created',
                title='Ticket Created 🎫',
                body=f'Your support ticket {instance.ticket_id} has been created. We\'ll respond soon.',
                send_push=True,
                send_email=True,
                data={
                    'ticket_id': instance.ticket_id,
                    'ticket_pk': instance.id
                }
            )
            
            logger.info(f"📧 Notification sent to user for ticket {instance.ticket_id}")
            
        except ImportError:
            logger.warning("Notifications app not available")
        except Exception as e:
            logger.error(f"Error sending ticket created notification: {str(e)}")
        
        # Notify support team (staff users)
        try:
            from django.contrib.auth import get_user_model
            from notifications.tasks import send_notification_all_channels
            
            User = get_user_model()
            staff_users = User.objects.filter(is_staff=True, is_active=True)
            
            for staff_user in staff_users:
                send_notification_all_channels.delay(
                    user_id=staff_user.id,
                    notification_type='support_new_ticket',
                    title='New Support Ticket 🎫',
                    body=f'{instance.user.get_full_name() or instance.user.phone_number} created ticket: {instance.subject}',
                    send_push=True,
                    data={
                        'ticket_id': instance.ticket_id,
                        'ticket_pk': instance.id,
                        'category': instance.category.name if instance.category else None
                    }
                )
            
            logger.info(f"📢 Notified {staff_users.count()} staff members about new ticket")
            
        except Exception as e:
            logger.error(f"Error notifying staff: {str(e)}")


@receiver(pre_save, sender=SupportTicket)
def capture_ticket_status_before_save(sender, instance, **kwargs):
    """
    Capture old status before saving.
    Store it on the instance so post_save can access it.
    """
    if instance.pk:  # Only for updates
        try:
            old_ticket = SupportTicket.objects.get(pk=instance.pk)
            instance._old_status = old_ticket.status
            instance._old_assigned_to = old_ticket.assigned_to
        except SupportTicket.DoesNotExist:
            instance._old_status = None
            instance._old_assigned_to = None
    else:
        instance._old_status = None
        instance._old_assigned_to = None


@receiver(post_save, sender=SupportTicket)
def ticket_status_changed_handler(sender, instance, created, **kwargs):
    """
    Handle ticket status changes.
    Send notifications when status changes.
    """
    if created:
        return  # Skip for new tickets (handled by ticket_created_handler)
    
    try:
        from notifications.tasks import send_notification_all_channels
        
        # Get old status from instance (set in pre_save signal)
        old_status = getattr(instance, '_old_status', None)
        old_assigned_to = getattr(instance, '_old_assigned_to', None)
        
        if old_status is None:
            return  # Can't detect changes
        
        # Check if status changed
        if old_status != instance.status:
            
            # Status changed to 'resolved'
            if instance.status == 'resolved':
                send_notification_all_channels.delay(
                    user_id=instance.user.id,
                    notification_type='support_ticket_resolved',
                    title='Ticket Resolved ✅',
                    body=f'Your ticket {instance.ticket_id} has been resolved!',
                    send_push=True,
                    send_email=True,
                    data={
                        'ticket_id': instance.ticket_id,
                        'ticket_pk': instance.id
                    }
                )
                
                logger.info(f"✅ Ticket {instance.ticket_id} marked as resolved")
            
            # Status changed to 'closed'
            elif instance.status == 'closed':
                send_notification_all_channels.delay(
                    user_id=instance.user.id,
                    notification_type='support_ticket_closed',
                    title='Ticket Closed',
                    body=f'Your ticket {instance.ticket_id} has been closed.',
                    send_push=True,
                    data={
                        'ticket_id': instance.ticket_id,
                        'ticket_pk': instance.id
                    }
                )
                
                logger.info(f"🔒 Ticket {instance.ticket_id} closed")
        
        # Check if assignment changed
        if instance.assigned_to and (old_assigned_to != instance.assigned_to):
            # Notify user about assignment
            send_notification_all_channels.delay(
                user_id=instance.user.id,
                notification_type='support_ticket_assigned',
                title='Ticket Assigned 👤',
                body=f'Your ticket has been assigned to our support team.',
                send_push=True,
                data={
                    'ticket_id': instance.ticket_id,
                    'ticket_pk': instance.id
                }
            )
            
            # Notify assigned staff
            send_notification_all_channels.delay(
                user_id=instance.assigned_to.id,
                notification_type='support_ticket_assigned_to_you',
                title='Ticket Assigned to You 🎫',
                body=f'Ticket {instance.ticket_id}: {instance.subject}',
                send_push=True,
                data={
                    'ticket_id': instance.ticket_id,
                    'ticket_pk': instance.id
                }
            )
            
            logger.info(f"👤 Ticket {instance.ticket_id} assigned to {instance.assigned_to.get_full_name()}")
    
    except Exception as e:
        logger.error(f"Error in ticket status change handler: {str(e)}")


@receiver(post_save, sender=TicketMessage)
def message_sent_handler(sender, instance, created, **kwargs):
    """
    Handle new messages in tickets.
    Send notifications to relevant parties.
    """
    if created:
        ticket = instance.ticket
        
        # Don't send notifications for internal notes
        if instance.is_internal:
            logger.info(f"📝 Internal note added to ticket {ticket.ticket_id}")
            return
        
        try:
            from notifications.tasks import send_notification_all_channels
            
            # If message is from staff, notify user
            if instance.is_staff_reply:
                send_notification_all_channels.delay(
                    user_id=ticket.user.id,
                    notification_type='support_new_message',
                    title='New Reply from Support 💬',
                    body=f'You have a new reply on ticket {ticket.ticket_id}',
                    send_push=True,
                    send_email=True,
                    data={
                        'ticket_id': ticket.ticket_id,
                        'ticket_pk': ticket.id,
                        'message_id': instance.id
                    }
                )
                
                logger.info(f"💬 User notified about staff reply on ticket {ticket.ticket_id}")
            
            # If message is from user, notify assigned staff or all staff
            else:
                if ticket.assigned_to:
                    # Notify assigned staff member
                    send_notification_all_channels.delay(
                        user_id=ticket.assigned_to.id,
                        notification_type='support_user_reply',
                        title='User Reply 💬',
                        body=f'New reply on ticket {ticket.ticket_id}',
                        send_push=True,
                        data={
                            'ticket_id': ticket.ticket_id,
                            'ticket_pk': ticket.id,
                            'message_id': instance.id
                        }
                    )
                    
                    logger.info(f"💬 Assigned staff notified about user reply on ticket {ticket.ticket_id}")
                
                else:
                    # Notify all staff
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    staff_users = User.objects.filter(is_staff=True, is_active=True)
                    
                    for staff_user in staff_users:
                        send_notification_all_channels.delay(
                            user_id=staff_user.id,
                            notification_type='support_user_reply',
                            title='User Reply 💬',
                            body=f'New reply on ticket {ticket.ticket_id}',
                            send_push=True,
                            data={
                                'ticket_id': ticket.ticket_id,
                                'ticket_pk': ticket.id,
                                'message_id': instance.id
                            }
                        )
                    
                    logger.info(f"💬 All staff notified about user reply on ticket {ticket.ticket_id}")
        
        except Exception as e:
            logger.error(f"Error sending message notification: {str(e)}")


@receiver(post_save, sender='rides.Ride')
def ride_issue_auto_ticket_handler(sender, instance, **kwargs):
    """
    Auto-create support ticket for cancelled rides if needed.
    (Optional - can be triggered manually instead)
    """
    # This is optional - you might want to let users create tickets manually
    # Uncomment if you want automatic ticket creation for cancelled rides
    
    # if instance.status == 'cancelled' and instance.cancellation_reason:
    #     # Check if ticket already exists
    #     existing_ticket = SupportTicket.objects.filter(
    #         ride=instance,
    #         user=instance.user
    #     ).exists()
    #     
    #     if not existing_ticket:
    #         # Auto-create ticket
    #         from .models import SupportCategory
    #         
    #         try:
    #             category = SupportCategory.objects.filter(
    #                 slug='ride-issue'
    #             ).first()
    #             
    #             if category:
    #                 ticket = SupportTicket.objects.create(
    #                     user=instance.user,
    #                     category=category,
    #                     subject=f'Cancelled Ride - {instance.id}',
    #                     description=f'Ride was cancelled. Reason: {instance.cancellation_reason}',
    #                     ride=instance,
    #                     priority='high'
    #                 )
    #                 
    #                 logger.info(f"🎫 Auto-created ticket {ticket.ticket_id} for cancelled ride {instance.id}")
    #         
    #         except Exception as e:
    #             logger.error(f"Error auto-creating ticket: {str(e)}")
    
    pass
