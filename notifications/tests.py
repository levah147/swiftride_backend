"""
FILE LOCATION: notifications/tests/test_models.py

Unit tests for notifications models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import (
    PushToken,
    Notification,
    NotificationPreference,
    SMSLog,
    EmailLog
)

User = get_user_model()


class PushTokenModelTest(TestCase):
    """Tests for PushToken model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            password='testpass123'
        )
    
    def test_create_push_token(self):
        """Test creating a push token"""
        token = PushToken.objects.create(
            user=self.user,
            token='test_fcm_token_123',
            platform='android',
            device_name='Samsung Galaxy S21'
        )
        
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.platform, 'android')
        self.assertTrue(token.is_active)
    
    def test_push_token_str(self):
        """Test PushToken __str__ method"""
        token = PushToken.objects.create(
            user=self.user,
            token='test_token',
            platform='ios'
        )
        
        self.assertIn(self.user.phone_number, str(token))


class NotificationModelTest(TestCase):
    """Tests for Notification model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            password='testpass123'
        )
    
    def test_create_notification(self):
        """Test creating a notification"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='ride_matched',
            title='Driver Found!',
            body='Your ride has been matched'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
    
    def test_mark_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='general',
            title='Test',
            body='Test notification'
        )
        
        self.assertFalse(notification.is_read)
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_get_unread_count(self):
        """Test getting unread notification count"""
        # Get initial count (may have notifications from signals)
        initial_count = Notification.get_unread_count(self.user)
        
        # Create 3 notifications
        notifications = []
        for i in range(3):
            notifications.append(Notification.objects.create(
                user=self.user,
                notification_type='general',
                title=f'Notification {i}',
                body=f'Body {i}'
            ))
        
        # Mark 1 as read
        notifications[0].mark_as_read()
        
        # Should have initial_count + 2 unread (3 created - 1 read)
        unread_count = Notification.get_unread_count(self.user)
        self.assertEqual(unread_count, initial_count + 2)


class NotificationPreferenceModelTest(TestCase):
    """Tests for NotificationPreference model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            password='testpass123'
        )
    
    def test_create_preference(self):
        """Test creating notification preferences"""
        prefs, created = NotificationPreference.objects.get_or_create(
            user=self.user
        )
        
        # Check defaults
        self.assertTrue(prefs.push_enabled)
        self.assertTrue(prefs.sms_enabled)
        self.assertTrue(prefs.email_enabled)
        self.assertTrue(prefs.inapp_enabled)
    
    def test_update_preference(self):
        """Test updating preferences"""
        prefs, created = NotificationPreference.objects.get_or_create(
            user=self.user
        )
        
        prefs.push_enabled = False
        prefs.save()
        
        prefs.refresh_from_db()
        self.assertFalse(prefs.push_enabled)


class SMSLogModelTest(TestCase):
    """Tests for SMSLog model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            password='testpass123'
        )
    
    def test_create_sms_log(self):
        """Test creating SMS log"""
        log = SMSLog.objects.create(
            user=self.user,
            phone_number=self.user.phone_number,
            message='Test SMS message',
            provider='africastalking',
            status='sent'
        )
        
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.provider, 'africastalking')


class EmailLogModelTest(TestCase):
    """Tests for EmailLog model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_email_log(self):
        """Test creating email log"""
        log = EmailLog.objects.create(
            user=self.user,
            recipient_email=self.user.email,
            subject='Test Email',
            body='Test email body',
            status='sent'
        )
        
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.recipient_email, self.user.email)