"""
FILE LOCATION: locations/apps.py
App configuration for locations app.
"""
from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'locations'
    verbose_name = 'Locations'
    
    def ready(self):
        """Import signals when app is ready"""
        import locations.signals  # Load location signals
