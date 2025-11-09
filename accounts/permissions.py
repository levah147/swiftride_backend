
"""
FILE LOCATION: accounts/permissions.py

Custom permissions for accounts app.
"""
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow users to access their own data, or admins to access all data.
    """
    def has_object_permission(self, request, view, obj):
        # Admins can access everything
        if request.user and request.user.is_staff:
            return True
        
        # Users can access their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user


class IsPhoneVerified(permissions.BasePermission):
    """
    Only allow access to users with verified phone numbers.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_phone_verified
        )


class IsDriver(permissions.BasePermission):
    """
    Only allow access to users who are drivers.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_driver
        )


