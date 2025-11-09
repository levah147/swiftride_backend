

"""
FILE LOCATION: vehicles/tests/test_vehicles.py
Test suite for vehicles app.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from drivers.models import Driver
from vehicles.models import Vehicle
from pricing.models import VehicleType


class VehicleModelTest(TestCase):
    """Test Vehicle model"""
    
    def setUp(self):
        # Create driver
        self.user = User.objects.create_user(
            phone_number='08011111111',
            first_name='Test',
            last_name='Driver'
        )
        self.user.is_driver = True
        self.user.save()
        
        self.driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='TEST123',
            vehicle_year=2020,
            driver_license_number='DL123',
            driver_license_expiry=timezone.now().date() + timedelta(days=365),
            status='approved'
        )
        
        # Create vehicle type
        self.vehicle_type = VehicleType.objects.create(
            name='Sedan',
            description='Standard sedan',
            base_fare=500,
            price_per_km=100
        )
    
    def test_vehicle_creation(self):
        """Test creating a vehicle"""
        vehicle = Vehicle.objects.create(
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            make='Toyota',
            model='Camry',
            year=2020,
            color='Black',
            license_plate='ABC123',
            registration_number='REG123',
            registration_expiry=timezone.now().date() + timedelta(days=365),
            insurance_company='Test Insurance',
            insurance_policy_number='POL123',
            insurance_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        self.assertEqual(vehicle.driver, self.driver)
        self.assertTrue(vehicle.is_active)
        self.assertFalse(vehicle.is_verified)
    
    def test_is_roadworthy(self):
        """Test roadworthy property"""
        vehicle = Vehicle.objects.create(
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            make='Toyota',
            model='Camry',
            year=2020,
            color='Black',
            license_plate='ABC123',
            registration_number='REG123',
            registration_expiry=timezone.now().date() + timedelta(days=365),
            insurance_company='Test Insurance',
            insurance_policy_number='POL123',
            insurance_expiry=timezone.now().date() + timedelta(days=365),
            is_verified=True
        )
        
        self.assertTrue(vehicle.is_roadworthy)


class VehicleAPITest(APITestCase):
    """Test Vehicle API"""
    
    def setUp(self):
        # Create driver
        self.user = User.objects.create_user(
            phone_number='08011111111',
            first_name='Test',
            last_name='Driver'
        )
        self.user.is_driver = True
        self.user.save()
        
        self.driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='TEST123',
            vehicle_year=2020,
            driver_license_number='DL123',
            driver_license_expiry=timezone.now().date() + timedelta(days=365),
            status='approved'
        )
        
        self.vehicle_type = VehicleType.objects.create(
            name='Sedan',
            description='Standard sedan',
            base_fare=500,
            price_per_km=100
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_vehicles(self):
        """Test listing driver's vehicles"""
        Vehicle.objects.create(
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            make='Toyota',
            model='Camry',
            year=2020,
            color='Black',
            license_plate='ABC123',
            registration_number='REG123',
            registration_expiry=timezone.now().date() + timedelta(days=365),
            insurance_company='Test Insurance',
            insurance_policy_number='POL123',
            insurance_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        url = '/api/vehicles/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)






