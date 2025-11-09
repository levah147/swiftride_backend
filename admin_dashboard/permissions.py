

"""
FILE LOCATION: admin_dashboard/permissions.py

Custom permissions for admin dashboard.

WHAT THIS DOES:
- Controls who can access admin endpoints
- Only staff/superuser can access
"""

from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Only allow superusers (highest level admins)
    
    USAGE:
    class MyView(viewsets.ViewSet):
        permission_classes = [IsSuperAdmin]
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsStaffOrSuperAdmin(permissions.BasePermission):
    """
    Allow staff members or superusers
    
    USAGE:
    For views that any admin can access
    """
    
    def has_permission(self, request, view):
        return request.user and (
            request.user.is_staff or 
            request.user.is_superuser
        )
        
   