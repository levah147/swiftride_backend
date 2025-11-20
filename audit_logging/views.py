"""
FILE LOCATION: audit_logging/views.py
API views for audit logging (admin only).
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import AuditLog, SecurityEvent
from .serializers import AuditLogSerializer, SecurityEventSerializer

 
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (admin only).
    Read-only to prevent tampering with audit logs.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action_type', 'severity', 'success', 'user']
    search_fields = ['description', 'ip_address', 'request_path']
    ordering_fields = ['timestamp', 'severity']
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get audit log statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        stats = {
            'total_logs': AuditLog.objects.count(),
            'last_24h': AuditLog.objects.filter(timestamp__gte=last_24h).count(),
            'last_7d': AuditLog.objects.filter(timestamp__gte=last_7d).count(),
            'by_action_type': {},
            'by_severity': {},
            'failed_actions': AuditLog.objects.filter(success=False).count(),
        }
        
        # Count by action type
        for action_type, _ in AuditLog.ACTION_TYPES:
            stats['by_action_type'][action_type] = AuditLog.objects.filter(
                action_type=action_type
            ).count()
        
        # Count by severity
        for severity, _ in AuditLog.SEVERITY_LEVELS:
            stats['by_severity'][severity] = AuditLog.objects.filter(
                severity=severity
            ).count()
        
        return Response(stats)


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing security events (admin only).
    Read-only to prevent tampering with security events.
    """
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event_type', 'severity', 'resolved']
    search_fields = ['description', 'ip_address', 'request_path']
    ordering_fields = ['timestamp', 'severity']
    ordering = ['-timestamp']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark security event as resolved"""
        event = self.get_object()
        notes = request.data.get('notes', '')
        event.resolve(resolved_by=request.user, notes=notes)
        return Response({'message': 'Security event resolved'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get security event statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        stats = {
            'total_events': SecurityEvent.objects.count(),
            'unresolved': SecurityEvent.objects.filter(resolved=False).count(),
            'last_24h': SecurityEvent.objects.filter(timestamp__gte=last_24h).count(),
            'last_7d': SecurityEvent.objects.filter(timestamp__gte=last_7d).count(),
            'by_event_type': {},
            'by_severity': {},
        }
        
        # Count by event type
        for event_type, _ in SecurityEvent.EVENT_TYPES:
            stats['by_event_type'][event_type] = SecurityEvent.objects.filter(
                event_type=event_type
            ).count()
        
        # Count by severity
        for severity, _ in SecurityEvent.SEVERITY_LEVELS:
            stats['by_severity'][severity] = SecurityEvent.objects.filter(
                severity=severity
            ).count()
        
        return Response(stats)

