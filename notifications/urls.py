"""
FILE LOCATION: notifications/urls.py

URL routing for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PushTokenViewSet,
    NotificationViewSet,
    NotificationPreferenceViewSet,
    SendNotificationViewSet,
    LogViewSet
)

app_name = 'notifications'

router = DefaultRouter()
router.register(r'tokens', PushTokenViewSet, basename='token')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    # Push token management
    # POST /api/notifications/tokens/ - Register device
    # GET /api/notifications/tokens/ - List devices
    # DELETE /api/notifications/tokens/{id}/ - Remove device
    
    # Notifications
    # GET /api/notifications/ - List notifications
    # GET /api/notifications/{id}/ - Get notification
    # POST /api/notifications/mark-read/ - Mark as read
    # GET /api/notifications/unread-count/ - Get unread count
    # GET /api/notifications/stats/ - Get statistics
    # DELETE /api/notifications/{id}/ - Delete notification
    
    # Preferences
    path('preferences/', NotificationPreferenceViewSet.as_view({
        'get': 'list',
        'put': 'update',
        'patch': 'update'
    }), name='preferences'),
    
    # Send notifications (Admin only)
    path('send/push/', SendNotificationViewSet.as_view({
        'post': 'push'
    }), name='send-push'),
    
    path('send/bulk/', SendNotificationViewSet.as_view({
        'post': 'bulk'
    }), name='send-bulk'),
    
    # Logs (Admin only)
    path('logs/sms/', LogViewSet.as_view({
        'get': 'sms'
    }), name='sms-logs'),
    
    path('logs/email/', LogViewSet.as_view({
        'get': 'email'
    }), name='email-logs'),
    
    # Router URLs
    path('', include(router.urls)),
]