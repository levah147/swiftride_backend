"""
FILE LOCATION: support/views.py

API views for support app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import (
    SupportCategory,
    SupportTicket,
    TicketMessage,
    TicketAttachment,
    FAQ
)
from .serializers import (
    SupportCategorySerializer,
    SupportTicketSerializer,
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    TicketMessageSerializer,
    TicketMessageCreateSerializer,
    TicketAttachmentSerializer,
    TicketUpdateSerializer,
    TicketRatingSerializer,
    FAQSerializer,
    SupportStatsSerializer
)


class SupportCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for support categories.
    
    Endpoints:
    - GET /api/support/categories/ - List categories
    - GET /api/support/categories/{id}/ - Get category
    """
    
    serializer_class = SupportCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return active categories"""
        return SupportCategory.objects.filter(is_active=True)
    
    def list(self, request, *args, **kwargs):
        """List all categories"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for support tickets.
    
    Endpoints:
    - POST /api/support/tickets/ - Create ticket
    - GET /api/support/tickets/ - List tickets
    - GET /api/support/tickets/{id}/ - Get ticket detail
    - PUT /api/support/tickets/{id}/ - Update ticket (staff only)
    - GET /api/support/tickets/{id}/messages/ - Get messages
    - POST /api/support/tickets/{id}/rate/ - Rate ticket
    - GET /api/support/tickets/stats/ - Get statistics (staff only)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'create':
            return SupportTicketCreateSerializer
        elif self.action == 'list':
            return SupportTicketListSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        """Return tickets based on user role"""
        user = self.request.user
        
        if user.is_staff:
            # Staff can see all tickets
            queryset = SupportTicket.objects.all()
        else:
            # Users can only see their own tickets
            queryset = SupportTicket.objects.filter(user=user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        return queryset.select_related(
            'user',
            'category',
            'assigned_to',
            'ride'
        ).prefetch_related('attachments')
    
    def create(self, request, *args, **kwargs):
        """Create a new ticket"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            ticket = serializer.save()
            
            # Return full ticket data
            response_serializer = SupportTicketSerializer(
                ticket,
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'message': 'Ticket created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def list(self, request, *args, **kwargs):
        """List tickets"""
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
        """Get ticket detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """Update ticket (staff only)"""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        serializer = TicketUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update fields
        data = serializer.validated_data
        
        if 'status' in data:
            instance.status = data['status']
            if data['status'] == 'resolved':
                instance.resolved_at = timezone.now()
            elif data['status'] == 'closed':
                instance.closed_at = timezone.now()
        
        if 'priority' in data:
            instance.priority = data['priority']
        
        if 'assigned_to' in data:
            if data['assigned_to']:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                assigned_user = User.objects.get(id=data['assigned_to'])
                instance.assign_to(assigned_user)
            else:
                instance.assigned_to = None
                instance.assigned_at = None
        
        instance.save()
        
        response_serializer = SupportTicketSerializer(instance)
        
        return Response({
            'success': True,
            'message': 'Ticket updated successfully',
            'data': response_serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get messages for a ticket.
        GET /api/support/tickets/{id}/messages/
        """
        ticket = self.get_object()
        
        # Get messages (exclude internal notes for non-staff)
        messages = ticket.messages.all()
        if not request.user.is_staff:
            messages = messages.filter(is_internal=False)
        
        messages = messages.select_related('sender').prefetch_related('attachments')
        
        serializer = TicketMessageSerializer(
            messages,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """
        Rate a ticket.
        POST /api/support/tickets/{id}/rate/
        """
        ticket = self.get_object()
        
        # Check if user owns ticket
        if ticket.user != request.user:
            return Response({
                'success': False,
                'error': 'You can only rate your own tickets'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if ticket is resolved/closed
        if ticket.status not in ['resolved', 'closed']:
            return Response({
                'success': False,
                'error': 'Can only rate resolved or closed tickets'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TicketRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ticket.rating = serializer.validated_data['rating']
        ticket.feedback = serializer.validated_data.get('feedback', '')
        ticket.save(update_fields=['rating', 'feedback'])
        
        return Response({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get support statistics (staff only).
        GET /api/support/tickets/stats/
        """
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        tickets = SupportTicket.objects.all()
        
        stats = {
            'total_tickets': tickets.count(),
            'open_tickets': tickets.filter(status='open').count(),
            'in_progress_tickets': tickets.filter(status='in_progress').count(),
            'resolved_tickets': tickets.filter(status='resolved').count(),
            'closed_tickets': tickets.filter(status='closed').count(),
            'average_response_time': 0.0,  # Calculate if needed
            'average_resolution_time': 0.0,  # Calculate if needed
            'user_rating_average': tickets.filter(
                rating__isnull=False
            ).aggregate(Avg('rating'))['rating__avg'] or 0.0
        }
        
        serializer = SupportStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class TicketMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ticket messages.
    
    Endpoints:
    - POST /api/support/messages/ - Send message
    - GET /api/support/messages/{id}/ - Get message
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'create':
            return TicketMessageCreateSerializer
        return TicketMessageSerializer
    
    def get_queryset(self):
        """Return messages user can access"""
        user = self.request.user
        
        if user.is_staff:
            return TicketMessage.objects.all()
        else:
            return TicketMessage.objects.filter(
                ticket__user=user,
                is_internal=False
            )
    
    def create(self, request, *args, **kwargs):
        """Send a message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            message = serializer.save()
            
            response_serializer = TicketMessageSerializer(
                message,
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'message': 'Message sent successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for FAQs.
    
    Endpoints:
    - GET /api/support/faq/ - List FAQs
    - GET /api/support/faq/{id}/ - Get FAQ
    - POST /api/support/faq/{id}/helpful/ - Mark as helpful
    - POST /api/support/faq/{id}/not-helpful/ - Mark as not helpful
    """
    
    serializer_class = FAQSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return published FAQs"""
        queryset = FAQ.objects.filter(is_published=True)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(question__icontains=search) | Q(answer__icontains=search)
            )
        
        return queryset.select_related('category')
    
    def retrieve(self, request, *args, **kwargs):
        """Get FAQ and increment view count"""
        instance = self.get_object()
        instance.increment_views()
        
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def helpful(self, request, pk=None):
        """Mark FAQ as helpful"""
        faq = self.get_object()
        faq.mark_helpful()
        
        return Response({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
    
    @action(detail=True, methods=['post'])
    def not_helpful(self, request, pk=None):
        """Mark FAQ as not helpful"""
        faq = self.get_object()
        faq.mark_not_helpful()
        
        return Response({
            'success': True,
            'message': 'Thank you for your feedback!'
        })