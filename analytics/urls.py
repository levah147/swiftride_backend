
# Create URL
"""
FILE LOCATION: analytics/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DriverEarningsViewSet,
    RideAnalyticsViewSet,
    RevenueReportViewSet,
    DashboardViewSet,
    HeatMapViewSet
)

app_name = 'analytics'

router = DefaultRouter()
router.register(r'earnings', DriverEarningsViewSet, basename='earnings')
router.register(r'rides', RideAnalyticsViewSet, basename='ride-analytics')
router.register(r'revenue', RevenueReportViewSet, basename='revenue')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'heatmap', HeatMapViewSet, basename='heatmap')

urlpatterns = [
    path('', include(router.urls)),
]


