"""
FILE LOCATION: rides/tests/test_rides.py

Comprehensive test suite for rides app.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from accounts.models import User
from drivers.models import Driver
from rides.models import Ride, RideRequest, DriverRideResponse, MutualRating


class RideModelTest(TestCase):
    """Test Ride model"""
    
    def setUp(self):
        from pricing.models import City, VehicleType
        
        # Create rider
        self.rider = User.objects.create_user(
            phone_number='08011111111',
            first_name='John',
            last_name='Rider'
        )
        self.rider.is_phone_verified = True
        self.rider.save()
        
        # Create driver
        self.driver_user = User.objects.create_user(
            phone_number='08022222222',
            first_name='Jane',
            last_name='Driver'
        )
        self.driver_user.is_phone_verified = True
        self.driver_user.is_driver = True
        self.driver_user.save()
        
        # Create city and vehicle type
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State',
            latitude=Decimal('6.5244'),
            longitude=Decimal('3.3792'),
            radius_km=Decimal('50.00')  # Service radius in km
        )
        
        self.vehicle_type = VehicleType.objects.create(
            id='car',
            name='Car',
            description='Standard car',
            max_passengers=4
        )
        
        self.driver = Driver.objects.create(
            user=self.driver_user,
            vehicle_type='car',
            vehicle_color='Black',
            license_plate='ABC123',
            vehicle_year=2020,
            driver_license_number='DL123',
            driver_license_expiry=timezone.now().date() + timedelta(days=365),
            status='approved',
            background_check_passed=True
        )
    
    def test_ride_creation(self):
        """Test creating a ride"""
        ride = Ride.objects.create(
            user=self.rider,
            vehicle_type=self.vehicle_type,
            city=self.city,
            pickup_location='Victoria Island',
            pickup_latitude=6.4281,
            pickup_longitude=3.4219,
            destination_location='Lekki',
            destination_latitude=6.4698,
            destination_longitude=3.5852,
            fare_amount=Decimal('1500.00'),
            distance_km=Decimal('15.5')
        )
        
        self.assertEqual(ride.status, 'pending')
        self.assertEqual(ride.user, self.rider)
        self.assertIsNone(ride.driver)
    
    def test_ride_properties(self):
        """Test ride properties"""
        ride = Ride.objects.create(
            user=self.rider,
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            city=self.city,
            pickup_location='Test',
            pickup_latitude=0.0,
            pickup_longitude=0.0,
            destination_location='Test Dest',
            destination_latitude=0.1,
            destination_longitude=0.1,
            fare_amount=Decimal('500.00')
        )
        
        self.assertEqual(ride.driver_full_name, 'Jane Driver')
        self.assertEqual(ride.driver_phone_number, '+2348022222222')
        self.assertIn('car', ride.vehicle_details.lower())


class RideAPITest(APITestCase):
    """Test Ride API endpoints"""
    
    def setUp(self):
        from pricing.models import City, VehicleType
        
        # Create rider
        self.rider = User.objects.create_user(
            phone_number='08011111111',
            first_name='John',
            last_name='Rider'
        )
        self.rider.is_phone_verified = True
        self.rider.save()
        
        # Create city and vehicle type
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State',
            latitude=Decimal('6.5244'),
            longitude=Decimal('3.3792'),
            radius_km=Decimal('50.00')  # Service radius in km
        )
        
        self.vehicle_type = VehicleType.objects.create(
            id='car',
            name='Car',
            description='Standard car',
            max_passengers=4
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.rider)
    
    def test_create_ride(self):
        """Test creating a ride via API"""
        from pricing.models import VehiclePricing
        from django.core.cache import cache
        from decimal import Decimal
        import hashlib
        
        # Create vehicle pricing for the city
        VehiclePricing.objects.create(
            vehicle_type=self.vehicle_type,
            city=self.city,
            base_fare=Decimal('500.00'),
            price_per_km=Decimal('100.00'),
            price_per_minute=Decimal('10.00'),
            minimum_fare=Decimal('800.00')
        )
        
        # First calculate fare to get fare_hash
        calc_url = '/api/pricing/calculate-fare/'
        calc_data = {
            'vehicle_type': 'car',
            'pickup_latitude': 6.4281,
            'pickup_longitude': 3.4219,
            'destination_latitude': 6.4698,
            'destination_longitude': 3.5852,
            'city_name': 'Lagos'
        }
        calc_response = self.client.post(calc_url, calc_data, format='json')
        
        if calc_response.status_code != status.HTTP_200_OK:
            self.fail(f"Failed to calculate fare: {calc_response.data}")
        
        fare_hash = calc_response.data['fare_hash']
        
        # Now create ride with fare_hash
        url = '/api/rides/'
        data = {
            'pickup_location': 'Victoria Island',
            'pickup_latitude': 6.4281,
            'pickup_longitude': 3.4219,
            'destination_location': 'Lekki',
            'destination_latitude': 6.4698,
            'destination_longitude': 3.5852,
            'ride_type': 'immediate',
            'fare_hash': fare_hash
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ride.objects.count(), 1)
        self.assertEqual(Ride.objects.first().user, self.rider)
    
    def test_list_rides(self):
        """Test listing user's rides"""
        # Create test rides
        Ride.objects.create(
            user=self.rider,
            vehicle_type=self.vehicle_type,
            city=self.city,
            pickup_location='Test 1',
            pickup_latitude=0.0,
            pickup_longitude=0.0,
            destination_location='Test Dest 1',
            destination_latitude=0.1,
            destination_longitude=0.1,
            fare_amount=Decimal('500.00')
        )
        
        url = '/api/rides/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class MutualRatingTest(TestCase):
    """Test MutualRating model"""
    
    def setUp(self):
        # Create rider
        self.rider = User.objects.create_user(
            phone_number='08011111111',
            first_name='John',
            last_name='Rider'
        )
        
        # Create driver
        self.driver_user = User.objects.create_user(
            phone_number='08022222222',
            first_name='Jane',
            last_name='Driver'
        )
        
        # Create city and vehicle type
        from pricing.models import City, VehicleType
        
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State',
            latitude=Decimal('6.5244'),
            longitude=Decimal('3.3792'),
            radius_km=Decimal('50.00')  # Service radius in km
        )
        
        self.vehicle_type = VehicleType.objects.create(
            id='car',
            name='Car',
            description='Standard car',
            max_passengers=4
        )
        
        self.driver = Driver.objects.create(
            user=self.driver_user,
            vehicle_type='car',
            vehicle_color='Black',
            license_plate='ABC123',
            vehicle_year=2020,
            driver_license_number='DL123',
            driver_license_expiry=timezone.now().date() + timedelta(days=365),
            status='approved'
        )
        
        # Create completed ride
        self.ride = Ride.objects.create(
            user=self.rider,
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            city=self.city,
            pickup_location='Test',
            pickup_latitude=0.0,
            pickup_longitude=0.0,
            destination_location='Test Dest',
            destination_latitude=0.1,
            destination_longitude=0.1,
            fare_amount=Decimal('500.00'),
            status='completed',
            completed_at=timezone.now()
        )
    
    def test_mutual_rating_creation(self):
        """Test creating mutual rating"""
        rating, created = MutualRating.objects.get_or_create(
            ride=self.ride,
            defaults={
                'rider_rating': 5,
                'rider_comment': 'Great driver!',
                'rider_rated_at': timezone.now()
            }
        )
        
        # If it already existed, update it
        if not created:
            rating.rider_rating = 5
            rating.rider_comment = 'Great driver!'
            rating.rider_rated_at = timezone.now()
            rating.save()
        
        self.assertFalse(rating.is_complete)
        
        # Driver rates back
        rating.driver_rating = 5
        rating.driver_comment = 'Great passenger!'
        rating.driver_rated_at = timezone.now()
        rating.save()
        
        self.assertTrue(rating.is_complete)
        