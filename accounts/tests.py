from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User, OTPVerification


class UserModelTest(TestCase):
    """Test cases for User model."""
    
    def test_phone_number_normalization(self):
        """Test phone number normalization on user creation."""
        # Test Nigerian format (0816...)
        user1 = User.objects.create_user(
            phone_number='08167791934',
            first_name='Test',
            last_name='User'
        )
        self.assertEqual(user1.phone_number, '+2348167791934')
        
        # Test with +234 already
        user2 = User.objects.create_user(
            phone_number='+2348167791935',
            first_name='Test2',
            last_name='User2'
        )
        self.assertEqual(user2.phone_number, '+2348167791935')
        
        # Test 10-digit format
        user3 = User.objects.create_user(
            phone_number='8167791936',
            first_name='Test3',
            last_name='User3'
        )
        self.assertEqual(user3.phone_number, '+2348167791936')
    
    def test_user_creation_defaults(self):
        """Test default values on user creation."""
        user = User.objects.create_user(
            phone_number='08167791934',
            first_name='John',
            last_name='Doe'
        )
        self.assertFalse(user.is_phone_verified)
        self.assertFalse(user.is_driver)
        self.assertEqual(user.rating, 5.00)
        self.assertEqual(user.total_rides, 0)
    
    def test_superuser_creation(self):
        """Test superuser creation."""
        admin = User.objects.create_superuser(
            phone_number='08167791934',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_phone_verified)


class OTPVerificationTest(TestCase):
    """Test cases for OTP verification."""
    
    def test_otp_creation(self):
        """Test OTP record creation."""
        otp = OTPVerification.objects.create(
            phone_number='08167791934',
            otp_code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertEqual(otp.phone_number, '+2348167791934')
        self.assertFalse(otp.is_verified)
        self.assertEqual(otp.attempts, 0)
    
    def test_otp_expiration(self):
        """Test OTP expiration check."""
        # Create expired OTP
        expired_otp = OTPVerification.objects.create(
            phone_number='08167791934',
            otp_code='123456',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(expired_otp.is_expired())
        
        # Create valid OTP
        valid_otp = OTPVerification.objects.create(
            phone_number='08167791935',
            otp_code='654321',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertFalse(valid_otp.is_expired())
    
    def test_otp_attempts_increment(self):
        """Test OTP attempts counter."""
        otp = OTPVerification.objects.create(
            phone_number='08167791934',
            otp_code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertEqual(otp.attempts, 0)
        
        otp.increment_attempts()
        self.assertEqual(otp.attempts, 1)
        
        otp.increment_attempts()
        self.assertEqual(otp.attempts, 2)


class OTPAPITest(APITestCase):
    """Test cases for OTP API endpoints."""
    
    def test_send_otp(self):
        """Test OTP sending endpoint."""
        url = '/api/auth/send-otp/'  # Fixed: Changed from /api/accounts/ to /api/auth/
        data = {'phone_number': '08167791934'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('expires_in', response.data)
        
        # Verify OTP was created in database
        otp = OTPVerification.objects.filter(phone_number='+2348167791934').first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
    
    def test_send_otp_without_phone(self):
        """Test OTP sending without phone number."""
        url = '/api/auth/send-otp/'  # Fixed: Changed from /api/accounts/ to /api/auth/
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        phone_number = '08167791934'
        otp_code = '123456'
        
        # Create OTP record
        OTPVerification.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Verify OTP
        url = '/api/auth/verify-otp/'  # Fixed: Changed from /api/accounts/ to /api/auth/
        data = {
            'phone_number': phone_number,
            'otp': otp_code  # Serializer accepts 'otp' and converts to 'otp_code' internally
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
    
    def test_verify_otp_invalid_code(self):
        """Test OTP verification with invalid code."""
        phone_number = '08167791934'
        
        # Create OTP record
        OTPVerification.objects.create(
            phone_number=phone_number,
            otp_code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Try to verify with wrong code
        url = '/api/auth/verify-otp/'  # Fixed: Changed from /api/accounts/ to /api/auth/
        data = {
            'phone_number': phone_number,
            'otp': '999999'  # Wrong code
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_verify_expired_otp(self):
        """Test verification of expired OTP."""
        phone_number = '08167791934'
        otp_code = '123456'
        
        # Create expired OTP
        OTPVerification.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )
        
        url = '/api/auth/verify-otp/'  # Fixed: Changed from /api/accounts/ to /api/auth/
        data = {
            'phone_number': phone_number,
            'otp': otp_code  # Serializer accepts 'otp' and converts to 'otp_code' internally
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'].lower())


class UserProfileAPITest(APITestCase):
    """Test cases for user profile API endpoints."""
    
    def setUp(self):
        """Create a test user and authenticate."""
        self.user = User.objects.create_user(
            phone_number='08167791934',
            first_name='John',
            last_name='Doe'
        )
        self.user.is_phone_verified = True
        self.user.save()
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_get_user_profile(self):
        """Test retrieving user profile."""
        url = '/api/accounts/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+2348167791934')
        self.assertEqual(response.data['first_name'], 'John')
        self.assertEqual(response.data['last_name'], 'Doe')
    
    def test_update_user_profile(self):
        """Test updating user profile."""
        url = '/api/accounts/profile/update/'
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Jane')
        self.assertEqual(response.data['last_name'], 'Smith')
        self.assertEqual(response.data['email'], 'jane@example.com')
        
        # Verify in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
    
    def test_delete_account(self):
        """Test account deletion."""
        url = '/api/accounts/delete-account/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('deleted_phone_number', response.data)
        
        # Verify user is deleted
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access profile."""
        self.client.force_authenticate(user=None)
        
        url = '/api/accounts/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)