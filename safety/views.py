
"""
FILE LOCATION: safety/views.py
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import EmergencySOS, TripShare, EmergencyContact
from .serializers import (
    EmergencySOSSerializer, TripShareSerializer, EmergencyContactSerializer
)
from .services import trigger_emergency_alert, send_trip_share_notification


class EmergencySOSViewSet(viewsets.ModelViewSet):
    """Emergency SOS management"""
    serializer_class = EmergencySOSSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return EmergencySOS.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def trigger(self, request):
        """Trigger emergency SOS"""
        sos = EmergencySOS.objects.create(
            user=request.user,
            ride_id=request.data.get('ride_id'),
            latitude=request.data.get('latitude'),
            longitude=request.data.get('longitude'),
            address=request.data.get('address', ''),
            notes=request.data.get('notes', '')
        )
        
        # Trigger emergency alert
        trigger_emergency_alert(sos)
        
        serializer = self.get_serializer(sos)
        return Response({
            'success': True,
            'message': 'Emergency alert activated',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve SOS alert"""
        sos = self.get_object()
        sos.status = 'resolved'
        sos.resolved_at = timezone.now()
        sos.save()
        
        return Response({'success': True, 'message': 'SOS resolved'})


class TripShareViewSet(viewsets.ModelViewSet):
    """Trip sharing management"""
    serializer_class = TripShareSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TripShare.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Share trip with contacts"""
        import uuid
        
        trip_share = TripShare.objects.create(
            user=request.user,
            ride_id=request.data.get('ride_id'),
            shared_with=request.data.get('contacts', []),
            share_link=f"https://swiftride.com/track/{uuid.uuid4().hex[:12]}",
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Send notifications
        send_trip_share_notification(trip_share)
        
        serializer = self.get_serializer(trip_share)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


class EmergencyContactViewSet(viewsets.ModelViewSet):
    """Emergency contacts management"""
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)




