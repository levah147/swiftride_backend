"""
FILE LOCATION: audit_logging/apps.py
App configuration for audit_logging app.
"""
from django.apps import AppConfig


class AuditLoggingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit_logging'
    verbose_name = 'Audit Logging'
    
    def ready(self):
        """Import signals when app is ready"""
        import audit_logging.signals

