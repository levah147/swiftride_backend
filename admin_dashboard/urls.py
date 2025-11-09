
"""
FILE LOCATION: admin_dashboard/urls.py

URL routing for admin dashboard API endpoints.

AVAILABLE ROUTES:
/api/admin/users/         - User management
/api/admin/drivers/       - Driver management
/api/admin/stats/         - Platform statistics
/api/admin/actions/       - Admin action logs
/api/admin/settings/      - Platform settings
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserManagementViewSet,
    DriverManagementViewSet,
    PlatformStatsViewSet,
    AdminActionLogViewSet,
    PlatformSettingsViewSet,
)

app_name = 'admin_dashboard_app'

router = DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='users')
router.register(r'drivers', DriverManagementViewSet, basename='drivers')
router.register(r'stats', PlatformStatsViewSet, basename='stats')
router.register(r'actions', AdminActionLogViewSet, basename='actions')
router.register(r'settings', PlatformSettingsViewSet, basename='settings')

urlpatterns = [
    path('', include(router.urls)),
]

