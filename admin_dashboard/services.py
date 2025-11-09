
"""
FILE LOCATION: admin_dashboard/services.py

🎛️ ULTIMATE ADMIN CONTROL CENTER
Complete control over ALL 13 apps!
"""
from django.db import transaction
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# ============================================
# USER MANAGEMENT SERVICES
# ============================================

def ban_user(admin, user_id, reason):
    """Ban a user and cancel all active rides"""
    from django.contrib.auth import get_user_model
    from rides.models import Ride
    from .models import AdminActionLog
    
    User = get_user_model()
    
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            
            # Ban user
            user.is_active = False
            user.save()
            
            # Cancel all active rides
            Ride.objects.filter(
                user=user,
                status__in=['pending', 'accepted', 'in_progress']
            ).update(status='cancelled', cancellation_reason='User banned by admin')
            
            # Log action
            AdminActionLog.objects.create(
                admin=admin,
                action_type='user_ban',
                target_type='user',
                target_id=user.id,
                reason=reason
            )
            
            logger.info(f"👮 Admin {admin.phone_number} banned user {user.phone_number}")
            
            return True, f"User {user.phone_number} banned successfully"
            
    except Exception as e:
        logger.error(f"Error banning user: {str(e)}")
        return False, str(e)


# ============================================
# DRIVER MANAGEMENT SERVICES
# ============================================

def approve_driver(admin, driver_id, notes=''):
    """Approve driver application"""
    from drivers.models import Driver
    from .models import AdminActionLog
    
    try:
        with transaction.atomic():
            driver = Driver.objects.get(id=driver_id)
            
            # Approve
            driver.status = 'approved'
            driver.is_active = True
            driver.save()
            
            # Log
            AdminActionLog.objects.create(
                admin=admin,
                action_type='driver_approve',
                target_type='driver',
                target_id=driver.id,
                reason=notes
            )
            
            # Notify driver
            try:
                from notifications.tasks import send_notification_all_channels
                
                send_notification_all_channels.delay(
                    user_id=driver.user.id,
                    notification_type='driver_approved',
                    title='Application Approved! 🎉',
                    body='Your driver application has been approved!',
                    send_push=True,
                    send_sms=True
                )
            except:
                pass
            
            logger.info(f"✅ Driver {driver.id} approved by {admin.phone_number}")
            
            return True, "Driver approved successfully"
            
    except Exception as e:
        logger.error(f"Error approving driver: {str(e)}")
        return False, str(e)


def suspend_driver(admin, driver_id, reason):
    """Suspend driver and cancel active rides"""
    from drivers.models import Driver
    from rides.models import Ride
    from .models import AdminActionLog
    
    try:
        with transaction.atomic():
            driver = Driver.objects.get(id=driver_id)
            
            # Suspend
            driver.status = 'suspended'
            driver.is_active = False
            driver.save()
            
            # Cancel active rides
            Ride.objects.filter(
                driver=driver,
                status__in=['accepted', 'in_progress']
            ).update(status='cancelled', cancellation_reason='Driver suspended')
            
            # Log
            AdminActionLog.objects.create(
                admin=admin,
                action_type='driver_suspend',
                target_type='driver',
                target_id=driver.id,
                reason=reason
            )
            
            logger.warning(f"⚠️ Driver {driver.id} suspended by {admin.phone_number}")
            
            return True, "Driver suspended successfully"
            
    except Exception as e:
        logger.error(f"Error suspending driver: {str(e)}")
        return False, str(e)


# ============================================
# RIDE MANAGEMENT SERVICES
# ============================================

def cancel_ride_admin(admin, ride_id, reason):
    """Admin cancels a ride"""
    from rides.models import Ride
    from .models import AdminActionLog
    
    try:
        with transaction.atomic():
            ride = Ride.objects.get(id=ride_id)
            
            # Cancel
            ride.status = 'cancelled'
            ride.cancellation_reason = f"Admin: {reason}"
            ride.save()
            
            # Issue refund if paid
            if ride.payment_status == 'completed':
                from payments.services import process_refund
                process_refund(ride.user, ride.fare_amount, f"Ride #{ride.id} cancelled by admin")
            
            # Log
            AdminActionLog.objects.create(
                admin=admin,
                action_type='ride_cancel',
                target_type='ride',
                target_id=ride.id,
                reason=reason
            )
            
            logger.info(f"🚫 Ride #{ride.id} cancelled by admin")
            
            return True, "Ride cancelled successfully"
            
    except Exception as e:
        logger.error(f"Error cancelling ride: {str(e)}")
        return False, str(e)


# ============================================
# PAYMENT MANAGEMENT SERVICES
# ============================================

def issue_refund_admin(admin, transaction_id, amount, reason):
    """Admin issues refund"""
    from payments.models import Transaction
    from .models import AdminActionLog
    
    try:
        with transaction.atomic():
            trans = Transaction.objects.get(id=transaction_id)
            
            # Process refund
            from payments.services import process_refund
            success, message = process_refund(trans.user, amount, reason)
            
            if success:
                # Log
                AdminActionLog.objects.create(
                    admin=admin,
                    action_type='refund_issue',
                    target_type='transaction',
                    target_id=trans.id,
                    reason=reason,
                    metadata={'amount': str(amount)}
                )
                
                logger.info(f"💰 Refund of ₦{amount} issued by admin")
                
                return True, "Refund issued successfully"
            
            return False, message
            
    except Exception as e:
        logger.error(f"Error issuing refund: {str(e)}")
        return False, str(e)


