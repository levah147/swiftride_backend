import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.settings')
django.setup()

from accounts.models import User
from drivers.models import Driver
from vehicles.models import Vehicle
from pricing.models import VehicleType

def verify_refactor():
    print("Verifying Driver & Vehicle Refactor...")
    
    # 1. Create a User
    user_email = "test_driver@example.com"
    user_phone = "+2348000000001"
    
    # Cleanup existing test user
    if User.objects.filter(phone_number=user_phone).exists():
        print(f"Deleting existing user: {user_phone}")
        User.objects.get(phone_number=user_phone).delete()
        
    user = User.objects.create_user(
        phone_number=user_phone,
        password="password123",
        first_name="Test",
        last_name="Driver"
    )
    print(f"Created user: {user.phone_number}")

    from datetime import date
    
    # 2. Create a Driver
    if hasattr(user, 'driver_profile'):
        driver = user.driver_profile
        print("Found existing driver profile")
    else:
        driver = Driver.objects.create(
            user=user,
            driver_license_number="DL12345678",
            driver_license_expiry=date(2030, 1, 1)
        )
        print("Created driver profile")

    # 3. Create a VehicleType
    v_type, _ = VehicleType.objects.get_or_create(
        id="sedan",
        defaults={
            'name': "Sedan",
            'description': "Standard sedan car",
            'max_passengers': 4,
            'platform_commission_percentage': 15
        }
    )
    print(f"Vehicle Type: {v_type.name}")

    # 4. Create a Vehicle
    vehicle, created = Vehicle.objects.get_or_create(
        driver=driver,
        license_plate="ABC-123-XY",
        defaults={
            'vehicle_type': v_type,
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'color': 'Silver',
            'registration_number': 'REG123',
            'registration_expiry': '2025-01-01',
            'insurance_company': 'Allianz',
            'insurance_policy_number': 'POL123',
            'insurance_expiry': '2025-01-01'
        }
    )
    print(f"Vehicle: {vehicle.make} {vehicle.model} ({vehicle.license_plate})")

    # 5. Link Vehicle to Driver (current_vehicle)
    driver.current_vehicle = vehicle
    driver.save()
    print("Linked vehicle to driver as current_vehicle")

    # 6. Verify Access
    refreshed_driver = Driver.objects.get(id=driver.id)
    if refreshed_driver.current_vehicle:
        print(f"SUCCESS: Driver current_vehicle is {refreshed_driver.current_vehicle.license_plate}")
        print(f"Vehicle Type via Driver: {refreshed_driver.current_vehicle.vehicle_type.name}")
    else:
        print("FAILURE: Driver current_vehicle is None")

if __name__ == "__main__":
    try:
        verify_refactor()
        print("Verification Complete!")
    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
