
"""
FILE LOCATION: support/tasks.py

Celery tasks for support app.
Background jobs for maintenance, notifications, and analytics.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import SupportTicket, FAQ
from .services import get_tickets_needing_attention, escalate_ticket
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_close_resolved_tickets():
    """
    Auto-close tickets resolved more than 7 days ago.
    
    Schedule: Daily
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        
        tickets = SupportTicket.objects.filter(
            status='resolved',
            resolved_at__lt=cutoff_date
        )
        
        count = 0
        for ticket in tickets:
            ticket.mark_closed()
            count += 1
            
            logger.info(f"🔒 Auto-closed ticket {ticket.ticket_id}")
        
        logger.info(f"✅ Auto-closed {count} resolved tickets")
        
        return {
            'success': True,
            'count': count
        }
        
    except Exception as e:
        logger.error(f"Error in auto_close_resolved_tickets: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_overdue_ticket_alerts():
    """
    Send alerts for overdue tickets that need attention.
    
    Schedule: Every 6 hours
    """
    try:
        tickets_needing_attention = get_tickets_needing_attention()
        
        alert_count = 0
        
        # Alert for old open tickets (>24h)
        old_open = tickets_needing_attention.get('old_open_tickets', [])
        for ticket in old_open:
            try:
                from notifications.tasks import send_notification_all_channels
                
                # Notify assigned staff or all staff
                if ticket.assigned_to:
                    send_notification_all_channels.delay(
                        user_id=ticket.assigned_to.id,
                        notification_type='support_overdue_ticket',
                        title='Overdue Ticket ⚠️',
                        body=f'Ticket {ticket.ticket_id} has been open for over 24 hours',
                        send_push=True,
                        data={'ticket_id': ticket.ticket_id}
                    )
                    alert_count += 1
            except:
                pass
        
        # Alert for urgent tickets
        urgent = tickets_needing_attention.get('urgent_tickets', [])
        for ticket in urgent[:5]:  # Limit to 5
            try:
                from notifications.tasks import send_notification_all_channels
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                staff_users = User.objects.filter(is_staff=True, is_active=True)
                
                for staff in staff_users:
                    send_notification_all_channels.delay(
                        user_id=staff.id,
                        notification_type='support_urgent_ticket',
                        title='Urgent Ticket 🚨',
                        body=f'Urgent: {ticket.subject}',
                        send_push=True,
                        data={'ticket_id': ticket.ticket_id}
                    )
                
                alert_count += 1
            except:
                pass
        
        logger.info(f"📢 Sent {alert_count} overdue ticket alerts")
        
        return {
            'success': True,
            'alert_count': alert_count
        }
        
    except Exception as e:
        logger.error(f"Error in send_overdue_ticket_alerts: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def escalate_old_open_tickets():
    """
    Auto-escalate tickets that have been open too long.
    
    Schedule: Daily
    """
    try:
        now = timezone.now()
        
        # Escalate tickets open > 48 hours
        old_tickets = SupportTicket.objects.filter(
            status__in=['open', 'in_progress'],
            created_at__lt=now - timedelta(hours=48),
            priority__in=['low', 'medium']
        )
        
        escalated_count = 0
        for ticket in old_tickets:
            escalate_ticket(ticket, reason="Auto-escalated due to age")
            escalated_count += 1
        
        logger.info(f"⬆️ Auto-escalated {escalated_count} old tickets")
        
        return {
            'success': True,
            'escalated_count': escalated_count
        }
        
    except Exception as e:
        logger.error(f"Error in escalate_old_open_tickets: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_unrated_ticket_reminders():
    """
    Send reminders to users to rate resolved tickets.
    
    Schedule: Daily
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=2)
        
        # Get resolved tickets without ratings older than 2 days
        unrated_tickets = SupportTicket.objects.filter(
            status='resolved',
            resolved_at__lt=cutoff_date,
            rating__isnull=True
        )
        
        reminder_count = 0
        for ticket in unrated_tickets[:20]:  # Limit to 20 per run
            try:
                from notifications.tasks import send_notification_all_channels
                
                send_notification_all_channels.delay(
                    user_id=ticket.user.id,
                    notification_type='support_rate_ticket',
                    title='Rate Your Support Experience ⭐',
                    body=f'How was your experience with ticket {ticket.ticket_id}?',
                    send_push=True,
                    data={'ticket_id': ticket.ticket_id}
                )
                
                reminder_count += 1
            except:
                pass
        
        logger.info(f"📧 Sent {reminder_count} rating reminders")
        
        return {
            'success': True,
            'reminder_count': reminder_count
        }
        
    except Exception as e:
        logger.error(f"Error in send_unrated_ticket_reminders: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_support_statistics():
    """
    Generate daily support statistics.
    
    Schedule: Daily at midnight
    """
    try:
        from .services import get_ticket_statistics
        from datetime import date
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Get yesterday's stats
        start = timezone.datetime.combine(yesterday, timezone.datetime.min.time())
        end = timezone.datetime.combine(yesterday, timezone.datetime.max.time())
        
        stats = get_ticket_statistics(start_date=start, end_date=end)
        
        logger.info(
            f"📊 Daily support stats - "
            f"Total: {stats['total_tickets']}, "
            f"Resolved: {stats['resolved_tickets']}, "
            f"Avg Response: {stats['average_response_time_hours']:.1f}h, "
            f"Avg Rating: {stats['average_rating']:.1f}"
        )
        
        # You can store these stats in a model or send to analytics service
        
        return {
            'success': True,
            'date': str(yesterday),
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error in generate_support_statistics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def update_faq_analytics():
    """
    Update FAQ view counts and helpfulness metrics.
    
    Schedule: Daily
    """
    try:
        from django.db.models import F
        
        # This task can be used for additional FAQ analytics
        # For now, we just log the top FAQs
        
        top_faqs = FAQ.objects.filter(
            is_published=True
        ).order_by('-view_count')[:10]
        
        logger.info(f"📚 Top {top_faqs.count()} FAQs by views")
        
        for faq in top_faqs:
            logger.info(f"  - {faq.question} ({faq.view_count} views)")
        
        return {
            'success': True,
            'top_faqs_count': top_faqs.count()
        }
        
    except Exception as e:
        logger.error(f"Error in update_faq_analytics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }