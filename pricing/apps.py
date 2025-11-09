
from django.apps import AppConfig


class PricingConfig(AppConfig):
    name = 'pricing'
    verbose_name = 'Pricing & Configuration'
    
    def ready(self):
        """Import signals when app is ready"""
        import pricing.signals



