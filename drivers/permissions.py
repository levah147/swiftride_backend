

"""
FILE LOCATION: drivers/permissions.py

Custom permissions for drivers app.
"""
from rest_framework import permissions


class IsDriver(permissions.BasePermission):
    """
    Allow only users who are registered drivers.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'driver_profile')
        )


class IsApprovedDriver(permissions.BasePermission):
    """
    Allow only approved drivers who can accept rides.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'driver_profile'):
            return False
        
        driver = request.user.driver_profile
        return driver.can_accept_rides


class IsDriverOwner(permissions.BasePermission):
    """
    Allow drivers to access their own data.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user and request.user.is_staff:
            return True
        
        # Driver can access their own data
        if hasattr(obj, 'driver'):
            return obj.driver.user == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user.driver_profile


