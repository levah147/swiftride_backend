"""
FILE LOCATION: chat/views.py

API views for chat app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Count, Max
from django.utils import timezone

from .models import Conversation, Message, MessageAttachment
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageListSerializer,
    MarkMessagesReadSerializer,
    UploadAttachmentSerializer,
    ConversationStatsSerializer
)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing conversations.
    
    Endpoints:
    - GET /api/chat/conversations/ - List conversations
    - GET /api/chat/conversations/{id}/ - Get conversation detail
    - GET /api/chat/conversations/{id}/messages/ - Get messages
    - POST /api/chat/conversations/{id}/archive/ - Archive conversation
    - GET /api/chat/conversations/stats/ - Get conversation statistics
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def get_queryset(self):
        """Return conversations for current user"""
        user = self.request.user
        
        # Get conversations where user is either rider or driver
        queryset = Conversation.objects.filter(
            Q(rider=user) | Q(driver=user),
            status='active'
        ).select_related(
            'rider',
            'driver',
            'ride',
            'last_message',
            'last_message__sender'
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List all conversations"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get conversation detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get messages for a conversation.
        GET /api/chat/conversations/{id}/messages/
        """
        conversation = self.get_object()
        
        # Get messages
        messages = Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).select_related('sender').prefetch_related('attachments')
        
        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive a conversation.
        POST /api/chat/conversations/{id}/archive/
        """
        conversation = self.get_object()
        conversation.archive()
        
        return Response({
            'success': True,
            'message': 'Conversation archived successfully'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get conversation statistics.
        GET /api/chat/conversations/stats/
        """
        user = request.user
        
        conversations = Conversation.objects.filter(
            Q(rider=user) | Q(driver=user)
        )
        
        stats = {
            'total_conversations': conversations.count(),
            'active_conversations': conversations.filter(status='active').count(),
            'archived_conversations': conversations.filter(status='archived').count(),
            'total_messages_sent': Message.objects.filter(sender=user).count(),
            'total_messages_received': Message.objects.filter(
                conversation__in=conversations
            ).exclude(sender=user).count(),
            'unread_messages': Message.objects.filter(
                conversation__in=conversations,
                is_read=False
            ).exclude(sender=user).count()
        }
        
        serializer = ConversationStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages.
    
    Endpoints:
    - POST /api/chat/messages/ - Send message
    - GET /api/chat/messages/{id}/ - Get message detail
    - PUT /api/chat/messages/{id}/ - Edit message
    - DELETE /api/chat/messages/{id}/ - Delete message
    - POST /api/chat/messages/mark-read/ - Mark messages as read
    - POST /api/chat/messages/upload-attachment/ - Upload attachment
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """Return messages for current user's conversations"""
        user = self.request.user
        
        # Get user's conversations
        conversations = Conversation.objects.filter(
            Q(rider=user) | Q(driver=user)
        )
        
        return Message.objects.filter(
            conversation__in=conversations,
            is_deleted=False
        ).select_related('sender', 'conversation').prefetch_related('attachments')
    
    def create(self, request, *args, **kwargs):
        """Send a new message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            message = serializer.save()
            
            # Return full message data
            response_serializer = MessageSerializer(message, context={'request': request})
            
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
    
    def update(self, request, *args, **kwargs):
        """Edit a message"""
        instance = self.get_object()
        
        # Check if user is sender
        if instance.sender != request.user:
            return Response({
                'success': False,
                'error': 'You can only edit your own messages'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get new content
        new_content = request.data.get('content')
        if not new_content:
            return Response({
                'success': False,
                'error': 'Content is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Edit message
        instance.edit_content(new_content)
        
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'message': 'Message updated successfully',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete a message"""
        instance = self.get_object()
        
        # Check if user is sender
        if instance.sender != request.user:
            return Response({
                'success': False,
                'error': 'You can only delete your own messages'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Soft delete
        instance.soft_delete()
        
        return Response({
            'success': True,
            'message': 'Message deleted successfully'
        })
    
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """
        Mark messages as read.
        POST /api/chat/messages/mark-read/
        Body: {"message_ids": [1, 2, 3]} or {"mark_all": true, "conversation_id": 1}
        """
        serializer = MarkMessagesReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if serializer.validated_data.get('mark_all'):
            # Mark all unread messages in conversation
            conversation_id = request.data.get('conversation_id')
            if not conversation_id:
                return Response({
                    'success': False,
                    'error': 'conversation_id required when mark_all is true'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            updated = Message.objects.filter(
                conversation_id=conversation_id,
                is_read=False
            ).exclude(sender=user).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': f'{updated} messages marked as read'
            })
        
        else:
            # Mark specific messages as read
            message_ids = serializer.validated_data.get('message_ids', [])
            updated = Message.objects.filter(
                id__in=message_ids,
                is_read=False
            ).exclude(sender=user).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': f'{updated} messages marked as read'
            })
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request):
        """
        Upload file attachment for a message.
        POST /api/chat/messages/upload-attachment/
        """
        serializer = UploadAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        message_id = serializer.validated_data.get('message_id')
        
        try:
            # Determine attachment type
            if file.content_type.startswith('image/'):
                attachment_type = 'image'
            elif file.content_type == 'application/pdf':
                attachment_type = 'document'
            else:
                attachment_type = 'document'
            
            # Create attachment
            attachment = MessageAttachment.objects.create(
                message_id=message_id,
                attachment_type=attachment_type,
                file=file,
                file_name=file.name,
                file_size=file.size,
                file_type=file.content_type
            )
            
            # If image, you might want to generate thumbnail here
            # (Implementation depends on your image processing library)
            
            return Response({
                'success': True,
                'message': 'File uploaded successfully',
                'data': {
                    'id': attachment.id,
                    'file_url': request.build_absolute_uri(attachment.file.url),
                    'file_name': attachment.file_name,
                    'file_size': attachment.file_size_formatted
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)