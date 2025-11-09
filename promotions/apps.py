
"""
FILE LOCATION: promotions/apps.py
"""
from django.apps import AppConfig


class PromotionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'promotions'
    verbose_name = 'Promotions & Referrals'
    
    def ready(self):
        """Import signals when app is ready"""
        import promotions.signals  # Load promotions signals

 

 