"""

file location: accounts/management/commands/cleanup_expired_otps.py

Management command to cleanup expired OTP verification records.

Usage:
    python manage.py cleanup_expired_otps
    python manage.py cleanup_expired_otps --days 7
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import OTPVerification


class Command(BaseCommand):
    help = 'Delete expired OTP verification records from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete OTPs older than this many days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get OTPs to delete
        otps_to_delete = OTPVerification.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = otps_to_delete.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} OTP record(s) '
                    f'older than {days} days.'
                )
            )
            
            # Show sample of records that would be deleted
            if count > 0:
                self.stdout.write("\nSample records:")
                for otp in otps_to_delete[:5]:
                    self.stdout.write(
                        f"  - {otp.phone_number}: {otp.created_at}"
                    )
                if count > 5:
                    self.stdout.write(f"  ... and {count - 5} more")
        else:
            # Actually delete
            deleted_count = otps_to_delete.delete()[0]
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} expired OTP record(s) '
                    f'older than {days} days.'
                )
            )
        
        # Show remaining OTP count
        remaining_count = OTPVerification.objects.count()
        self.stdout.write(
            self.style.WARNING(
                f'Remaining OTP records: {remaining_count}'
            )
        )
        
        # Show statistics
        verified_count = OTPVerification.objects.filter(is_verified=True).count()
        pending_count = OTPVerification.objects.filter(is_verified=False).count()
        
        self.stdout.write("\nStatistics:")
        self.stdout.write(f"  Verified: {verified_count}")
        self.stdout.write(f"  Pending: {pending_count}")
        self.stdout.write(f"  Total: {remaining_count}")