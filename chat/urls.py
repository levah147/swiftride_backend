"""
FILE LOCATION: chat/urls.py

URL routing for chat app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet

app_name = 'chat'

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    # Conversations
    # GET /api/chat/conversations/ - List conversations
    # GET /api/chat/conversations/{id}/ - Get conversation
    # GET /api/chat/conversations/{id}/messages/ - Get messages
    # POST /api/chat/conversations/{id}/archive/ - Archive conversation
    # GET /api/chat/conversations/stats/ - Get statistics
    
    # Messages
    # POST /api/chat/messages/ - Send message
    # GET /api/chat/messages/{id}/ - Get message
    # PUT /api/chat/messages/{id}/ - Edit message
    # DELETE /api/chat/messages/{id}/ - Delete message
    # POST /api/chat/messages/mark-read/ - Mark as read
    # POST /api/chat/messages/upload-attachment/ - Upload file
    
    path('', include(router.urls)),
]