# ============================================
# PROMO CODE MANAGEMENT SERVICES
# ============================================

def create_promo_admin(admin, promo_data):
    """Admin creates promo code"""
    from promotions.models import PromoCode
    from .models import AdminActionLog
    
    try:
        promo = PromoCode.objects.create(**promo_data)
        
        # Log
        AdminActionLog.objects.create(
            admin=admin,
            action_type='promo_create',
            target_type='promo',
            target_id=promo.id,
            reason=f"Created promo code: {promo.code}"
        )
        
        logger.info(f"🎁 Promo code {promo.code} created by admin")
        
        return True, promo
        
    except Exception as e:
        logger.error(f"Error creating promo: {str(e)}")
        return False, None


# ============================================
# ANALYTICS & REPORTING SERVICES
# ============================================

def get_platform_overview():
    """Get complete platform overview"""
    from django.contrib.auth import get_user_model
    from rides.models import Ride
    from drivers.models import Driver
    from payments.models import Transaction
    
    User = get_user_model()
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        # Users
        'total_users': User.objects.count(),
        'active_users_today': User.objects.filter(last_login__date=today).count(),
        'new_users_this_week': User.objects.filter(date_joined__gte=week_ago).count(),
        
        # Drivers
        'total_drivers': Driver.objects.count(),
        'active_drivers': Driver.objects.filter(status='approved', is_active=True).count(),
        'pending_applications': Driver.objects.filter(status='pending').count(),
        
        # Rides
        'total_rides': Ride.objects.count(),
        'completed_rides': Ride.objects.filter(status='completed').count(),
        'active_rides': Ride.objects.filter(status__in=['pending', 'accepted', 'in_progress']).count(),
        'today_rides': Ride.objects.filter(created_at__date=today).count(),
        
        # Revenue
        'total_revenue': Ride.objects.filter(status='completed').aggregate(
            total=Sum('fare_amount')
        )['total'] or Decimal('0.00'),
        
        'today_revenue': Ride.objects.filter(
            status='completed',
            completed_at__date=today
        ).aggregate(total=Sum('fare_amount'))['total'] or Decimal('0.00'),
        
        'month_revenue': Ride.objects.filter(
            status='completed',
            completed_at__gte=month_ago
        ).aggregate(total=Sum('fare_amount'))['total'] or Decimal('0.00'),
        
        # Platform earnings (20% commission)
        'platform_earnings': (Ride.objects.filter(status='completed').aggregate(
            total=Sum('fare_amount')
        )['total'] or Decimal('0.00')) * Decimal('0.20'),
    }
    
    return stats


def get_user_analytics(user_id):
    """Get detailed user analytics"""
    from django.contrib.auth import get_user_model
    from rides.models import Ride
    from payments.models import Transaction, Wallet
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        
        rides = Ride.objects.filter(user=user)
        
        analytics = {
            'total_rides': rides.count(),
            'completed_rides': rides.filter(status='completed').count(),
            'cancelled_rides': rides.filter(status='cancelled').count(),
            'total_spent': rides.filter(status='completed').aggregate(
                total=Sum('fare_amount')
            )['total'] or Decimal('0.00'),
            'average_fare': rides.filter(status='completed').aggregate(
                avg=Avg('fare_amount')
            )['avg'] or Decimal('0.00'),
            'wallet_balance': Wallet.objects.filter(user=user).first().balance if Wallet.objects.filter(user=user).exists() else Decimal('0.00'),
            'total_transactions': Transaction.objects.filter(user=user).count(),
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        return {}


# ============================================
# SUPPORT TICKET MANAGEMENT
# ============================================

def resolve_ticket_admin(admin, ticket_id, resolution_notes):
    """Admin resolves support ticket"""
    from support.models import SupportTicket
    from support.services import resolve_ticket
    from .models import AdminActionLog
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        
        # Resolve
        resolve_ticket(ticket, admin)
        
        # Add notes
        from support.models import TicketMessage
        TicketMessage.objects.create(
            ticket=ticket,
            sender=admin,
            message=f"RESOLVED: {resolution_notes}",
            is_staff_reply=True
        )
        
        # Log
        AdminActionLog.objects.create(
            admin=admin,
            action_type='ticket_resolve',
            target_type='ticket',
            target_id=ticket.id,
            reason=resolution_notes
        )
        
        logger.info(f"✅ Ticket #{ticket.id} resolved by admin")
        
        return True, "Ticket resolved successfully"
        
    except Exception as e:
        logger.error(f"Error resolving ticket: {str(e)}")
        return False, str(e)


# ============================================
# SAFETY & INCIDENT MANAGEMENT
# ============================================

def handle_sos_admin(admin, sos_id, action):
    """Admin handles SOS alert"""
    from safety.models import EmergencySOS
    from .models import AdminActionLog
    
    try:
        sos = EmergencySOS.objects.get(id=sos_id)
        
        if action == 'resolve':
            sos.resolve(resolved_by=admin)
        elif action == 'escalate':
            sos.priority = 'critical'
            sos.save()
        
        # Log
        AdminActionLog.objects.create(
            admin=admin,
            action_type='sos_handle',
            target_type='sos',
            target_id=sos.id,
            reason=f"Action: {action}"
        )
        
        logger.info(f"🚨 SOS #{sos.id} handled by admin")
        
        return True, "SOS handled successfully"
        
    except Exception as e:
        logger.error(f"Error handling SOS: {str(e)}")
        return False, str(e)


