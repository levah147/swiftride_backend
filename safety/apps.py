

"""
FILE LOCATION: safety/apps.py
"""
from django.apps import AppConfig


class SafetyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'safety'
    verbose_name = 'Safety Features'
    
    def ready(self):
        """Import signals when app is ready"""
        import safety.signals  # Load safety signals


