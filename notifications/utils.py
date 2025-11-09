"""
FILE LOCATION: notifications/utils.py

Utility functions for sending notifications safely.
Handles Celery connection errors gracefully.
"""
import logging
from .tasks import send_notification_all_channels

logger = logging.getLogger(__name__)


def safe_send_notification(*args, **kwargs):
    """
    Safely send notification via Celery.
    Falls back to synchronous execution if Celery is unavailable.
    
    Args:
        *args: Positional arguments for send_notification_all_channels
        **kwargs: Keyword arguments for send_notification_all_channels
    
    Returns:
        bool: True if notification was sent, False otherwise
    """
    try:
        # Try to send notification asynchronously via Celery
        send_notification_all_channels.delay(*args, **kwargs)
        return True
    except Exception as e:
        # If Celery is not available (e.g., during tests), try synchronous execution
        logger.warning(f"Could not send notification asynchronously: {str(e)}")
        try:
            # Fallback to synchronous execution
            send_notification_all_channels(*args, **kwargs)
            return True
        except Exception as sync_error:
            # If synchronous execution also fails, log and continue
            logger.error(f"Could not send notification synchronously: {str(sync_error)}")
            return False
