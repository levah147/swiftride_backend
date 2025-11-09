


"""

FILE LOCATION: support/utils.py
"""
import logging

logger = logging.getLogger(__name__)

def calculate_response_time(ticket):
    """Calculate time to first response"""
    if ticket.first_response_at:
        delta = ticket.first_response_at - ticket.created_at
        return delta.total_seconds() / 3600  # hours
    return None

def send_ticket_notification(ticket, notification_type):
    """Send notification for ticket updates"""
    from notifications.tasks import send_push_notification_task
    
    messages = {
        'created': ('Ticket Created', f'Your ticket {ticket.ticket_id} has been created'),
        'assigned': ('Ticket Assigned', f'Your ticket has been assigned to a support agent'),
        'resolved': ('Ticket Resolved', f'Your ticket {ticket.ticket_id} has been resolved'),
    }
    
    if notification_type in messages:
        title, body = messages[notification_type]
        send_push_notification_task.delay(
            user_ids=[ticket.user.id],
            title=title,
            body=body,
            notification_type='general'
        )
        