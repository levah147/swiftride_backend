from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import time

from accounts.models import User
from .models import City, VehicleType, VehiclePricing, SurgePricing, FuelPriceAdjustment


class CityModelTest(TestCase):
    """Test cases for City model"""
    
    def setUp(self):
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State',
            latitude=Decimal('6.5244'),
            longitude=Decimal('3.3792'),
            radius_km=Decimal('50.00')
        )
    
    def test_city_creation(self):
        """Test creating a city"""
        self.assertEqual(self.city.name, 'Lagos')
        self.assertEqual(self.city.currency, 'NGN')
        self.assertTrue(self.city.is_active)
    
    def test_get_available_vehicles(self):
        """Test getting available vehicle types"""
        vehicles = self.city.get_available_vehicles()
        self.assertEqual(len(vehicles), 4)
        self.assertIn('bike', vehicles)
        self.assertIn('car', vehicles)
    
    def test_is_within_service_area(self):
        """Test service area boundary check"""
        # Within service area (Lagos coordinates)
        self.assertTrue(
            self.city.is_within_service_area(
                Decimal('6.4550'), 
                Decimal('3.3841')
            )
        )
        
        # Outside service area (Abuja coordinates)
        self.assertFalse(
            self.city.is_within_service_area(
                Decimal('9.0765'),
                Decimal('7.3986')
            )
        )
    
    def test_city_validation(self):
        """Test city data validation"""
        # Invalid latitude
        from django.core.exceptions import ValidationError
        city = City(
            name='Test City',
            state='Test State',
            latitude=Decimal('100.00')  # Invalid
        )
        with self.assertRaises(ValidationError):
            city.full_clean()


class VehiclePricingTest(TestCase):
    """Test cases for vehicle pricing"""
    
    def setUp(self):
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State'
        )
        
        self.vehicle_type = VehicleType.objects.create(
            id='car',
            name='Car',
            description='Standard car',
            max_passengers=4
        )
        
        self.pricing = VehiclePricing.objects.create(
            vehicle_type=self.vehicle_type,
            city=self.city,
            base_fare=Decimal('500.00'),
            price_per_km=Decimal('100.00'),
            price_per_minute=Decimal('10.00'),
            minimum_fare=Decimal('800.00')
        )
    
    def test_fare_calculation_basic(self):
        """Test basic fare calculation"""
        fare = self.pricing.calculate_fare(
            distance_km=5.0,
            duration_minutes=15,
            surge_multiplier=1.0
        )
        
        # 500 + (100 * 5) + (10 * 15) = 1150
        expected = Decimal('1150.00')
        self.assertEqual(fare, expected)
    
    def test_fare_calculation_minimum(self):
        """Test minimum fare enforcement"""
        fare = self.pricing.calculate_fare(
            distance_km=0.5,
            duration_minutes=2,
            surge_multiplier=1.0
        )
        
        # Should return minimum fare
        self.assertEqual(fare, self.pricing.minimum_fare)
    
    def test_fare_calculation_with_surge(self):
        """Test fare calculation with surge"""
        fare = self.pricing.calculate_fare(
            distance_km=5.0,
            duration_minutes=15,
            surge_multiplier=2.0
        )
        
        # (500 + 500 + 150) * 2 = 2300
        expected = Decimal('2300.00')
        self.assertEqual(fare, expected)
    
    def test_driver_earnings_calculation(self):
        """Test driver earnings calculation"""
        total_fare = Decimal('1000.00')
        earnings = self.pricing.calculate_driver_earnings(total_fare)
        
        # Platform takes 20%, driver gets 80%
        self.assertEqual(earnings['total_fare'], total_fare)
        self.assertEqual(earnings['platform_fee'], Decimal('200.00'))
        self.assertEqual(earnings['driver_earnings'], Decimal('800.00'))


class SurgePricingTest(TestCase):
    """Test cases for surge pricing"""
    
    def setUp(self):
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State'
        )
    
    def test_surge_creation(self):
        """Test creating surge pricing rule"""
        surge = SurgePricing.objects.create(
            name='Morning Rush',
            city=self.city,
            surge_level='moderate',
            multiplier=Decimal('1.5'),
            start_time=time(7, 0),
            end_time=time(10, 0)
        )
        
        self.assertEqual(surge.multiplier, Decimal('1.5'))
        self.assertTrue(surge.monday)
    
    def test_get_current_multiplier_no_surge(self):
        """Test getting multiplier when no surge active"""
        multiplier = SurgePricing.get_current_multiplier(self.city)
        self.assertEqual(multiplier, 1.0)
    
    def test_surge_time_validation(self):
        """Test surge time range validation"""
        from django.core.exceptions import ValidationError
        
        surge = SurgePricing(
            name='Invalid',
            city=self.city,
            multiplier=Decimal('1.5'),
            start_time=time(10, 0),
            end_time=time(8, 0)  # Before start time
        )
        
        with self.assertRaises(ValidationError):
            surge.full_clean()


