"""
Setup initial data for SwiftRide
Creates Cities, VehicleTypes, and VehiclePricing
"""
from django.core.management.base import BaseCommand
from pricing.models import City, VehicleType, VehiclePricing
from decimal import Decimal


class Command(BaseCommand):
    help = 'Initialize SwiftRide with initial city, vehicle types, and pricing data'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Setting up SwiftRide initial data...\n")

        # Create Lagos City
        lagos, created = City.objects.get_or_create(
            name="Lagos",
            defaults={
                'state': 'Lagos',
                'country': 'Nigeria',
                'latitude': Decimal('6.5244'),
                'longitude': Decimal('3.3792'),
                'radius_km': Decimal('50.0'),  # FIXED: radius_km not service_radius_km
                'is_active': True,
                'currency': 'NGN',
                'timezone': 'Africa/Lagos'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Created city: {lagos.name}'))
        else:
            self.stdout.write(f'➡️  City already exists: {lagos.name}')

        # Create Vehicle Types (id is primary key, not auto-generated)
        vehicle_types_data = [
            {
                'id': 'bike',  # FIXED: id is the primary key (CharField)
                'name': 'Bike (Okada)',
                'description': 'Motorcycle ride - fastest for short distances',
                'max_passengers': 1,
                'icon_name': 'motorcycle',
                'color': '#FF6B35',
                'is_active': True,
                'display_order': 1
            },
            {
                'id': 'keke',
                'name': 'Keke (Tricycle)',
                'description': 'Tricycle ride - affordable for 2-3 people',
                'max_passengers': 3,
                'icon_name': 'local_taxi',
                'color': '#FFD23F',
                'is_active': True,
                'display_order': 2
            },
            {
                'id': 'car',
                'name': 'Car (Standard)',
                'description': 'Standard car ride - comfortable for up to 4 people',
                'max_passengers': 4,
                'icon_name': 'directions_car',
                'color': '#0066FF',
                'is_active': True,
                'display_order': 3
            },
            {
                'id': 'suv',
                'name': 'SUV (Premium)',
                'description': 'Premium SUV - spacious and comfortable',
                'max_passengers': 6,
                'icon_name': 'airport_shuttle',
                'color': '#6A0572',
                'has_luggage_space': True,
                'is_active': True,
                'display_order': 4
            }
        ]

        for vtype_data in vehicle_types_data:
            vtype, created = VehicleType.objects.get_or_create(
                id=vtype_data['id'],  # FIXED: use id not name
                defaults=vtype_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Created vehicle type: {vtype.name}'))
            else:
                self.stdout.write(f'➡️  Vehicle type already exists: {vtype.name}')

        # Create Pricing for each vehicle type in Lagos
        pricing_data = [
            {
                'vehicle_type_id': 'bike',  # FIXED: use vehicle_type_id
                'base_fare': Decimal('200.00'),
                'price_per_km': Decimal('50.00'),
                'price_per_minute': Decimal('10.00'),
                'minimum_fare': Decimal('500.00')
            },
            {
                'vehicle_type_id': 'keke',
                'base_fare': Decimal('300.00'),
                'price_per_km': Decimal('80.00'),
                'price_per_minute': Decimal('12.00'),
                'minimum_fare': Decimal('600.00')
            },
            {
                'vehicle_type_id': 'car',
                'base_fare': Decimal('500.00'),
                'price_per_km': Decimal('150.00'),
                'price_per_minute': Decimal('15.00'),
                'minimum_fare': Decimal('800.00')
            },
            {
                'vehicle_type_id': 'suv',
                'base_fare': Decimal('800.00'),
                'price_per_km': Decimal('200.00'),
                'price_per_minute': Decimal('20.00'),
                'minimum_fare': Decimal('1200.00')
            }
        ]

        for pricing in pricing_data:
            vtype_id = pricing.pop('vehicle_type_id')
            vtype = VehicleType.objects.get(id=vtype_id)
            
            vpricing, created = VehiclePricing.objects.get_or_create(
                vehicle_type=vtype,
                city=lagos,
                defaults={
                    **pricing,
                    'is_active': True,
                    'is_default': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Created pricing for {vtype.name} in {lagos.name}'
                ))
            else:
                self.stdout.write(
                    f'➡️  Pricing already exists for {vtype.name} in {lagos.name}'
                )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS('✅ SETUP COMPLETE!'))
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   • Cities: {City.objects.count()}")
        self.stdout.write(f"   • Vehicle Types: {VehicleType.objects.count()}")
        self.stdout.write(f"   • Pricing Rules: {VehiclePricing.objects.count()}\n")
