"""
FILE LOCATION: audit_logging/middleware.py

Middleware for automatic audit logging of all requests.
Logs critical actions automatically.
"""
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog, SecurityEvent
from .utils import get_client_ip
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

 
class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log critical actions.
    
    Logs:
    - POST, PUT, DELETE requests (create, update, delete actions)
    - Failed authentication attempts
    - Admin actions
    - Payment operations
    """
    
    # Paths to exclude from audit logging (to reduce noise)
    EXCLUDED_PATHS = [
        '/admin/jsi18n/',
        '/static/',
        '/media/',
        '/api/notifications/read/',
        '/api/chat/typing/',
    ]
    
    # Actions that should be logged
    LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Critical paths that should always be logged
    CRITICAL_PATHS = [
        '/api/payments/',
        '/api/rides/',
        '/api/admin-dashboard/',
        '/api/auth/',
    ]
    
    def process_response(self, request, response):
        """Process response and log if necessary"""
        
        # Skip if path is excluded
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return response
        
        # Only log certain HTTP methods
        if request.method not in self.LOGGED_METHODS:
            return response
        
        # Skip if user is not authenticated (unless it's a critical path)
        if not request.user.is_authenticated:
            if not any(request.path.startswith(path) for path in self.CRITICAL_PATHS):
                return response
        
        # Determine action type from HTTP method
        action_map = {
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        action_type = action_map.get(request.method, 'system')
        
        # Determine severity
        severity = 'medium'
        if any(request.path.startswith(path) for path in self.CRITICAL_PATHS):
            severity = 'high'
        if response.status_code >= 500:
            severity = 'critical'
        elif response.status_code >= 400:
            severity = 'high'
        
        # Create description
        description = f"{request.method} {request.path}"
        if request.user.is_authenticated:
            description += f" by {request.user.phone_number}"
        
        # Log the action
        try:
            AuditLog.log_action(
                user=request.user if request.user.is_authenticated else None,
                action_type=action_type,
                description=description,
                severity=severity,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                metadata={
                    'status_code': response.status_code,
                    'content_type': response.get('Content-Type', ''),
                },
                success=response.status_code < 400,
                error_message=response.data.get('error', '') if hasattr(response, 'data') else ''
            )
        except Exception as e:
            # Don't break the request if logging fails
            logger.error(f"Error creating audit log: {str(e)}")
        
        return response


class SecurityEventMiddleware(MiddlewareMixin):
    """
    Middleware to detect and log security events.
    
    Detects:
    - Failed authentication attempts
    - Rate limit violations
    - Suspicious activity patterns
    """
    
    def process_response(self, request, response):
        """Process response and detect security events"""
        
        # Log failed authentication attempts
        if request.path.startswith('/api/auth/') and response.status_code == 401:
            try:
                SecurityEvent.objects.create(
                    user=None,
                    event_type='failed_login',
                    severity='medium',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    description=f"Failed login attempt from {get_client_ip(request)}",
                    metadata={
                        'status_code': response.status_code,
                    }
                )
            except Exception as e:
                logger.error(f"Error creating security event: {str(e)}")
        
        # Log rate limit violations (429 status)
        if response.status_code == 429:
            try:
                SecurityEvent.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    event_type='rate_limit_exceeded',
                    severity='medium',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_path=request.path,
                    request_method=request.method,
                    description=f"Rate limit exceeded for {request.path}",
                    metadata={
                        'status_code': response.status_code,
                    }
                )
            except Exception as e:
                logger.error(f"Error creating security event: {str(e)}")
        
        return response

