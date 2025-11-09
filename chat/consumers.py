"""
FILE LOCATION: chat/consumers.py

WebSocket consumer for real-time chat.
Handles real-time messaging, typing indicators, read receipts.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, TypingIndicator
from .serializers import MessageSerializer
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.
    
    URL: ws://domain/ws/chat/<conversation_id>/
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify user is participant in conversation
        is_participant = await self.check_user_is_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Clear typing indicator
        await self.clear_typing_indicator()
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        
        Message types:
        - send_message: Send a chat message
        - typing_start: User started typing
        - typing_stop: User stopped typing
        - mark_read: Mark messages as read
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'send_message':
                await self.handle_send_message(data)
            
            elif message_type == 'typing_start':
                await self.handle_typing_start()
            
            elif message_type == 'typing_stop':
                await self.handle_typing_stop()
            
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)
            
            else:
                await self.send_error('Unknown message type')
        
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send_error('Server error')
    
    async def handle_send_message(self, data):
        """Handle sending a chat message"""
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        metadata = data.get('metadata', {})
        reply_to_id = data.get('reply_to_id')
        
        if not content:
            await self.send_error('Message content is required')
            return
        
        # Create message in database
        message = await self.create_message(
            content=content,
            message_type=message_type,
            metadata=metadata,
            reply_to_id=reply_to_id
        )
        
        if not message:
            await self.send_error('Failed to create message')
            return
        
        # Serialize message
        message_data = await self.serialize_message(message)
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
        
        # Clear typing indicator
        await self.clear_typing_indicator()
    
    async def handle_typing_start(self):
        """Handle typing start indicator"""
        await self.set_typing_indicator(True)
        
        # Broadcast typing indicator to others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'phone_number': self.user.phone_number,
                'is_typing': True
            }
        )
    
    async def handle_typing_stop(self):
        """Handle typing stop indicator"""
        await self.clear_typing_indicator()
        
        # Broadcast typing stop to others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'phone_number': self.user.phone_number,
                'is_typing': False
            }
        )
    
    async def handle_mark_read(self, data):
        """Handle marking messages as read"""
        message_ids = data.get('message_ids', [])
        
        if message_ids:
            await self.mark_messages_read(message_ids)
            
            # Notify sender that messages were read
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'message_ids': message_ids,
                    'read_by': self.user.id
                }
            )
    
    # Group message handlers (called by channel_layer.group_send)
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        message = event['message']
        
        # Don't send to self (already sent in handle_send_message)
        if message['sender']['id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'new_message',
                'message': message
            }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send own typing indicator back
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'phone_number': event['phone_number'],
                'is_typing': event['is_typing']
            }))
    
    async def messages_read(self, event):
        """Send read receipt to WebSocket"""
        # Only send to message sender
        message_ids = event['message_ids']
        messages = await self.get_messages_by_ids(message_ids)
        
        for message in messages:
            if message.sender_id == self.user.id:
                await self.send(text_data=json.dumps({
                    'type': 'message_read',
                    'message_id': message.id,
                    'read_by': event['read_by']
                }))
                break
    
    # Helper methods
    
    async def send_error(self, error_message):
        """Send error message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    # Database operations (sync to async)
    
    @database_sync_to_async
    def check_user_is_participant(self):
        """Check if user is participant in conversation"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=self.conversation_id
            )
            return self.user in [conversation.rider, conversation.driver]
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content, message_type, metadata, reply_to_id):
        """Create message in database"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=self.conversation_id
            )
            
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type=message_type,
                metadata=metadata,
                reply_to_id=reply_to_id
            )
            
            return message
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for sending"""
        from .serializers import MessageSerializer
        serializer = MessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def set_typing_indicator(self, is_typing):
        """Set typing indicator in database"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=self.conversation_id
            )
            TypingIndicator.set_typing(conversation, self.user, is_typing)
        except Exception as e:
            logger.error(f"Error setting typing indicator: {str(e)}")
    
    @database_sync_to_async
    def clear_typing_indicator(self):
        """Clear typing indicator"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=self.conversation_id
            )
            TypingIndicator.objects.filter(
                conversation=conversation,
                user=self.user
            ).delete()
        except Exception as e:
            logger.error(f"Error clearing typing indicator: {str(e)}")
    
    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        """Mark messages as read in database"""
        try:
            from django.utils import timezone
            Message.objects.filter(
                id__in=message_ids,
                is_read=False
            ).exclude(sender=self.user).update(
                is_read=True,
                read_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error marking messages read: {str(e)}")
    
    @database_sync_to_async
    def get_messages_by_ids(self, message_ids):
        """Get messages by IDs"""
        return list(Message.objects.filter(id__in=message_ids))