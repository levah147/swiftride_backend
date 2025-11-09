"""
FILE LOCATION: notifications/views.py

API views for notifications app.
Handles all notification-related endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta

from .models import (
    PushToken,
    Notification,
    NotificationPreference,
    SMSLog,
    EmailLog
)
from .serializers import (
    PushTokenSerializer,
    NotificationSerializer,
    NotificationListSerializer,
    MarkNotificationReadSerializer,
    NotificationPreferenceSerializer,
    SendPushNotificationSerializer,
    SMSLogSerializer,
    EmailLogSerializer,
    NotificationStatsSerializer,
    BulkSendNotificationSerializer
)
from .tasks import (
    send_push_notification_task,
    send_sms_task,
    send_email_task
)


class PushTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing push notification tokens.
    
    Endpoints:
    - POST /api/notifications/tokens/ - Register device token
    - GET /api/notifications/tokens/ - List user's devices
    - DELETE /api/notifications/tokens/{id}/ - Remove device
    """
    
    serializer_class = PushTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return tokens for current user only"""
        return PushToken.objects.filter(user=self.request.user, is_active=True)
    
    def create(self, request, *args, **kwargs):
        """Register a new push token"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
            return Response(
                {
                    'success': True,
                    'message': 'Device registered successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Deactivate a push token"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        
        return Response(
            {
                'success': True,
                'message': 'Device removed successfully'
            },
            status=status.HTTP_200_OK
        )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications.
    
    Endpoints:
    - GET /api/notifications/ - List all notifications
    - GET /api/notifications/{id}/ - Get notification detail
    - POST /api/notifications/mark-read/ - Mark as read
    - GET /api/notifications/unread-count/ - Get unread count
    - GET /api/notifications/stats/ - Get notification statistics
    - DELETE /api/notifications/{id}/ - Delete notification
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        """Return notifications for current user"""
        user = self.request.user
        queryset = Notification.objects.filter(user=user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset.select_related('ride', 'transaction')
    
    def list(self, request, *args, **kwargs):
        """List notifications with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get notification detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """
        Mark notifications as read.
        POST /api/notifications/mark-read/
        Body: {"notification_ids": [1, 2, 3]} or {"mark_all": true}
        """
        serializer = MarkNotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if serializer.validated_data.get('mark_all'):
            # Mark all as read
            updated = Notification.objects.filter(
                user=user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': f'{updated} notifications marked as read'
            })
        
        else:
            # Mark specific notifications as read
            notification_ids = serializer.validated_data.get('notification_ids', [])
            updated = Notification.objects.filter(
                user=user,
                id__in=notification_ids,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': f'{updated} notifications marked as read'
            })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.
        GET /api/notifications/unread-count/
        """
        count = Notification.get_unread_count(request.user)
        
        return Response({
            'success': True,
            'unread_count': count
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get notification statistics.
        GET /api/notifications/stats/
        """
        user = request.user
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        
        notifications = Notification.objects.filter(user=user)
        
        stats = {
            'total_notifications': notifications.count(),
            'unread_count': notifications.filter(is_read=False).count(),
            'read_count': notifications.filter(is_read=True).count(),
            'today_count': notifications.filter(created_at__gte=today_start).count(),
            'this_week_count': notifications.filter(created_at__gte=week_start).count(),
            
            # By type
            'ride_notifications': notifications.filter(
                notification_type__in=['ride_matched', 'ride_accepted', 'ride_started', 'ride_completed']
            ).count(),
            'payment_notifications': notifications.filter(
                notification_type__in=['payment_received', 'wallet_credited', 'wallet_debited']
            ).count(),
            'system_notifications': notifications.filter(
                notification_type__in=['promo_available', 'general']
            ).count(),
        }
        
        serializer = NotificationStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete a notification"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'success': True,
            'message': 'Notification deleted successfully'
        }, status=status.HTTP_200_OK)


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for managing notification preferences.
    
    Endpoints:
    - GET /api/notifications/preferences/ - Get preferences
    - PUT /api/notifications/preferences/ - Update preferences
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get user's notification preferences"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = NotificationPreferenceSerializer(preference)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def update(self, request):
        """Update notification preferences"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = NotificationPreferenceSerializer(
            preference,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Preferences updated successfully',
            'data': serializer.data
        })


class SendNotificationViewSet(viewsets.ViewSet):
    """
    ViewSet for sending notifications (Admin only).
    
    Endpoints:
    - POST /api/notifications/send/push/ - Send push notification
    - POST /api/notifications/send/bulk/ - Send bulk notifications
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def push(self, request):
        """
        Send push notification to users.
        Admin only endpoint.
        """
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SendPushNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Queue push notification task
        task = send_push_notification_task.delay(
            user_ids=data.get('user_ids'),
            user_type=data.get('user_type'),
            title=data['title'],
            body=data['body'],
            notification_type=data.get('notification_type', 'general'),
            data_payload=data.get('data', {})
        )
        
        return Response({
            'success': True,
            'message': 'Notifications queued for delivery',
            'task_id': task.id
        })
    
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """
        Send bulk notifications via multiple channels.
        Admin only endpoint.
        """
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkSendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        recipients = data['recipients']
        
        # Create in-app notifications
        notifications_created = 0
        for user_id in recipients:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                
                notification = Notification.objects.create(
                    user=user,
                    notification_type=data['notification_type'],
                    title=data['title'],
                    body=data['body'],
                    data=data.get('data', {})
                )
                notifications_created += 1
                
                # Queue additional delivery methods
                if data.get('send_push'):
                    send_push_notification_task.delay(
                        user_ids=[user_id],
                        title=data['title'],
                        body=data['body'],
                        notification_type=data['notification_type']
                    )
                
                if data.get('send_sms'):
                    send_sms_task.delay(
                        user_id=user_id,
                        message=f"{data['title']}: {data['body']}"
                    )
                
                if data.get('send_email'):
                    send_email_task.delay(
                        user_id=user_id,
                        subject=data['title'],
                        body=data['body']
                    )
            
            except Exception as e:
                continue
        
        return Response({
            'success': True,
            'message': f'Sent notifications to {notifications_created} users'
        })


class LogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notification logs.
    Admin only.
    
    Endpoints:
    - GET /api/notifications/logs/sms/ - View SMS logs
    - GET /api/notifications/logs/email/ - View email logs
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return logs based on action"""
        if not self.request.user.is_staff:
            return self.get_serializer_class().Meta.model.objects.none()
        
        if self.action == 'sms':
            return SMSLog.objects.all()
        elif self.action == 'email':
            return EmailLog.objects.all()
        return None
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'sms':
            return SMSLogSerializer
        elif self.action == 'email':
            return EmailLogSerializer
        return SMSLogSerializer
    
    @action(detail=False, methods=['get'])
    def sms(self, request):
        """Get SMS logs"""
        queryset = SMSLog.objects.all().order_by('-created_at')[:100]
        serializer = SMSLogSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def email(self, request):
        """Get email logs"""
        queryset = EmailLog.objects.all().order_by('-created_at')[:100]
        serializer = EmailLogSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })