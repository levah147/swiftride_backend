
"""
FILE LOCATION: analytics/tasks.py

Celery tasks for analytics app.
Scheduled jobs for data aggregation and report generation.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .services import (
    update_daily_ride_analytics,
    update_driver_earnings,
    generate_revenue_report,
    update_popular_locations
)
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics():
    """
    Generate daily analytics for yesterday.
    
    Schedule: Daily at 1:00 AM
    """
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Generate ride analytics
        ride_analytics = update_daily_ride_analytics(yesterday)
        
        # Generate driver earnings for all active drivers
        from drivers.models import Driver
        from rides.models import Ride
        
        # Get drivers who had rides yesterday
        drivers_with_rides = Ride.objects.filter(
            created_at__date=yesterday,
            driver__isnull=False
        ).values_list('driver', flat=True).distinct()
        
        drivers = Driver.objects.filter(id__in=drivers_with_rides)
        
        earnings_count = 0
        for driver in drivers:
            earnings = update_driver_earnings(driver, yesterday)
            if earnings:
                earnings_count += 1
        
        # Update popular locations
        locations_count = update_popular_locations(yesterday)
        
        logger.info(
            f"📊 Generated daily analytics for {yesterday} - "
            f"{earnings_count} driver earnings, {locations_count} locations"
        )
        
        return {
            'success': True,
            'date': str(yesterday),
            'drivers_count': earnings_count,
            'locations_count': locations_count
        }
        
    except Exception as e:
        logger.error(f"Error in generate_daily_analytics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_weekly_revenue_report():
    """
    Generate weekly revenue report.
    
    Schedule: Weekly on Monday
    """
    try:
        today = timezone.now().date()
        start_date = today - timedelta(days=7)
        
        report = generate_revenue_report('weekly', start_date, today)
        
        if report:
            logger.info(
                f"💰 Generated weekly revenue report: "
                f"₦{report.net_revenue} net revenue"
            )
            
            return {
                'success': True,
                'period': f"{start_date} to {today}",
                'net_revenue': float(report.net_revenue)
            }
        
        return {
            'success': False,
            'error': 'Failed to generate report'
        }
        
    except Exception as e:
        logger.error(f"Error in generate_weekly_revenue_report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_monthly_revenue_report():
    """
    Generate monthly revenue report.
    
    Schedule: Monthly on 1st day
    """
    try:
        today = timezone.now().date()
        start_date = today.replace(day=1) - timedelta(days=1)  # Last month
        start_date = start_date.replace(day=1)
        end_date = today.replace(day=1) - timedelta(days=1)
        
        report = generate_revenue_report('monthly', start_date, end_date)
        
        if report:
            logger.info(
                f"💰 Generated monthly revenue report for {start_date.strftime('%B %Y')}: "
                f"₦{report.net_revenue}"
            )
            
            return {
                'success': True,
                'month': start_date.strftime('%B %Y'),
                'net_revenue': float(report.net_revenue)
            }
        
        return {
            'success': False,
            'error': 'Failed to generate report'
        }
        
    except Exception as e:
        logger.error(f"Error in generate_monthly_revenue_report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_analytics_data():
    """
    Clean up old analytics data (older than 1 year).
    
    Schedule: Monthly
    """
    try:
        from .models import (
            DriverEarnings,
            RideAnalytics,
            UserActivity,
            PopularLocation
        )
        
        cutoff_date = timezone.now().date() - timedelta(days=365)
        
        # Delete old records
        earnings_deleted = DriverEarnings.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        analytics_deleted = RideAnalytics.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        activity_deleted = UserActivity.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        locations_deleted = PopularLocation.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        total_deleted = (
            earnings_deleted +
            analytics_deleted +
            activity_deleted +
            locations_deleted
        )
        
        logger.info(f"🗑️ Cleaned up {total_deleted} old analytics records")
        
        return {
            'success': True,
            'deleted_count': total_deleted
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_analytics_data: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_daily_analytics_report():
    """
    Send daily analytics summary to admin users.
    
    Schedule: Daily at 9:00 AM
    """
    try:
        from .services import get_dashboard_stats
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get dashboard stats
        stats = get_dashboard_stats()
        
        # Send to admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        
        for admin in admin_users:
            try:
                from notifications.tasks import send_notification_all_channels
                
                send_notification_all_channels.delay(
                    user_id=admin.id,
                    notification_type='analytics_daily_report',
                    title='Daily Analytics Report 📊',
                    body=f"Yesterday: {stats['today_rides']} rides, ₦{stats['today_revenue']} revenue",
                    send_push=True,
                    send_email=True,
                    data=stats
                )
            except:
                pass
        
        logger.info(f"📧 Sent daily analytics report to {admin_users.count()} admins")
        
        return {
            'success': True,
            'recipients': admin_users.count()
        }
        
    except Exception as e:
        logger.error(f"Error in send_daily_analytics_report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def update_real_time_metrics():
    """
    Update real-time dashboard metrics.
    
    Schedule: Every 5 minutes
    """
    try:
        # Update current day's analytics
        today = timezone.now().date()
        
        update_daily_ride_analytics(today)
        
        logger.debug("📊 Updated real-time metrics")
        
        return {
            'success': True,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in update_real_time_metrics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }