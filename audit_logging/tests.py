"""
FILE LOCATION: audit_logging/tests.py
Tests for audit logging app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import AuditLog, SecurityEvent

User = get_user_model()


class AuditLogTestCase(TestCase):
    """Test cases for AuditLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348167791934',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_audit_log(self):
        """Test creating an audit log"""
        log = AuditLog.log_action(
            user=self.user,
            action_type='create',
            description='Test action',
            severity='medium'
        )
        
        self.assertIsNotNone(log.id)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, 'create')
        self.assertEqual(log.severity, 'medium')
    
    def test_audit_log_str(self):
        """Test audit log string representation"""
        log = AuditLog.log_action(
            user=self.user,
            action_type='create',
            description='Test action'
        )
        
        self.assertIn(self.user.phone_number, str(log))
        self.assertIn('create', str(log))


class SecurityEventTestCase(TestCase):
    """Test cases for SecurityEvent model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348167791934',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_security_event(self):
        """Test creating a security event"""
        event = SecurityEvent.objects.create(
            user=self.user,
            event_type='failed_login',
            severity='medium',
            ip_address='127.0.0.1',
            description='Failed login attempt'
        )
        
        self.assertIsNotNone(event.id)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.event_type, 'failed_login')
        self.assertFalse(event.resolved)
    
    def test_resolve_security_event(self):
        """Test resolving a security event"""
        event = SecurityEvent.objects.create(
            user=self.user,
            event_type='failed_login',
            severity='medium',
            ip_address='127.0.0.1',
            description='Failed login attempt'
        )
        
        event.resolve(resolved_by=self.user, notes='Resolved')
        
        self.assertTrue(event.resolved)
        self.assertIsNotNone(event.resolved_at)
        self.assertEqual(event.resolved_by, self.user)

