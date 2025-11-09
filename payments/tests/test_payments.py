

"""
FILE LOCATION: payments/tests/test_payments.py
"""
from django.test import TestCase
from decimal import Decimal
from accounts.models import User
from drivers.models import Driver
from rides.models import Ride
from payments.models import Wallet, Transaction
from payments.services import process_ride_payment_service


class WalletTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08011111111',
            first_name='Test',
            last_name='User'
        )
        self.wallet = Wallet.objects.create(user=self.user)
    
    def test_add_funds(self):
        """Test adding funds atomically"""
        self.wallet.add_funds(1000)
        self.assertEqual(self.wallet.balance, Decimal('1000.00'))
    
    def test_deduct_funds(self):
        """Test deducting funds with balance check"""
        self.wallet.balance = Decimal('1000.00')
        self.wallet.save()
        
        self.wallet.deduct_funds(500)
        self.assertEqual(self.wallet.balance, Decimal('500.00'))
    
    def test_insufficient_balance(self):
        """Test deduction fails with insufficient balance"""
        with self.assertRaises(ValueError):
            self.wallet.deduct_funds(100)


class RidePaymentTest(TestCase):
    def setUp(self):
        # Create rider
        self.rider = User.objects.create_user(
            phone_number='08011111111',
            first_name='Rider',
            last_name='User'
        )
        self.rider_wallet = Wallet.objects.create(
            user=self.rider,
            balance=Decimal('5000.00')
        )
        
        # Create driver
        self.driver_user = User.objects.create_user(
            phone_number='08022222222',
            first_name='Driver',
            last_name='User'
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
        self.driver_wallet = Wallet.objects.create(user=self.driver_user)
    
    def test_ride_payment_processing(self):
        """Test complete ride payment flow"""
        # Create completed ride
        ride = Ride.objects.create(
            user=self.rider,
            driver=self.driver,
            pickup_location='Test',
            pickup_latitude=0,
            pickup_longitude=0,
            destination_location='Test',
            destination_latitude=0.1,
            destination_longitude=0.1,
            fare_amount=Decimal('2000.00'),
            status='completed'
        )
        
        # Process payment
        rider_txn, driver_txn = process_ride_payment_service(ride)
        
        # Check rider payment
        self.rider_wallet.refresh_from_db()
        self.assertEqual(self.rider_wallet.balance, Decimal('3000.00'))
        
        # Check driver earnings (80% after 20% commission)
        self.driver_wallet.refresh_from_db()
        self.assertEqual(self.driver_wallet.balance, Decimal('1600.00'))
        
        # Check transactions created
        self.assertEqual(rider_txn.amount, Decimal('2000.00'))
        self.assertEqual(driver_txn.amount, Decimal('1600.00'))


