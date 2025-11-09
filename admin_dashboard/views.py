"""
FILE LOCATION: admin_dashboard/views.py

===========================================
ADMIN DASHBOARD VIEWS - EXPLAINED
===========================================

WHAT THIS FILE DOES:
- Defines API endpoints for admin operations
- Handles requests from admin frontend
- Returns data in JSON format

ENDPOINTS CREATED:
1. User Management - ban/unban users, view user details
2. Driver Management - approve/reject drivers
3. Statistics - platform overview stats
4. Settings - update platform settings
5. Reports - handle user reports
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum
from django.utils import timezone

from .models import AdminActionLog, PlatformSettings, SystemNotification, UserReport
from .serializers import (
    UserListSerializer,
    UserDetailSerializer,
    BanUserSerializer,
    DriverApprovalSerializer,
    AdminActionLogSerializer,
    PlatformSettingsSerializer,
    PlatformStatsSerializer,
    UserReportSerializer,
    SystemNotificationSerializer,
)

User = get_user_model()


# ==========================================
# USER MANAGEMENT ENDPOINTS
# ==========================================

class UserManagementViewSet(viewsets.ModelViewSet):
    """
    WHAT THIS DOES:
    - Provides endpoints for managing users
    - Admins can view, search, ban, unban users
    
    AVAILABLE ENDPOINTS:
    GET    /api/admin/users/              - List all users
    GET    /api/admin/users/123/          - Get specific user
    POST   /api/admin/users/ban/          - Ban a user
    POST   /api/admin/users/unban/        - Unban a user
    GET    /api/admin/users/search/       - Search users
    """
    
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail"""
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        LIST ALL USERS
        
        ENDPOINT: GET /api/admin/users/
        
        QUERY PARAMETERS:
        - is_driver=true/false - Filter by driver status
        - is_active=true/false - Filter by active status
        - search=text - Search by phone/name
        
        EXAMPLE REQUEST:
        GET /api/admin/users/?is_driver=false&is_active=true
        
        EXAMPLE RESPONSE:
        {
            "success": true,
            "count": 1500,
            "data": [
                {
                    "id": 123,
                    "phone_number": "+2348012345678",
                    "first_name": "John",
                    "is_active": true,
                    ...
                }
            ]
        }
        """
        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by driver status
        is_driver = request.query_params.get('is_driver')
        if is_driver is not None:
            queryset = queryset.filter(is_driver=is_driver.lower() == 'true')
        
        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(phone_number__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def ban(self, request):
        """
        BAN A USER
        
        ENDPOINT: POST /api/admin/users/ban/
        
        REQUEST BODY:
        {
            "user_id": 123,
            "reason": "Spam account"
        }
        
        WHAT IT DOES:
        1. Validates the request
        2. Marks user as inactive
        3. Logs the action
        4. Returns success message
        
        RESPONSE:
        {
            "success": true,
            "message": "User banned successfully"
        }
        """
        serializer = BanUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        reason = serializer.validated_data['reason']
        
        try:
            user = User.objects.get(id=user_id)
            
            # Ban the user
            user.is_active = False
            user.save()
            
            # Log the action
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='user_ban',
                target_type='user',
                target_id=user.id,
                reason=reason
            )
            
            return Response({
                'success': True,
                'message': f'User {user.phone_number} banned successfully'
            })
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def unban(self, request):
        """
        UNBAN A USER
        
        ENDPOINT: POST /api/admin/users/unban/
        
        REQUEST BODY:
        {
            "user_id": 123
        }
        """
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Unban the user
            user.is_active = True
            user.save()
            
            # Log the action
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='user_unban',
                target_type='user',
                target_id=user.id
            )
            
            return Response({
                'success': True,
                'message': f'User {user.phone_number} unbanned successfully'
            })
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# DRIVER MANAGEMENT ENDPOINTS
# ==========================================

class DriverManagementViewSet(viewsets.ViewSet):
    """
    WHAT THIS DOES:
    - Manage driver approvals and suspensions
    
    AVAILABLE ENDPOINTS:
    GET    /api/admin/drivers/pending/      - List pending approvals
    POST   /api/admin/drivers/approve/      - Approve driver
    POST   /api/admin/drivers/reject/       - Reject driver
    POST   /api/admin/drivers/suspend/      - Suspend driver
    """
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        GET PENDING DRIVER APPROVALS
        
        ENDPOINT: GET /api/admin/drivers/pending/
        
        RESPONSE:
        {
            "success": true,
            "count": 15,
            "data": [...]
        }
        """
        from drivers.models import Driver
        
        pending_drivers = Driver.objects.filter(
            verification_status='pending'
        ).select_related('user')
        
        data = []
        for driver in pending_drivers:
            data.append({
                'id': driver.id,
                'user_id': driver.user.id,
                'phone_number': driver.user.phone_number,
                'name': f"{driver.user.first_name} {driver.user.last_name}",
                'license_number': driver.license_number,
                'submitted_at': driver.created_at,
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'data': data
        })
    
    @action(detail=False, methods=['post'])
    def approve(self, request):
        """
        APPROVE A DRIVER
        
        ENDPOINT: POST /api/admin/drivers/approve/
        
        REQUEST BODY:
        {
            "driver_id": 456,
            "notes": "Documents verified"
        }
        """
        from drivers.models import Driver
        
        serializer = DriverApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        driver_id = serializer.validated_data['driver_id']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            driver = Driver.objects.get(id=driver_id)
            
            # Approve the driver
            driver.verification_status = 'verified'
            driver.is_active = True
            driver.save()
            
            # Log action
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='driver_approve',
                target_type='driver',
                target_id=driver.id,
                reason=notes
            )
            
            return Response({
                'success': True,
                'message': 'Driver approved successfully'
            })
            
        except Driver.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Driver not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def reject(self, request):
        """
        REJECT A DRIVER
        
        ENDPOINT: POST /api/admin/drivers/reject/
        
        REQUEST BODY:
        {
            "driver_id": 456,
            "notes": "Invalid license"
        }
        """
        from drivers.models import Driver
        
        serializer = DriverApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        driver_id = serializer.validated_data['driver_id']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            driver = Driver.objects.get(id=driver_id)
            
            # Reject the driver
            driver.verification_status = 'rejected'
            driver.save()
            
            # Log action
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='driver_reject',
                target_type='driver',
                target_id=driver.id,
                reason=notes
            )
            
            return Response({
                'success': True,
                'message': 'Driver rejected'
            })
            
        except Driver.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Driver not found'
            }, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# PLATFORM STATISTICS ENDPOINT
