
"""
FILE LOCATION: analytics/apps.py
App configuration for analytics app.
"""
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics & Reporting'
    
    def ready(self):
        """Import signals when app is ready"""
        import analytics.signals  # Load analytics signals


