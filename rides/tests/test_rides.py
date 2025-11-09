
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
        
        self.driver = Driver.objects.create(
            user=self.driver_user,
            vehicle_type='sedan',
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
        self.assertIn('sedan', ride.vehicle_details.lower())


class RideAPITest(APITestCase):
    """Test Ride API endpoints"""
    
    def setUp(self):
        # Create rider
        self.rider = User.objects.create_user(
            phone_number='08011111111',
            first_name='John',
            last_name='Rider'
        )
        self.rider.is_phone_verified = True
        self.rider.save()
        
        # Authenticate
        self.client.force_authenticate(user=self.rider)
    
    def test_create_ride(self):
        """Test creating a ride via API"""
        url = '/api/rides/'
        data = {
            'pickup_location': 'Victoria Island',
            'pickup_latitude': 6.4281,
            'pickup_longitude': 3.4219,
            'destination_location': 'Lekki',
            'destination_latitude': 6.4698,
            'destination_longitude': 3.5852,
            'ride_type': 'immediate',
            'fare_amount': '1500.00'
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
        
        self.driver = Driver.objects.create(
            user=self.driver_user,
            vehicle_type='sedan',
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
        rating = MutualRating.objects.create(
            ride=self.ride,
            rider_rating=5,
            rider_comment='Great driver!',
            rider_rated_at=timezone.now()
        )
        
        self.assertFalse(rating.is_complete)
        
        # Driver rates back
        rating.driver_rating = 5
        rating.driver_comment = 'Great passenger!'
        rating.driver_rated_at = timezone.now()
        rating.save()
        
        self.assertTrue(rating.is_complete)





