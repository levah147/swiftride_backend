from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, datetime
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User
from .models import Driver, DriverVerificationDocument, VehicleImage, DriverRating


class DriverModelTest(TestCase):
    """Test cases for Driver model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08167791934',
            first_name='John',
            last_name='Doe'
        )
        self.user.is_phone_verified = True
        self.user.save()
    
    def test_driver_creation(self):
        """Test creating a driver profile"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        self.assertEqual(driver.status, 'pending')
        self.assertFalse(driver.is_online)
        self.assertFalse(driver.is_available)
        self.assertEqual(driver.rating, 5.00)
        self.assertEqual(driver.total_rides, 0)
    
    def test_license_plate_uppercase(self):
        """Test license plate is converted to uppercase"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='abc123xy',  # lowercase
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        self.assertEqual(driver.license_plate, 'ABC123XY')
    
    def test_expired_license(self):
        """Test license expiry check"""
        # Test that validation prevents expired license
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as context:
            driver = Driver(
                user=self.user,
                vehicle_type='sedan',
                vehicle_color='Black',
                license_plate='ABC123XY',
                vehicle_year=2020,
                driver_license_number='DL123456',
                driver_license_expiry=timezone.now().date() - timedelta(days=1)  # Expired
            )
            driver.full_clean()  # This will trigger validation
        self.assertIn('driver_license_expiry', str(context.exception))
    
    def test_can_accept_rides(self):
        """Test can_accept_rides property"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        # Initially cannot accept (pending status)
        self.assertFalse(driver.can_accept_rides)
        
        # Approve and pass background check
        driver.status = 'approved'
        driver.background_check_passed = True
        driver.save()
        
        self.assertTrue(driver.can_accept_rides)
    
    def test_update_rating(self):
        """Test rating calculation"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        # Create riders
        rider1 = User.objects.create_user(
            phone_number='08111111111',
            first_name='Rider',
            last_name='One'
        )
        rider2 = User.objects.create_user(
            phone_number='08222222222',
            first_name='Rider',
            last_name='Two'
        )
        
        # Add ratings
        DriverRating.objects.create(driver=driver, rider=rider1, rating=4.0)
        DriverRating.objects.create(driver=driver, rider=rider2, rating=5.0)
        
        # Rating should be updated automatically
        driver.refresh_from_db()
        self.assertEqual(driver.rating, 4.5)
        self.assertEqual(driver.total_ratings, 2)


class DriverAPITest(APITestCase):
    """Test cases for Driver API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08167791934',
            first_name='John',
            last_name='Doe'
        )
        self.user.is_phone_verified = True
        self.user.save()
        
        self.client.force_authenticate(user=self.user)
    
    def test_driver_application(self):
        """Test submitting driver application"""
        url = '/api/drivers/apply/'
        data = {
            'vehicle_type': 'sedan',
            'vehicle_color': 'Black',
            'license_plate': 'ABC123XY',
            'vehicle_year': 2020,
            'driver_license_number': 'DL123456',
            'driver_license_expiry': (timezone.now().date() + timedelta(days=365)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('driver', response.data)
        self.assertEqual(response.data['driver']['status'], 'pending')
    
    def test_duplicate_application(self):
        """Test applying twice returns error"""
        # Create first application
        Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        # Try to apply again
        url = '/api/drivers/apply/'
        data = {
            'vehicle_type': 'suv',
            'vehicle_color': 'White',
            'license_plate': 'XYZ789AB',
            'vehicle_year': 2021,
            'driver_license_number': 'DL789012',
            'driver_license_expiry': (timezone.now().date() + timedelta(days=365)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_driver_profile(self):
        """Test retrieving driver profile"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        url = '/api/drivers/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['license_plate'], 'ABC123XY')
    
    def test_get_driver_status(self):
        """Test checking driver status"""
        url = '/api/drivers/status/'
        
        # Before application
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_driver'])
        
        # After application
        Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_driver'])
        self.assertEqual(response.data['driver']['status'], 'pending')
    
    def test_upload_document(self):
        """Test uploading verification document"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        url = '/api/drivers/upload-document/'
        
        # Create a dummy file
        file_content = b'Test document content'
        document = SimpleUploadedFile('license.pdf', file_content, content_type='application/pdf')
        
        data = {
            'document_type': 'license',
            'document': document
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['document_type'], 'license')
        self.assertTrue(response.data['document_url'])
    
    def test_documents_status(self):
        """Test getting document upload status"""
        driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        url = '/api/drivers/documents-status/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('documents', response.data)
        self.assertIn('images', response.data)
        self.assertIn('ready_for_review', response.data)


class AdminDriverAPITest(APITestCase):
    """Test cases for admin driver endpoints"""
    
    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            phone_number='08100000000',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        
        # Create regular user and driver
        self.user = User.objects.create_user(
            phone_number='08167791934',
            first_name='John',
            last_name='Doe'
        )
        self.user.is_phone_verified = True
        self.user.save()
        
        self.driver = Driver.objects.create(
            user=self.user,
            vehicle_type='sedan',
            vehicle_color='Black',
            license_plate='ABC123XY',
            vehicle_year=2020,
            driver_license_number='DL123456',
            driver_license_expiry=timezone.now().date() + timedelta(days=365)
        )
        
        # Create required documents
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_content = b'Test document'
        
        for doc_type in ['license', 'registration', 'insurance', 'id_card']:
            doc = DriverVerificationDocument.objects.create(
                driver=self.driver,
                document_type=doc_type,
                document=SimpleUploadedFile(f'{doc_type}.pdf', file_content)
            )
            doc.is_verified = True
            doc.save()
        
        self.driver.background_check_passed = True
        self.driver.save()
        
        self.client.force_authenticate(user=self.admin)
    
    def test_admin_list_drivers(self):
        """Test admin can list all drivers"""
        url = '/api/drivers/admin/list/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response may be paginated
        if isinstance(response.data, dict) and 'results' in response.data:
            # Paginated response
            self.assertGreaterEqual(len(response.data['results']), 1)
            # Check that our driver is in the list
            driver_ids = [d['id'] for d in response.data['results']]
            self.assertIn(self.driver.id, driver_ids)
        else:
            # Non-paginated response
            self.assertGreaterEqual(len(response.data), 1)
            driver_ids = [d['id'] for d in response.data]
            self.assertIn(self.driver.id, driver_ids)
    
    def test_admin_approve_driver(self):
        """Test admin can approve driver"""
        url = f'/api/drivers/admin/approve/{self.driver.id}/'
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, 'approved')
        self.assertTrue(self.driver.user.is_driver)
    
    def test_admin_reject_driver(self):
        """Test admin can reject driver"""
        url = f'/api/drivers/admin/reject/{self.driver.id}/'
        data = {'rejection_reason': 'Invalid documents'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, 'rejected')
        self.assertEqual(self.driver.rejection_reason, 'Invalid documents')
    
    def test_approve_without_documents(self):
        """Test cannot approve without verified documents"""
        # Create driver without documents
        user2 = User.objects.create_user(
            phone_number='08111111111',
            first_name='Jane',
            last_name='Smith'
        )
        driver2 = Driver.objects.create(
            user=user2,
            vehicle_type='suv',
            vehicle_color='White',
            license_plate='XYZ789AB',
            vehicle_year=2021,
            driver_license_number='DL789012',
            driver_license_expiry=timezone.now().date() + timedelta(days=365),
            background_check_passed=True
        )
        
        url = f'/api/drivers/admin/approve/{driver2.id}/'
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('missing_documents', response.data)
    
    def test_admin_verify_document(self):
        """Test admin can verify individual document"""
        # Create unverified document
        from django.core.files.uploadedfile import SimpleUploadedFile
        doc = DriverVerificationDocument.objects.create(
            driver=self.driver,
            document_type='vehicle_inspection',
            document=SimpleUploadedFile('inspection.pdf', b'Test')
        )
        
        url = f'/api/drivers/admin/verify-document/{doc.id}/'
        data = {'notes': 'Document verified by admin'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        doc.refresh_from_db()
        self.assertTrue(doc.is_verified)
        self.assertEqual(doc.verified_by, self.admin)
        self.assertIsNotNone(doc.verified_date)
    
    def test_non_admin_cannot_approve(self):
        """Test regular users cannot approve drivers"""
        self.client.force_authenticate(user=self.user)
        
        url = f'/api/drivers/admin/approve/{self.driver.id}/'
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)