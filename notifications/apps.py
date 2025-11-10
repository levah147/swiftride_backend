
"""
FILE LOCATION: notifications/apps.py
App configuration for notifications app.
"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'Notifications'
    
    def ready(self):
        """Import signals when app is ready"""
        import notifications.signals
        # CRITICAL: Setup cross-app signal handlers
        # This connects notifications to all other apps (drivers, rides, payments, vehicles, etc.)
        notifications.signals.setup_cross_app_signals()

