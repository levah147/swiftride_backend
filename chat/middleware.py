
"""
FILE LOCATION: chat/middleware.py

WebSocket authentication middleware.
Authenticates WebSocket connections using JWT tokens.
"""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections via JWT.
    
    Usage in routing.py:
    application = JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    )
    """
    
    async def __call__(self, scope, receive, send):
        """Authenticate the connection"""
        
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            try:
                # Validate token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                
                # Get user from database
                scope['user'] = await self.get_user(user_id)
                
            except Exception as e:
                logger.error(f"JWT authentication error: {str(e)}")
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


# Alternative: Token from headers (if your client supports it)
class TokenAuthMiddleware(BaseMiddleware):
    """
    Authenticate via Authorization header.
    """
    
    async def __call__(self, scope, receive, send):
        """Authenticate the connection"""
        
        headers = dict(scope.get('headers', []))
        
        # Get authorization header
        auth_header = headers.get(b'authorization', b'').decode()
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                scope['user'] = await self.get_user(user_id)
            except Exception as e:
                logger.error(f"Token authentication error: {str(e)}")
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()
