
"""
FILE LOCATION: admin_dashboard/tests/test_admin.py

Unit tests for admin dashboard.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminDashboardTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone_number='+2348011111111',
            password='testpass123'
        )
    
    def test_admin_can_access(self):
        """Test that admin users have proper access"""
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_superuser)

