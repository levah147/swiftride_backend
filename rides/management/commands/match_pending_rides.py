

"""
FILE LOCATION: rides/management/commands/match_pending_rides.py

Management command to manually trigger ride matching.

Usage:
    python manage.py match_pending_rides
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from rides.models import Ride, RideRequest
from rides.utils import find_nearby_drivers


class Command(BaseCommand):
    help = 'Match pending rides with nearby drivers'
    
    def handle(self, *args, **options):
        # Find pending rides
        pending_rides = Ride.objects.filter(
            status='pending',
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        
        matched = 0
        
        for ride in pending_rides:
            self.stdout.write(f"Processing ride #{ride.id}...")
            
            # Find nearby drivers
            drivers = find_nearby_drivers(
                float(ride.pickup_latitude),
                float(ride.pickup_longitude)
            )
            
            if drivers:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Found {len(drivers)} drivers nearby"
                    )
                )
                matched += 1
                
                # TODO: Notify drivers
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  No drivers available"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcessed {pending_rides.count()} rides, "
                f"found drivers for {matched}"
            )
        )



