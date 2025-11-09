
"""
FILE LOCATION: support/services.py

Service layer for support business logic.
Ticket management, auto-assignment, statistics, etc.
"""
from django.db.models import Q, Avg, Count, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def create_ticket(user, category, subject, description, ride=None, priority='medium'):
    """
    Create a support ticket.
    
    Args:
        user: User creating ticket
        category: SupportCategory object
        subject: Ticket subject
        description: Ticket description
        ride: Related ride (optional)
        priority: Ticket priority
    
    Returns:
        SupportTicket: Created ticket
    """
    from .models import SupportTicket
    
    try:
        ticket = SupportTicket.objects.create(
            user=user,
            category=category,
            subject=subject.strip(),
            description=description.strip(),
            ride=ride,
            priority=priority
        )
        
        logger.info(f"🎫 Ticket created: {ticket.ticket_id} by {user.phone_number}")
        
        # Auto-assign if rules exist
        auto_assign_ticket(ticket)
        
        return ticket
        
    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        return None


def auto_assign_ticket(ticket):
    """
    Auto-assign ticket to available staff based on category and workload.
    
    Args:
        ticket: SupportTicket object
    
    Returns:
        bool: Whether assignment was successful
    """
    from django.contrib.auth import get_user_model
    
    try:
        User = get_user_model()
        
        # Get active staff members
        staff_users = User.objects.filter(
            is_staff=True,
            is_active=True
        )
        
        if not staff_users.exists():
            logger.warning("No staff members available for auto-assignment")
            return False
        
        # Get staff with least assigned tickets
        staff_workload = []
        for staff in staff_users:
            active_tickets = staff.assigned_tickets.filter(
                status__in=['open', 'in_progress']
            ).count()
            
            staff_workload.append((staff, active_tickets))
        
        # Sort by workload (ascending)
        staff_workload.sort(key=lambda x: x[1])
        
        # Assign to staff with least workload
        least_busy_staff = staff_workload[0][0]
        
        ticket.assign_to(least_busy_staff)
        
        logger.info(f"✅ Ticket {ticket.ticket_id} auto-assigned to {least_busy_staff.get_full_name()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error auto-assigning ticket: {str(e)}")
        return False


def add_message(ticket, sender, message, is_internal=False):
    """
    Add a message to a ticket.
    
    Args:
        ticket: SupportTicket object
        sender: User sending message
        message: Message content
        is_internal: Is internal note
    
    Returns:
        TicketMessage: Created message
    """
    from .models import TicketMessage
    
    try:
        ticket_message = TicketMessage.objects.create(
            ticket=ticket,
            sender=sender,
            message=message.strip(),
            is_internal=is_internal
        )
        
        logger.info(f"💬 Message added to ticket {ticket.ticket_id}")
        
        return ticket_message
        
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        return None


def resolve_ticket(ticket, resolved_by=None):
    """
    Mark ticket as resolved.
    
    Args:
        ticket: SupportTicket object
        resolved_by: User resolving ticket (optional)
    
    Returns:
        bool: Success status
    """
    try:
        ticket.mark_resolved()
        
        logger.info(f"✅ Ticket {ticket.ticket_id} marked as resolved")
        
        return True
        
    except Exception as e:
        logger.error(f"Error resolving ticket: {str(e)}")
        return False


def close_ticket(ticket, closed_by=None):
    """
    Close a ticket.
    
    Args:
        ticket: SupportTicket object
        closed_by: User closing ticket (optional)
    
    Returns:
        bool: Success status
    """
    try:
        ticket.mark_closed()
        
        logger.info(f"🔒 Ticket {ticket.ticket_id} closed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error closing ticket: {str(e)}")
        return False