class FuelPriceAdjustmentTest(TestCase):
    """Test cases for fuel price adjustments"""
    
    def setUp(self):
        self.city = City.objects.create(
            name='Lagos',
            state='Lagos State'
        )
        
        self.fuel_adj = FuelPriceAdjustment.objects.create(
            city=self.city,
            fuel_price_per_litre=Decimal('1000.00'),
            baseline_fuel_price=Decimal('800.00'),
            adjustment_per_100_naira=Decimal('10.00')
        )
    
    def test_calculate_adjustment(self):
        """Test fuel adjustment calculation"""
        adjustment = self.fuel_adj.calculate_adjustment()
        
        # (1000 - 800) / 100 * 10 = 20
        expected = Decimal('20.00')
        self.assertEqual(adjustment, expected)
    
    def test_no_adjustment_below_baseline(self):
        """Test no adjustment when fuel price below baseline"""
        self.fuel_adj.fuel_price_per_litre = Decimal('700.00')
        self.fuel_adj.save()
        
        adjustment = self.fuel_adj.calculate_adjustment()
        self.assertEqual(adjustment, Decimal('0.00'))


class VehicleAPITest(APITestCase):
    """Test cases for vehicle API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08167791934',
            first_name='Test',
            last_name='User'
        )
        self.user.is_phone_verified = True
        self.user.save()
        
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
        
        self.pricing = VehiclePricing.objects.create(
            vehicle_type=self.vehicle_type,
            city=self.city,
            base_fare=Decimal('500.00'),
            price_per_km=Decimal('100.00'),
            price_per_minute=Decimal('10.00'),
            minimum_fare=Decimal('800.00')
        )
    
    def test_list_cities(self):
        """Test listing active cities"""
        url = '/api/pricing/cities/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response may be paginated or a list
        if isinstance(response.data, dict) and 'results' in response.data:
            cities = response.data['results']
        else:
            cities = response.data
        
        self.assertGreaterEqual(len(cities), 1)
        city_names = [c['name'] for c in cities]
        self.assertIn('Lagos', city_names)
    
    def test_detect_city(self):
        """Test city detection from coordinates"""
        url = '/api/pricing/detect-city/'
        data = {
            'latitude': 6.5244,
            'longitude': 3.3792
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Lagos')
    
    def test_get_available_vehicles(self):
        """Test getting available vehicles for city"""
        url = '/api/pricing/types/?city=Lagos'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vehicles', response.data)
        self.assertEqual(len(response.data['vehicles']), 1)
    
    def test_calculate_fare(self):
        """Test fare calculation"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/pricing/calculate-fare/'
        data = {
            'vehicle_type': 'car',
            'pickup_latitude': 6.5244,
            'pickup_longitude': 3.3792,
            'destination_latitude': 6.4550,
            'destination_longitude': 3.3841,
            'city_name': 'Lagos'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_fare', response.data)
        self.assertIn('fare_hash', response.data)
        self.assertGreater(response.data['total_fare'], 0)
    
    def test_calculate_fare_requires_auth(self):
        """Test fare calculation requires authentication"""
        url = '/api/pricing/calculate-fare/'
        data = {
            'vehicle_type': 'car',
            'pickup_latitude': 6.5244,
            'pickup_longitude': 3.3792,
            'destination_latitude': 6.4550,
            'destination_longitude': 3.3841
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_calculate_fare_invalid_distance(self):
        """Test fare calculation with too short distance"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/pricing/calculate-fare/'
        data = {
            'vehicle_type': 'car',
            'pickup_latitude': 6.5244,
            'pickup_longitude': 3.3792,
            'destination_latitude': 6.5244,  # Same as pickup
            'destination_longitude': 3.3792,
            'city_name': 'Lagos'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('too close', response.data['error'].lower())
    
    def test_verify_fare(self):
        """Test fare verification"""
        self.client.force_authenticate(user=self.user)
        
        # First calculate fare
        calc_url = '/api/pricing/calculate-fare/'
        calc_data = {
            'vehicle_type': 'car',
            'pickup_latitude': 6.5244,
            'pickup_longitude': 3.3792,
            'destination_latitude': 6.4550,
            'destination_longitude': 3.3841,
            'city_name': 'Lagos'
        }
        
        calc_response = self.client.post(calc_url, calc_data, format='json')
        if calc_response.status_code != status.HTTP_200_OK:
            self.fail(f"Failed to calculate fare: {calc_response.data}")
        fare_hash = calc_response.data['fare_hash']
        
        # Then verify it
        verify_url = '/api/pricing/verify-fare/'
        verify_data = {'fare_hash': fare_hash}
        
        verify_response = self.client.post(verify_url, verify_data, format='json')
        
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_response.data['valid'])
    
    def test_get_surge_info(self):
        """Test getting surge information"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/pricing/surge-info/?city=Lagos'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_multiplier', response.data)
        self.assertEqual(response.data['current_multiplier'], 1.0)