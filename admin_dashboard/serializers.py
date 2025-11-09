"""
FILE LOCATION: admin_dashboard/serializers.py

===========================================
ADMIN DASHBOARD SERIALIZERS - EXPLAINED
===========================================

WHAT THIS FILE DOES:
- Converts database data to JSON format for API responses
- Validates incoming data from API requests
- Formats data for admin dashboard display

Think of serializers as translators between:
Database ↔ JSON (API)
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AdminActionLog, PlatformSettings, SystemNotification, UserReport

User = get_user_model()


# ==========================================
# USER MANAGEMENT SERIALIZERS
# ==========================================

class UserListSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Shows user info in admin user list
    - Includes important fields only (not sensitive data)
    
    USED IN:
    GET /api/admin/users/ - List all users
    
    OUTPUT EXAMPLE:
    {
        "id": 123,
        "phone_number": "+2348012345678",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "is_driver": false,
        "total_rides": 25,
        "created_at": "2025-01-15T10:30:00Z"
    }
    """
    
    total_rides = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone_number',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_driver',
            'total_rides',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_total_rides(self, obj):
        """Count user's completed rides"""
        from rides.models import Ride
        return Ride.objects.filter(
            rider=obj,
            status='completed'
        ).count()


class UserDetailSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Shows full user details when admin clicks on a user
    - More information than the list view
    
    USED IN:
    GET /api/admin/users/123/ - Get specific user
    """
    
    total_rides = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone_number',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_driver',
            'is_staff',
            'total_rides',
            'total_spent',
            'average_rating',
            'created_at',
            'last_login',
        ]
        read_only_fields = fields
    
    def get_total_rides(self, obj):
        from rides.models import Ride
        return Ride.objects.filter(rider=obj, status='completed').count()
    
    def get_total_spent(self, obj):
        from rides.models import Ride
        from django.db.models import Sum
        total = Ride.objects.filter(
            rider=obj,
            status='completed'
        ).aggregate(Sum('final_fare'))['final_fare__sum']
        return total or 0
    
    def get_average_rating(self, obj):
        if obj.is_driver:
            try:
                from rides.models import Ride
                from django.db.models import Avg
                avg = Ride.objects.filter(
                    driver=obj.driver,
                    driver_rating__isnull=False
                ).aggregate(Avg('driver_rating'))['driver_rating__avg']
                return round(avg, 2) if avg else None
            except:
                return None
        return None


class BanUserSerializer(serializers.Serializer):
    """
    WHAT IT DOES:
    - Validates data when admin wants to ban a user
    - Ensures reason is provided
    
    USED IN:
    POST /api/admin/users/ban/
    
    INPUT EXAMPLE:
    {
        "user_id": 123,
        "reason": "Spam account"
    }
    """
    
    user_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=True, min_length=10)
    
    def validate_user_id(self, value):
        """Check if user exists"""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found")
        return value


# ==========================================
# DRIVER MANAGEMENT SERIALIZERS
# ==========================================

class DriverApprovalSerializer(serializers.Serializer):
    """
    WHAT IT DOES:
    - Validates driver approval/rejection requests
    
    USED IN:
    POST /api/admin/drivers/approve/
    POST /api/admin/drivers/reject/
    
    INPUT EXAMPLE:
    {
        "driver_id": 456,
        "notes": "Documents verified"
    }
    """
    
    driver_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


# ==========================================
# ADMIN ACTION LOG SERIALIZERS
# ==========================================

class AdminActionLogSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Shows admin action history
    - Displays who did what and when
    
    USED IN:
    GET /api/admin/actions/ - View admin activity log
    
    OUTPUT EXAMPLE:
    {
        "id": 789,
        "admin_name": "+2348011111111",
        "action_type": "user_ban",
        "action_display": "Ban User",
        "target_type": "user",
        "target_id": 123,
        "reason": "Spam account",
        "created_at": "2025-01-15T14:30:00Z"
    }
    """
    
    admin_name = serializers.CharField(
        source='admin.phone_number',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_type_display',
        read_only=True
    )
    
    class Meta:
        model = AdminActionLog
        fields = [
            'id',
            'admin_name',
            'action_type',
            'action_display',
            'target_type',
            'target_id',
            'reason',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields


# ==========================================
# PLATFORM SETTINGS SERIALIZERS
# ==========================================

class PlatformSettingsSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Allows admins to view and update platform settings
    
    USED IN:
    GET /api/admin/settings/ - List all settings
    PUT /api/admin/settings/{id}/ - Update a setting
    
    OUTPUT EXAMPLE:
    {
        "id": 1,
        "key": "base_fare",
        "value": "500",
        "value_type": "number",
        "description": "Base fare for all rides",
        "category": "pricing"
    }
    """
    
    class Meta:
        model = PlatformSettings
        fields = [
            'id',
            'key',
            'value',
            'value_type',
            'description',
            'category',
            'is_active',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


# ==========================================
# STATISTICS SERIALIZERS
# ==========================================

class PlatformStatsSerializer(serializers.Serializer):
    """
    WHAT IT DOES:
    - Formats platform overview statistics
    - Used in admin dashboard homepage
    
    OUTPUT EXAMPLE:
    {
        "total_users": 5000,
        "total_drivers": 500,
        "active_drivers": 120,
        "total_rides": 25000,
        "active_rides": 15,
        "today_rides": 350,
        "today_revenue": "175000.00",
        "total_revenue": "12500000.00"
    }
    """
    
    # Users
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    
    # Drivers
    total_drivers = serializers.IntegerField()
    active_drivers = serializers.IntegerField()
    pending_driver_approvals = serializers.IntegerField()
    
    # Rides
    total_rides = serializers.IntegerField()
    active_rides = serializers.IntegerField()
    today_rides = serializers.IntegerField()
    
    # Revenue
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    platform_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


# ==========================================
# USER REPORT SERIALIZERS
# ==========================================

class UserReportSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Shows user reports/complaints
    - Helps admins review issues
    
    OUTPUT EXAMPLE:
    {
        "id": 999,
        "reporter": "+2348011111111",
        "reported_user": "+2348022222222",
        "report_type": "harassment",
        "description": "Driver was rude",
        "status": "pending",
        "created_at": "2025-01-15T12:00:00Z"
    }
    """
    
    reporter_phone = serializers.CharField(
        source='reporter.phone_number',
        read_only=True
    )
    reported_user_phone = serializers.CharField(
        source='reported_user.phone_number',
        read_only=True
    )
    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    
    class Meta:
        model = UserReport
        fields = [
            'id',
            'reporter_phone',
            'reported_user_phone',
            'report_type',
            'report_type_display',
            'description',
            'status',
            'ride',
            'admin_notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ==========================================
# SYSTEM NOTIFICATION SERIALIZERS
# ==========================================

class SystemNotificationSerializer(serializers.ModelSerializer):
    """
    WHAT IT DOES:
    - Formats system-wide notifications
    - Used when admins send announcements
    """
    
    class Meta:
        model = SystemNotification
        fields = [
            'id',
            'title',
            'message',
            'notification_type',
            'target_audience',
            'is_active',
            'scheduled_at',
            'sent_at',
            'created_at',
        ]
        read_only_fields = ['id', 'sent_at', 'created_at']