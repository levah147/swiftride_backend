from django.apps import AppConfig


class DriversConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'drivers'
    verbose_name = 'Driver Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import drivers.signals  # ⚠️ IMPORTANT: Load signal handlers