def get_ticket_statistics(start_date=None, end_date=None):
    """
    Get support ticket statistics.
    
    Args:
        start_date: Start date for stats
        end_date: End date for stats
    
    Returns:
        dict: Statistics
    """
    from .models import SupportTicket
    
    try:
        tickets = SupportTicket.objects.all()
        
        # Filter by date range if provided
        if start_date:
            tickets = tickets.filter(created_at__gte=start_date)
        if end_date:
            tickets = tickets.filter(created_at__lte=end_date)
        
        # Count by status
        stats = {
            'total_tickets': tickets.count(),
            'open_tickets': tickets.filter(status='open').count(),
            'in_progress_tickets': tickets.filter(status='in_progress').count(),
            'waiting_user_tickets': tickets.filter(status='waiting_user').count(),
            'resolved_tickets': tickets.filter(status='resolved').count(),
            'closed_tickets': tickets.filter(status='closed').count(),
        }
        
        # Count by priority
        stats['low_priority'] = tickets.filter(priority='low').count()
        stats['medium_priority'] = tickets.filter(priority='medium').count()
        stats['high_priority'] = tickets.filter(priority='high').count()
        stats['urgent_priority'] = tickets.filter(priority='urgent').count()
        
        # Average response time (in hours)
        response_times = []
        for ticket in tickets.filter(first_response_at__isnull=False):
            if ticket.response_time:
                response_times.append(ticket.response_time.total_seconds() / 3600)
        
        stats['average_response_time_hours'] = (
            sum(response_times) / len(response_times)
            if response_times else 0
        )
        
        # Average resolution time (in hours)
        resolution_times = []
        for ticket in tickets.filter(resolved_at__isnull=False):
            if ticket.resolution_time:
                resolution_times.append(ticket.resolution_time.total_seconds() / 3600)
        
        stats['average_resolution_time_hours'] = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0
        )
        
        # Average rating
        avg_rating = tickets.filter(
            rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg']
        
        stats['average_rating'] = round(float(avg_rating), 2) if avg_rating else 0
        
        # Count tickets with ratings
        stats['rated_tickets'] = tickets.filter(rating__isnull=False).count()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return {}


def get_staff_performance(staff_user):
    """
    Get performance metrics for a staff member.
    
    Args:
        staff_user: Staff user
    
    Returns:
        dict: Performance metrics
    """
    from .models import SupportTicket
    
    try:
        assigned_tickets = SupportTicket.objects.filter(assigned_to=staff_user)
        
        metrics = {
            'total_assigned': assigned_tickets.count(),
            'open': assigned_tickets.filter(status='open').count(),
            'in_progress': assigned_tickets.filter(status='in_progress').count(),
            'resolved': assigned_tickets.filter(status='resolved').count(),
            'closed': assigned_tickets.filter(status='closed').count(),
        }
        
        # Average response time
        response_times = []
        for ticket in assigned_tickets.filter(first_response_at__isnull=False):
            if ticket.response_time:
                response_times.append(ticket.response_time.total_seconds() / 3600)
        
        metrics['average_response_time_hours'] = (
            sum(response_times) / len(response_times)
            if response_times else 0
        )
        
        # Average resolution time
        resolution_times = []
        for ticket in assigned_tickets.filter(resolved_at__isnull=False):
            if ticket.resolution_time:
                resolution_times.append(ticket.resolution_time.total_seconds() / 3600)
        
        metrics['average_resolution_time_hours'] = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0
        )
        
        # Average rating
        avg_rating = assigned_tickets.filter(
            rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg']
        
        metrics['average_rating'] = round(float(avg_rating), 2) if avg_rating else 0
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting staff performance: {str(e)}")
        return {}


def search_faqs(query):
    """
    Search FAQs by question or answer.
    
    Args:
        query: Search query
    
    Returns:
        QuerySet: Matching FAQs
    """
    from .models import FAQ
    
    try:
        faqs = FAQ.objects.filter(
            Q(question__icontains=query) | Q(answer__icontains=query),
            is_published=True
        ).order_by('sort_order', '-view_count')
        
        return faqs
        
    except Exception as e:
        logger.error(f"Error searching FAQs: {str(e)}")
        return FAQ.objects.none()


def get_popular_faqs(limit=10):
    """
    Get most viewed FAQs.
    
    Args:
        limit: Number of FAQs to return
    
    Returns:
        QuerySet: Popular FAQs
    """
    from .models import FAQ
    
    try:
        return FAQ.objects.filter(
            is_published=True
        ).order_by('-view_count')[:limit]
        
    except Exception as e:
        logger.error(f"Error getting popular FAQs: {str(e)}")
        return FAQ.objects.none()


def escalate_ticket(ticket, reason=None):
    """
    Escalate ticket priority.
    
    Args:
        ticket: SupportTicket object
        reason: Escalation reason (optional)
    
    Returns:
        bool: Success status
    """
    from .models import SupportTicket
    
    try:
        # Escalate priority
        if ticket.priority == 'low':
            ticket.priority = 'medium'
        elif ticket.priority == 'medium':
            ticket.priority = 'high'
        elif ticket.priority == 'high':
            ticket.priority = 'urgent'
        
        ticket.save(update_fields=['priority'])
        
        logger.info(f"⬆️ Ticket {ticket.ticket_id} escalated to {ticket.priority}")
        
        # Add internal note if reason provided
        if reason:
            from .models import TicketMessage
            from django.contrib.auth import get_user_model
            
            # Get a staff user to add note
            User = get_user_model()
            staff_user = User.objects.filter(is_staff=True).first()
            
            if staff_user:
                TicketMessage.objects.create(
                    ticket=ticket,
                    sender=staff_user,
                    message=f"Ticket escalated. Reason: {reason}",
                    is_internal=True
                )
        
        return True
        
    except Exception as e:
        logger.error(f"Error escalating ticket: {str(e)}")
        return False


def get_tickets_needing_attention():
    """
    Get tickets that need attention (old open tickets, etc.)
    
    Returns:
        dict: Tickets needing attention
    """
    from .models import SupportTicket
    
    try:
        now = timezone.now()
        
        # Open tickets older than 24 hours
        old_open_tickets = SupportTicket.objects.filter(
            status='open',
            created_at__lt=now - timedelta(hours=24)
        ).order_by('created_at')
        
        # In progress tickets older than 48 hours
        old_in_progress = SupportTicket.objects.filter(
            status='in_progress',
            updated_at__lt=now - timedelta(hours=48)
        ).order_by('updated_at')
        
        # Urgent tickets
        urgent_tickets = SupportTicket.objects.filter(
            priority='urgent',
            status__in=['open', 'in_progress']
        ).order_by('-created_at')
        
        return {
            'old_open_tickets': old_open_tickets,
            'old_in_progress_tickets': old_in_progress,
            'urgent_tickets': urgent_tickets
        }
        
    except Exception as e:
        logger.error(f"Error getting tickets needing attention: {str(e)}")
        return {}
