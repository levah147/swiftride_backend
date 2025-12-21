from django.core.management.base import BaseCommand
from rides.models import Ride, RideRequest, DriverRideResponse, MutualRating

class Command(BaseCommand):
    help = 'Clean all ride data'

    def handle(self, *args, **options):
        DriverRideResponse.objects.all().delete()
        RideRequest.objects.all().delete()
        MutualRating.objects.all().delete()
        Ride.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('✅ All ride data cleaned!'))