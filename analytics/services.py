
"""
FILE LOCATION: analytics/services.py

Service layer for analytics business logic.
Data aggregation, report generation, metrics calculation.
"""
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def update_daily_ride_analytics(target_date):
    """
    Update daily ride analytics for a specific date.
    
    Args:
        target_date: Date to generate analytics for
    
    Returns:
        RideAnalytics: Updated analytics object
    """
    from .models import RideAnalytics
    from rides.models import Ride
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Get all rides for the date
        rides = Ride.objects.filter(created_at__date=target_date)
        
        # Calculate metrics
        total_rides = rides.count()
        completed_rides = rides.filter(status='completed').count()
        cancelled_by_rider = rides.filter(
            status='cancelled',
            cancelled_by__phone_number__isnull=False  # Cancelled by user
        ).count()
        cancelled_by_driver = rides.filter(
            status='cancelled',
            driver__isnull=False
        ).count() - cancelled_by_rider
        
        # Financial metrics
        completed = rides.filter(status='completed')
        total_revenue = completed.aggregate(
            total=Sum('fare_amount')
        )['total'] or Decimal('0.00')
        
        # Platform revenue (assume 20% commission)
        platform_revenue = total_revenue * Decimal('0.20')
        driver_earnings = total_revenue - platform_revenue
        
        # Distance and time
        total_distance = completed.aggregate(
            total=Sum('distance')
        )['total'] or Decimal('0.00')
        
        # User metrics
        active_riders = rides.values('user').distinct().count()
        active_drivers = rides.filter(driver__isnull=False).values('driver').distinct().count()
        
        # New users (registered on this date)
        new_riders = User.objects.filter(
            date_joined__date=target_date,
            driver__isnull=True
        ).count()
        
        # Update or create analytics
        analytics, created = RideAnalytics.objects.update_or_create(
            date=target_date,
            defaults={
                'total_rides': total_rides,
                'completed_rides': completed_rides,
                'cancelled_by_rider': cancelled_by_rider,
                'cancelled_by_driver': cancelled_by_driver,
                'active_riders': active_riders,
                'new_riders': new_riders,
                'active_drivers': active_drivers,
                'total_revenue': total_revenue,
                'platform_revenue': platform_revenue,
                'driver_earnings': driver_earnings,
                'total_distance_km': total_distance,
                'average_ride_distance': total_distance / completed_rides if completed_rides > 0 else 0,
            }
        )
        
        logger.info(f"📊 Updated ride analytics for {target_date}")
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error updating ride analytics: {str(e)}")
        return None


def update_driver_earnings(driver, target_date):
    """
    Update driver earnings for a specific date.
    
    Args:
        driver: Driver object
        target_date: Date to calculate earnings for
    
    Returns:
        DriverEarnings: Updated earnings object
    """
    from .models import DriverEarnings
    from rides.models import Ride
    
    try:
        # Get driver's rides for the date
        rides = Ride.objects.filter(
            driver=driver,
            created_at__date=target_date
        )
        
        completed_rides = rides.filter(status='completed')
        
        # Calculate earnings
        gross_earnings = completed_rides.aggregate(
            total=Sum('fare_amount')
        )['total'] or Decimal('0.00')
        
        # Platform fee (20%)
        platform_fee = gross_earnings * Decimal('0.20')
        net_earnings = gross_earnings - platform_fee
        
        # Distance and time
        total_distance = completed_rides.aggregate(
            total=Sum('distance')
        )['total'] or Decimal('0.00')
        
        # Ratings
        avg_rating = completed_rides.filter(
            mutual_rating__driver_rating__isnull=False
        ).aggregate(
            avg=Avg('mutual_rating__driver_rating')
        )['avg']
        
        # Update or create earnings record
        earnings, created = DriverEarnings.objects.update_or_create(
            driver=driver,
            date=target_date,
            defaults={
                'total_rides': rides.count(),
                'completed_rides': completed_rides.count(),
                'cancelled_rides': rides.filter(status='cancelled').count(),
                'gross_earnings': gross_earnings,
                'platform_fee': platform_fee,
                'net_earnings': net_earnings,
                'total_distance_km': total_distance,
                'average_rating': avg_rating,
            }
        )
        
        logger.info(f"💰 Updated earnings for driver {driver.id} on {target_date}")
        
        return earnings
        
    except Exception as e:
        logger.error(f"Error updating driver earnings: {str(e)}")
        return None


