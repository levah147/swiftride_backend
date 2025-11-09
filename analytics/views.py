"""
FILE LOCATION: analytics/views.py

API views for analytics and reporting.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import (
    DriverEarnings,
    RideAnalytics,
    RevenueReport,
    UserActivity,
    PopularLocation
)
from .serializers import (
    DriverEarningsSerializer,
    DriverEarningsSummarySerializer,
    RideAnalyticsSerializer,
    RevenueReportSerializer,
    UserActivitySerializer,
    PopularLocationSerializer,
    DashboardStatsSerializer,
    PeakHoursSerializer,
    TopDriverSerializer,
    RevenueBreakdownSerializer,
    RidesTrendSerializer,
    PerformanceMetricsSerializer,
    HeatMapDataSerializer
)
from .utils import (
    calculate_growth_rate,
    get_demand_level,
    calculate_performance_metrics
)


class DriverEarningsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for driver earnings analytics.
    
    Endpoints:
    - GET /api/analytics/earnings/ - List earnings (drivers see own, staff see all)
    - GET /api/analytics/earnings/{id}/ - Get earning detail
    - GET /api/analytics/earnings/summary/ - Get earnings summary
    - GET /api/analytics/earnings/my-earnings/ - Driver's own earnings
    """
    
    serializer_class = DriverEarningsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return earnings based on user role"""
        user = self.request.user
        
        if user.is_staff:
            # Staff can see all earnings
            queryset = DriverEarnings.objects.all()
        else:
            # Drivers see only their own
            try:
                driver = user.driver
                queryset = DriverEarnings.objects.filter(driver=driver)
            except:
                queryset = DriverEarnings.objects.none()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.select_related('driver__user')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get earnings summary for a period.
        GET /api/analytics/earnings/summary/?start_date=2025-01-01&end_date=2025-01-31
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        summary = queryset.aggregate(
            total_rides=Sum('total_rides'),
            completed_rides=Sum('completed_rides'),
            total_earnings=Sum('net_earnings'),
            total_tips=Sum('tips_received'),
            total_bonuses=Sum('bonuses'),
            total_distance=Sum('total_distance_km'),
            total_hours=Sum('online_hours'),
            average_rating=Avg('average_rating')
        )
        
        # Calculate average daily earnings
        days_count = queryset.values('date').distinct().count()
        if days_count > 0:
            summary['average_daily_earnings'] = summary['total_earnings'] / days_count
        else:
            summary['average_daily_earnings'] = Decimal('0.00')
        
        serializer = DriverEarningsSummarySerializer(summary)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def my_earnings(self, request):
        """
        Get current driver's earnings.
        GET /api/analytics/earnings/my-earnings/?period=week
        """
        try:
            driver = request.user.driver
        except:
            return Response({
                'success': False,
                'error': 'Driver profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        period = request.query_params.get('period', 'week')  # day, week, month, year
        
        today = timezone.now().date()
        
        if period == 'day':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=7)
        
        earnings = DriverEarnings.objects.filter(
            driver=driver,
            date__gte=start_date,
            date__lte=today
        )
        
        serializer = self.get_serializer(earnings, many=True)
        
        return Response({
            'success': True,
            'period': period,
            'data': serializer.data
        })


class RideAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ride analytics (Admin only).
    
    Endpoints:
    - GET /api/analytics/rides/ - List ride analytics
    - GET /api/analytics/rides/{id}/ - Get specific day's analytics
    - GET /api/analytics/rides/trends/ - Get ride trends
    - GET /api/analytics/rides/peak-hours/ - Get peak hours analysis
    """
    
    serializer_class = RideAnalyticsSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Return ride analytics"""
        queryset = RideAnalytics.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Get ride trends over time.
        GET /api/analytics/rides/trends/?days=30
        """
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        analytics = RideAnalytics.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        trends = []
        for record in analytics:
            trends.append({
                'date': record.date,
                'rides_count': record.completed_rides,
                'revenue': record.total_revenue,
                'average_fare': (
                    record.total_revenue / record.completed_rides
                    if record.completed_rides > 0 else Decimal('0.00')
                )
            })
        
        serializer = RidesTrendSerializer(trends, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def peak_hours(self, request):
        """
        Analyze peak hours for rides.
        GET /api/analytics/rides/peak-hours/?date=2025-01-01
        """
        date_str = request.query_params.get('date', timezone.now().date())
        
        try:
            analytics = RideAnalytics.objects.get(date=date_str)
        except RideAnalytics.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No data for this date'
            }, status=status.HTTP_404_NOT_FOUND)
        
        hourly_data = analytics.hourly_rides
        peak_hours = []
        
        for hour, count in hourly_data.items():
            demand = get_demand_level(count)
            peak_hours.append({
                'hour': int(hour),
                'ride_count': count,
                'average_fare': Decimal('0.00'),  # Calculate if needed
                'demand_level': demand
            })
        
        peak_hours.sort(key=lambda x: x['ride_count'], reverse=True)
        serializer = PeakHoursSerializer(peak_hours[:24], many=True)
        
        return Response({
            'success': True,
            'date': date_str,
            'data': serializer.data
        })


class RevenueReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for revenue reports (Admin only).
    
    Endpoints:
    - GET /api/analytics/revenue/ - List revenue reports
    - GET /api/analytics/revenue/{id}/ - Get specific report
    - GET /api/analytics/revenue/breakdown/ - Get revenue breakdown
    - POST /api/analytics/revenue/generate/ - Generate new report
    """
    
    serializer_class = RevenueReportSerializer
    permission_classes = [IsAdminUser]
    queryset = RevenueReport.objects.all()
    
    @action(detail=False, methods=['get'])
    def breakdown(self, request):
        """
        Get revenue breakdown by payment method, category, etc.
        GET /api/analytics/revenue/breakdown/?period=month
        """
        period = request.query_params.get('period', 'month')
        
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)
        
        # Get revenue data
        from rides.models import Ride
        rides = Ride.objects.filter(
            status='completed',
            completed_at__date__gte=start_date
        )
        
        total_revenue = rides.aggregate(Sum('final_fare'))['final_fare__sum'] or 0
        
        breakdown = [
            {
                'category': 'Completed Rides',
                'amount': total_revenue,
                'percentage': 100,
                'count': rides.count()
            }
        ]
        
        serializer = RevenueBreakdownSerializer(breakdown, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for dashboard overview (Admin only).
    
    Endpoints:
    - GET /api/analytics/dashboard/overview/ - Get dashboard overview
    - GET /api/analytics/dashboard/performance/ - Get performance metrics
    - GET /api/analytics/dashboard/top-drivers/ - Get top drivers
    """
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Get dashboard overview statistics.
        GET /api/analytics/dashboard/overview/
        """
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        from rides.models import Ride
        from django.contrib.auth import get_user_model
        from drivers.models import Driver
        
        User = get_user_model()
        
        # Today's stats
        today_analytics = RideAnalytics.objects.filter(date=today).first()
        
        stats = {
            'today_rides': today_analytics.total_rides if today_analytics else 0,
            'today_revenue': today_analytics.total_revenue if today_analytics else Decimal('0.00'),
            'today_active_drivers': today_analytics.active_drivers if today_analytics else 0,
            'today_active_riders': today_analytics.active_riders if today_analytics else 0,
            
            # Week stats
            'week_rides': Ride.objects.filter(created_at__date__gte=week_ago).count(),
            'week_revenue': Ride.objects.filter(
                status='completed',
                completed_at__date__gte=week_ago
            ).aggregate(Sum('final_fare'))['final_fare__sum'] or Decimal('0.00'),
            
            # Month stats
            'month_rides': Ride.objects.filter(created_at__date__gte=month_ago).count(),
            'month_revenue': Ride.objects.filter(
                status='completed',
                completed_at__date__gte=month_ago
            ).aggregate(Sum('final_fare'))['final_fare__sum'] or Decimal('0.00'),
            
            # Totals
            'total_riders': User.objects.filter(is_driver=False).count(),
            'total_drivers': Driver.objects.count(),
            'total_rides_all_time': Ride.objects.count(),
            
            # Growth rates
            'rides_growth_rate': Decimal('0.00'),
            'revenue_growth_rate': Decimal('0.00'),
        }
        
        serializer = DashboardStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def top_drivers(self, request):
        """
        Get top performing drivers.
        GET /api/analytics/dashboard/top-drivers/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        period_days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # Aggregate driver earnings
        top_drivers = DriverEarnings.objects.filter(
            date__gte=start_date
        ).values('driver__user__id', 'driver__user__first_name', 'driver__user__last_name', 'driver__user__phone_number').annotate(
            total_rides=Sum('completed_rides'),
            total_earnings=Sum('net_earnings'),
            average_rating=Avg('average_rating')
        ).order_by('-total_earnings')[:limit]
        
        result = []
        for driver in top_drivers:
            result.append({
                'driver_id': driver['driver__user__id'],
                'driver_name': f"{driver['driver__user__first_name']} {driver['driver__user__last_name']}".strip() or driver['driver__user__phone_number'],
                'phone_number': driver['driver__user__phone_number'],
                'total_rides': driver['total_rides'],
                'total_earnings': driver['total_earnings'],
                'average_rating': driver['average_rating'] or Decimal('0.00'),
                'completion_rate': Decimal('95.00')  # Calculate if needed
            })
        
        serializer = TopDriverSerializer(result, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class HeatMapViewSet(viewsets.ViewSet):
    """
    ViewSet for heat map data.
    
    Endpoints:
    - GET /api/analytics/heatmap/pickups/ - Get pickup heat map data
    - GET /api/analytics/heatmap/dropoffs/ - Get dropoff heat map data
    """
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def pickups(self, request):
        """Get pickup locations heat map data"""
        return self._get_heatmap_data('pickup')
    
    @action(detail=False, methods=['get'])
    def dropoffs(self, request):
        """Get dropoff locations heat map data"""
        return self._get_heatmap_data('dropoff')
    
    def _get_heatmap_data(self, location_type):
        """Helper to get heat map data"""
        days = int(self.request.query_params.get('days', 7))
        limit = int(self.request.query_params.get('limit', 100))
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        locations = PopularLocation.objects.filter(
            location_type=location_type,
            date__gte=start_date
        ).values('latitude', 'longitude', 'area').annotate(
            intensity=Sum('ride_count')
        ).order_by('-intensity')[:limit]
        
        serializer = HeatMapDataSerializer(locations, many=True)
        
        return Response({
            'success': True,
            'location_type': location_type,
            'data': serializer.data
        })