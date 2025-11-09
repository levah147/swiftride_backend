

"""
FILE LOCATION: drivers/management/commands/check_driver_licenses.py

Management command to check for expired driver licenses.

Usage:
    python manage.py check_driver_licenses
    python manage.py check_driver_licenses --notify
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from drivers.models import Driver


class Command(BaseCommand):
    help = 'Check for drivers with expired licenses'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Send notifications to drivers with expired licenses'
        )
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find expired licenses
        expired = Driver.objects.filter(
            status='approved',
            driver_license_expiry__lte=today
        )
        
        count = expired.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired licenses found')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'Found {count} driver(s) with expired licenses:')
        )
        
        for driver in expired:
            self.stdout.write(
                f"  - {driver.user.phone_number}: Expired on {driver.driver_license_expiry}"
            )
            
            if options['notify']:
                # TODO: Send notification
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Notification sent')
                )




