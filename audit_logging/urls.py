"""
FILE LOCATION: audit_logging/urls.py
URL configuration for audit logging app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, SecurityEventViewSet

router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'security-events', SecurityEventViewSet, basename='security-event')

urlpatterns = [
    path('', include(router.urls)),
]

