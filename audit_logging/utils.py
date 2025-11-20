"""
FILE LOCATION: audit_logging/utils.py

Utility functions for audit logging.
"""
from .models import AuditLog, SecurityEvent
from django.contrib.contenttypes.models import ContentType


def get_client_ip(request):
    """
    Get the client's IP address from the request.
    Handles proxy headers (X-Forwarded-For, X-Real-IP).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_action(
    user,
    action_type,
    content_object=None,
    description='',
    severity='medium',
    request=None,
    metadata=None,
    success=True,
    error_message=None
):
    """
    Convenience function to log a user action.
    
    Usage:
        from audit_logging.utils import log_user_action
        
        log_user_action(
            user=request.user,
            action_type='create',
            content_object=ride,
            description='Ride created',
            request=request,
            metadata={'ride_id': ride.id}
        )
    """
    ip_address = None
    user_agent = ''
    request_path = ''
    request_method = ''
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request_path = request.path
        request_method = request.method
    
    return AuditLog.log_action(
        user=user,
        action_type=action_type,
        content_object=content_object,
        description=description,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent,
        request_path=request_path,
        request_method=request_method,
        metadata=metadata or {},
        success=success,
        error_message=error_message
    )


def log_security_event(
    event_type,
    description,
    severity='medium',
    user=None,
    request=None,
    metadata=None
):
    """
    Convenience function to log a security event.
    
    Usage:
        from audit_logging.utils import log_security_event
        
        log_security_event(
            event_type='suspicious_activity',
            description='Multiple failed login attempts',
            severity='high',
            request=request
        )
    """
    ip_address = None
    user_agent = ''
    request_path = ''
    request_method = ''
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request_path = request.path
        request_method = request.method
    
    return SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent,
        request_path=request_path,
        request_method=request_method,
        description=description,
        metadata=metadata or {}
    )
    