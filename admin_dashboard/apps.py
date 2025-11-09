
"""
FILE LOCATION: admin_dashboard/apps.py
"""
from django.apps import AppConfig


class AdminDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_dashboard'
    verbose_name = 'Admin Dashboard & Control Center'
    
    def ready(self):
        """Import signals when app is ready"""
        # No signals needed for admin dashboard
        pass