# ==========================================

class PlatformStatsViewSet(viewsets.ViewSet):
    """
    WHAT THIS DOES:
    - Provides platform overview statistics
    - Used in admin dashboard homepage
    
    ENDPOINT:
    GET /api/admin/stats/overview/
    """
    
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        GET PLATFORM OVERVIEW
        
        ENDPOINT: GET /api/admin/stats/overview/
        
        RESPONSE:
        {
            "success": true,
            "data": {
                "total_users": 5000,
                "total_drivers": 500,
                "total_rides": 25000,
                "today_revenue": "175000.00",
                ...
            }
        }
        """
        from rides.models import Ride
        from drivers.models import Driver
        
        today = timezone.now().date()
        
        # Calculate statistics
        stats = {
            # Users
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'new_users_today': User.objects.filter(created_at__date=today).count(),
            
            # Drivers
            'total_drivers': Driver.objects.count(),
            'active_drivers': Driver.objects.filter(is_active=True).count(),
            'pending_driver_approvals': Driver.objects.filter(
                verification_status='pending'
            ).count(),
            
            # Rides
            'total_rides': Ride.objects.count(),
            'active_rides': Ride.objects.filter(
                status__in=['pending', 'accepted', 'started']
            ).count(),
            'today_rides': Ride.objects.filter(created_at__date=today).count(),
            
            # Revenue
            'total_revenue': Ride.objects.filter(
                status='completed'
            ).aggregate(Sum('final_fare'))['final_fare__sum'] or 0,
            
            'today_revenue': Ride.objects.filter(
                status='completed',
                completed_at__date=today
            ).aggregate(Sum('final_fare'))['final_fare__sum'] or 0,
            
            'platform_revenue': 0,  # Calculate platform fees
        }
        
        serializer = PlatformStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


# ==========================================
# ADMIN ACTION LOG ENDPOINT
# ==========================================

class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    WHAT THIS DOES:
    - Shows history of admin actions
    - Provides audit trail
    
    ENDPOINTS:
    GET /api/admin/actions/              - List all actions
    GET /api/admin/actions/123/          - Get specific action
    """
    
    serializer_class = AdminActionLogSerializer
    permission_classes = [IsAdminUser]
    queryset = AdminActionLog.objects.all().select_related('admin')
    
    def list(self, request, *args, **kwargs):
        """
        LIST ADMIN ACTIONS
        
        QUERY PARAMETERS:
        - action_type - Filter by action type
        - admin_id - Filter by admin user
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by action type
        action_type = request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by admin
        admin_id = request.query_params.get('admin_id')
        if admin_id:
            queryset = queryset.filter(admin_id=admin_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


# ==========================================
# PLATFORM SETTINGS ENDPOINT
# ==========================================

class PlatformSettingsViewSet(viewsets.ModelViewSet):
    """
    WHAT THIS DOES:
    - Allows admins to view and update platform settings
    
    ENDPOINTS:
    GET    /api/admin/settings/           - List all settings
    PUT    /api/admin/settings/123/       - Update a setting
    """
    
    serializer_class = PlatformSettingsSerializer
    permission_classes = [IsAdminUser]
    queryset = PlatformSettings.objects.all()
    
    def update(self, request, *args, **kwargs):
        """
        UPDATE A SETTING
        
        REQUEST BODY:
        {
            "value": "600"
        }
        """
        instance = self.get_object()
        old_value = instance.value
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Update the setting
        instance.updated_by = request.user
        self.perform_update(serializer)
        
        # Log the action
        AdminActionLog.objects.create(
            admin=request.user,
            action_type='settings_update',
            target_type='setting',
            target_id=instance.id,
            reason=f"Changed {instance.key} from {old_value} to {instance.value}"
        )
        
        return Response({
            'success': True,
            'message': 'Setting updated successfully',
            'data': serializer.data
        })