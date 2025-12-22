
"""
FILE LOCATION: analytics/signals.py

Signal handlers for analytics app.
Automatically collect data from all other apps for analytics.

CRITICAL INTEGRATIONS:
- Track ride completion for analytics
- Calculate driver earnings
- Update revenue reports
- Track user activity
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='rides.Ride')
def ride_completed_analytics_handler(sender, instance, **kwargs):
    """
    Track ride completion for analytics.
    Updates daily analytics when ride completes.
    """
    if instance.status == 'completed':
        from .services import update_daily_ride_analytics, update_driver_earnings
        
        try:
            # Update daily ride analytics
            update_daily_ride_analytics(instance.created_at.date())
            
            # Update driver earnings for the day
            if instance.driver:
                update_driver_earnings(instance.driver, instance.created_at.date())
            
            logger.info(f"[ANALYTICS] Analytics updated for completed ride #{instance.id}")
            
        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")


@receiver(post_save, sender='payments.Transaction')
def transaction_revenue_tracking_handler(sender, instance, **kwargs):
    """
    Track revenue from transactions.
    Updates revenue reports when transactions complete.
    """
    if instance.status == 'completed' and instance.transaction_type in ['ride_payment', 'deposit']:
        from .services import update_revenue_data
        
        try:
            update_revenue_data(instance.created_at.date())
            
            logger.info(f"💰 Revenue data updated for transaction #{instance.id}")
            
        except Exception as e:
            logger.error(f"Error tracking revenue: {str(e)}")


@receiver(post_save, sender='drivers.Driver')
def driver_status_analytics_handler(sender, instance, **kwargs):
    """
    Track driver activity changes.
    Update driver analytics when status changes.
    """
    # Track when driver goes online/offline
    if instance.is_online:
        from .services import track_driver_activity
        
        try:
            track_driver_activity(instance, timezone.now())
            
            logger.debug(f"📊 Driver {instance.id} activity tracked")
            
        except Exception as e:
            logger.error(f"Error tracking driver activity: {str(e)}")