def generate_revenue_report(period_type, start_date, end_date):
    """
    Generate revenue report for a period.
    
    Args:
        period_type: 'daily', 'weekly', 'monthly', 'yearly'
        start_date: Start date
        end_date: End date
    
    Returns:
        RevenueReport: Generated report
    """
    from .models import RevenueReport
    from payments.models import Transaction
    
    try:
        # Get all transactions in period
        transactions = Transaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Calculate metrics
        completed = transactions.filter(status='completed')
        
        gross_revenue = completed.filter(
            transaction_type__in=['ride_payment', 'deposit']
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Platform revenue (commission)
        platform_revenue = gross_revenue * Decimal('0.20')
        
        # Driver payouts
        driver_payouts = completed.filter(
            transaction_type='withdrawal'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Refunds
        refunds = completed.filter(
            transaction_type='refund'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        net_revenue = platform_revenue - refunds
        
        # Transaction counts
        total_transactions = transactions.count()
        successful = completed.count()
        failed = transactions.filter(status='failed').count()
        refund_count = transactions.filter(transaction_type='refund').count()
        
        # Average transaction value
        avg_value = gross_revenue / successful if successful > 0 else Decimal('0.00')
        
        # Create or update report
        report, created = RevenueReport.objects.update_or_create(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'gross_revenue': gross_revenue,
                'platform_revenue': platform_revenue,
                'driver_payouts': driver_payouts,
                'refunds': refunds,
                'net_revenue': net_revenue,
                'total_transactions': total_transactions,
                'successful_transactions': successful,
                'failed_transactions': failed,
                'refund_count': refund_count,
                'average_transaction_value': avg_value,
            }
        )
        
        logger.info(f"📄 Generated {period_type} revenue report for {start_date} to {end_date}")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating revenue report: {str(e)}")
        return None


def get_dashboard_stats():
    """
    Get dashboard overview statistics.
    
    Returns:
        dict: Dashboard statistics
    """
    from .models import RideAnalytics
    from rides.models import Ride
    from django.contrib.auth import get_user_model
    from drivers.models import Driver
    
    User = get_user_model()
    
    try:
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Today's stats
        today_analytics = RideAnalytics.objects.filter(date=today).first()
        
        today_rides = today_analytics.total_rides if today_analytics else 0
        today_revenue = today_analytics.total_revenue if today_analytics else Decimal('0.00')
        today_active_drivers = today_analytics.active_drivers if today_analytics else 0
        today_active_riders = today_analytics.active_riders if today_analytics else 0
        
        # Week stats
        week_analytics = RideAnalytics.objects.filter(
            date__gte=week_ago,
            date__lte=today
        ).aggregate(
            rides=Sum('total_rides'),
            revenue=Sum('total_revenue')
        )
        
        # Month stats
        month_analytics = RideAnalytics.objects.filter(
            date__gte=month_ago,
            date__lte=today
        ).aggregate(
            rides=Sum('total_rides'),
            revenue=Sum('total_revenue')
        )
        
        # Totals
        total_riders = User.objects.filter(driver__isnull=True).count()
        total_drivers = Driver.objects.filter(status='approved').count()
        total_rides = Ride.objects.count()
        
        # Growth rates (compare to previous period)
        prev_week_start = week_ago - timedelta(days=7)
        prev_week_analytics = RideAnalytics.objects.filter(
            date__gte=prev_week_start,
            date__lt=week_ago
        ).aggregate(
            rides=Sum('total_rides'),
            revenue=Sum('total_revenue')
        )
        
        from .utils import calculate_growth_rate
        
        rides_growth = calculate_growth_rate(
            week_analytics['rides'] or 0,
            prev_week_analytics['rides'] or 1
        )
        
        revenue_growth = calculate_growth_rate(
            float(week_analytics['revenue'] or 0),
            float(prev_week_analytics['revenue'] or 1)
        )
        
        stats = {
            'today_rides': today_rides,
            'today_revenue': today_revenue,
            'today_active_drivers': today_active_drivers,
            'today_active_riders': today_active_riders,
            'week_rides': week_analytics['rides'] or 0,
            'week_revenue': week_analytics['revenue'] or Decimal('0.00'),
            'month_rides': month_analytics['rides'] or 0,
            'month_revenue': month_analytics['revenue'] or Decimal('0.00'),
            'total_riders': total_riders,
            'total_drivers': total_drivers,
            'total_rides_all_time': total_rides,
            'rides_growth_rate': rides_growth,
            'revenue_growth_rate': revenue_growth,
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return {}


def get_top_drivers(limit=10, period_days=30):
    """
    Get top performing drivers.
    
    Args:
        limit: Number of drivers to return
        period_days: Period to analyze
    
    Returns:
        list: Top drivers
    """
    from .models import DriverEarnings
    from drivers.models import Driver
    
    try:
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # Aggregate driver earnings
        top_drivers = DriverEarnings.objects.filter(
            date__gte=start_date
        ).values('driver').annotate(
            total_rides=Sum('completed_rides'),
            total_earnings=Sum('net_earnings'),
            avg_rating=Avg('average_rating')
        ).order_by('-total_earnings')[:limit]
        
        # Get driver details
        results = []
        for item in top_drivers:
            driver = Driver.objects.get(id=item['driver'])
            
            # Calculate completion rate
            total = DriverEarnings.objects.filter(
                driver=driver,
                date__gte=start_date
            ).aggregate(
                total=Sum('total_rides'),
                completed=Sum('completed_rides')
            )
            
            completion_rate = (
                (total['completed'] / total['total'] * 100)
                if total['total'] > 0 else 0
            )
            
            results.append({
                'driver_id': driver.id,
                'driver_name': driver.user.get_full_name() or driver.user.phone_number,
                'phone_number': driver.user.phone_number,
                'total_rides': item['total_rides'],
                'total_earnings': item['total_earnings'],
                'average_rating': item['avg_rating'] or Decimal('0.00'),
                'completion_rate': round(completion_rate, 2)
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting top drivers: {str(e)}")
        return []


def update_popular_locations(target_date):
    """
    Update popular locations for heat maps.
    
    Args:
        target_date: Date to analyze
    
    Returns:
        int: Number of locations updated
    """
    from .models import PopularLocation
    from rides.models import Ride
    from collections import defaultdict
    
    try:
        rides = Ride.objects.filter(
            created_at__date=target_date,
            status='completed'
        )
        
        # Aggregate pickup locations
        pickup_data = defaultdict(lambda: {'count': 0, 'coords': None, 'address': ''})
        
        for ride in rides:
            grid_cell = PopularLocation.get_grid_cell(
                ride.pickup_latitude,
                ride.pickup_longitude
            )
            
            pickup_data[grid_cell]['count'] += 1
            pickup_data[grid_cell]['coords'] = (
                float(ride.pickup_latitude),
                float(ride.pickup_longitude)
            )
            pickup_data[grid_cell]['address'] = ride.pickup_location
        
        # Create/update location records
        count = 0
        for grid_cell, data in pickup_data.items():
            lat, lng = data['coords']
            
            PopularLocation.objects.update_or_create(
                location_type='pickup',
                grid_cell=grid_cell,
                date=target_date,
                defaults={
                    'latitude': Decimal(str(lat)),
                    'longitude': Decimal(str(lng)),
                    'address': data['address'][:500],
                    'ride_count': data['count']
                }
            )
            count += 1
        
        # Same for dropoff locations
        # ... (similar code)
        
        logger.info(f"📍 Updated {count} popular locations for {target_date}")
        
        return count
        
    except Exception as e:
        logger.error(f"Error updating popular locations: {str(e)}")
        return 0


def track_driver_activity(driver, timestamp):
    """
    Track driver activity for analytics.
    
    Args:
        driver: Driver object
        timestamp: Activity timestamp
    
    Returns:
        UserActivity: Updated activity record
    """
    from .models import UserActivity
    
    try:
        activity_date = timestamp.date()
        
        activity, created = UserActivity.objects.get_or_create(
            user=driver.user,
            date=activity_date,
            defaults={
                'user_type': 'driver'
            }
        )
        
        # Increment session count if new session
        activity.session_count += 1
        activity.save()
        
        return activity
        
    except Exception as e:
        logger.error(f"Error tracking driver activity: {str(e)}")
        return None


def update_revenue_data(target_date):
    """
    Update revenue data for a specific date.
    
    Args:
        target_date: Date to update
    
    Returns:
        bool: Success status
    """
    try:
        # Generate daily report
        generate_revenue_report('daily', target_date, target_date)
        
        logger.info(f"💰 Updated revenue data for {target_date}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating revenue data: {str(e)}")
        return False


