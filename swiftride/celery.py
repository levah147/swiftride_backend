"""
FILE LOCATION: swiftride/celery.py

Celery configuration for SwiftRide.
Handles background tasks and periodic tasks (Celery Beat).
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.settings')

app = Celery('swiftride')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ========================================
# CELERY BEAT SCHEDULE (Periodic Tasks)
# ========================================
app.conf.beat_schedule = {
    # ============ RIDES APP ============
    'cleanup-expired-rides': {
        'task': 'rides.tasks.cleanup_expired_rides',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'auto-complete-stuck-rides': {
        'task': 'rides.tasks.auto_complete_stuck_rides',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'calculate-driver-ratings': {
        'task': 'rides.tasks.calculate_driver_ratings',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    
    # ============ DRIVERS APP ============
    'update-driver-availability': {
        'task': 'drivers.tasks.update_driver_availability',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-locations': {
        'task': 'drivers.tasks.cleanup_old_locations',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    'send-driver-earnings-summary': {
        'task': 'drivers.tasks.send_driver_earnings_summary',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Weekly Monday 9 AM
    },
    
    # ============ PAYMENTS APP ============
    'process-pending-transactions': {
        'task': 'payments.tasks.process_pending_transactions',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'check-payment-status': {
        'task': 'payments.tasks.check_payment_status',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'process-pending-refunds': {
        'task': 'payments.tasks.process_pending_refunds',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'generate-daily-payment-report': {
        'task': 'payments.tasks.generate_daily_payment_report',
        'schedule': crontab(hour=23, minute=30),  # Daily at 11:30 PM
    },
    
    # ============ NOTIFICATIONS APP ============
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'cleanup-old-logs': {
        'task': 'notifications.tasks.cleanup_old_logs',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Weekly Sunday 4 AM
    },
    'send-daily-notification-summary': {
        'task': 'notifications.tasks.send_daily_notification_summary',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    
    # ============ CHAT APP ============
    'cleanup-old-conversations': {
        'task': 'chat.tasks.cleanup_old_conversations',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'cleanup-deleted-messages': {
        'task': 'chat.tasks.cleanup_deleted_messages',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Weekly Sunday 4 AM
    },
    'cleanup-orphaned-attachments': {
        'task': 'chat.tasks.cleanup_orphaned_attachments',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),  # Weekly Sunday 5 AM
    },
    'cleanup-typing-indicators': {
        'task': 'chat.tasks.cleanup_typing_indicators',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'generate-chat-statistics': {
        'task': 'chat.tasks.generate_chat_statistics',
        'schedule': crontab(hour=23, minute=0),  # Daily at 11 PM
    },
    'send-unread-message-notifications': {
        'task': 'chat.tasks.send_unread_message_notifications',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    
    # ============ SUPPORT APP ============
    'auto-close-resolved-tickets': {
        'task': 'support.tasks.auto_close_resolved_tickets',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    
    # ============ ACCOUNTS APP ============
    'cleanup-expired-otps': {
        'task': 'accounts.tasks.cleanup_expired_otps',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'deactivate-inactive-users': {
        'task': 'accounts.tasks.deactivate_inactive_users',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Weekly Sunday 2 AM
    },
}

# ========================================
# CELERY TASK SETTINGS
# ========================================
app.conf.task_routes = {
    # High priority tasks
    'rides.tasks.match_driver_for_ride': {'queue': 'high_priority'},
    'rides.tasks.notify_ride_status': {'queue': 'high_priority'},
    'notifications.tasks.send_push_notification_task': {'queue': 'high_priority'},
    
    # Normal priority tasks
    'payments.tasks.*': {'queue': 'default'},
    'chat.tasks.*': {'queue': 'default'},
    
    # Low priority tasks (cleanup, reports)
    '*.tasks.cleanup_*': {'queue': 'low_priority'},
    '*.tasks.generate_*': {'queue': 'low_priority'},
}

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# Task result expiration
app.conf.result_expires = 3600  # 1 hour

# Task retry settings
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# Worker settings
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 1000

# ========================================
# CELERY SIGNALS
# ========================================
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


# ========================================
# STARTUP TASKS
# ========================================
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup additional periodic tasks"""
    # Add any dynamic periodic tasks here
    pass


# ========================================
# ERROR HANDLING
# ========================================
from celery.signals import task_failure

@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    """Handle task failures"""
    import logging
    logger = logging.getLogger('celery')
    logger.error(f'Task {sender.name} failed: {exception}')
    
    # You can add notification logic here
    # e.g., send email to admin, log to monitoring service, etc.


if __name__ == '__main__':
    app.start()