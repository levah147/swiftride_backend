from django.apps import AppConfig

class VehiclesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vehicles'
    verbose_name = 'Vehicle Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import vehicles.signals

