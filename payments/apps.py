

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = 'Payment Management'
    
    def ready(self):
        """Import signals - CRITICAL for ride payment integration!"""
        import payments.signals  # ⚠️ CRITICAL!


