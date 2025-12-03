"""
FILE LOCATION: rides/consumers.py

WebSocket consumer for real-time ride updates.
Handles driver location tracking, ride status updates, and chat.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .models import Ride

User = get_user_model()


class RideConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for ride tracking.
    
    URL: ws://your-backend/ws/ride/<ride_id>/?token=<jwt_token>
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'
        self.user = None
        
        try:
            # Authenticate user from JWT token
            token = self.scope['query_string'].decode().split('token=')[1]
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            self.user = await self.get_user(user_id)
            
            if not self.user:
                await self.close()
                return
            
            # Verify user has access to this ride
            ride = await self.get_ride(self.ride_id)
            if not ride or (ride.user_id != self.user.id and 
                          (not hasattr(ride, 'driver_id') or ride.driver_id != self.user.id)):
                await self.close()
                return
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection',
                'message': 'Connected to ride updates',
                'ride_id': self.ride_id
            }))
            
            print(f"✅ WebSocket connected: User {self.user.id} to Ride {self.ride_id}")
            
        except Exception as e:
            print(f"❌ WebSocket connection error: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"🔌 WebSocket disconnected: Ride {self.ride_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'driver_location':
                await self.handle_driver_location(data)
            
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            
            elif message_type == 'cancel_ride':
                await self.handle_cancel_ride(data)
            
            elif message_type == 'request_driver_location':
                await self.handle_request_driver_location(data)
            
            else:
                print(f"⚠️ Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error handling message: {e}")
    
    async def handle_driver_location(self, data):
        """Broadcast driver location to all connected clients"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'driver_location_update',
                'driver_id': str(self.user.id),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'heading': data.get('heading'),
                'speed': data.get('speed'),
                'timestamp': data.get('timestamp'),
            }
        )
    
    async def handle_chat_message(self, data):
        """Broadcast chat message"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message_update',
                'sender': 'rider' if self.user.id == (await self.get_ride(self.ride_id)).user_id else 'driver',
                'message': data.get('message'),
                'timestamp': data.get('timestamp'),
            }
        )
    
    async def handle_cancel_ride(self, data):
        """Handle ride cancellation"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ride_status_update',
                'status': 'cancelled',
                'reason': data.get('reason'),
                'timestamp': data.get('timestamp'),
            }
        )
    
    async def handle_request_driver_location(self, data):
        """Request current driver location"""
        pass
    
    # Event handlers (receive from group_send)
    
    async def driver_location_update(self, event):
        """Send driver location update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'driver_location',
            'driver_id': event['driver_id'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'heading': event.get('heading'),
            'speed': event.get('speed'),
            'timestamp': event['timestamp'],
        }))
    
    async def ride_status_update(self, event):
        """Send ride status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'ride_status',
            'status': event['status'],
            'message': event.get('message'),
            'timestamp': event.get('timestamp'),
            'data': event.get('data'),
        }))
    
    async def driver_matched_update(self, event):
        """Send driver match notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'driver_matched',
            'driver_id': event['driver_id'],
            'driver_name': event['driver_name'],
            'vehicle_model': event['vehicle_model'],
            'license_plate': event['license_plate'],
            'rating': event['rating'],
            'eta': event['eta'],
            'driver_latitude': event.get('driver_latitude'),
            'driver_longitude': event.get('driver_longitude'),
        }))
    
    async def chat_message_update(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'sender': event['sender'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))
    
    # Database queries (async)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_ride(self, ride_id):
        """Get ride from database"""
        try:
            return Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return None