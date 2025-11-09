


"""
FILE LOCATION: rides/permissions.py

Custom permissions for rides app.
"""
from rest_framework import permissions


class IsRideOwner(permissions.BasePermission):
    """
    Allow riders to access their own rides.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user and request.user.is_staff:
            return True
        
        # Rider can access their own rides
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsRideDriver(permissions.BasePermission):
    """
    Allow assigned driver to access the ride.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user and request.user.is_staff:
            return True
        
        # Driver can access rides they're assigned to
        if hasattr(obj, 'driver') and obj.driver:
            return obj.driver.user == request.user
        
        return False


class IsRideParticipant(permissions.BasePermission):
    """
    Allow both rider and driver to access the ride.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user and request.user.is_staff:
            return True
        
        # Rider can access
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Driver can access
        if hasattr(obj, 'driver') and obj.driver and obj.driver.user == request.user:
            return True
        
        return False


class CanRateRide(permissions.BasePermission):
    """
    Allow rating only if ride is completed and user is participant.
    """
    def has_object_permission(self, request, view, obj):
        # Ride must be completed
        if obj.status != 'completed':
            return False
        
        # Must be rider or driver
        is_rider = obj.user == request.user
        is_driver = obj.driver and obj.driver.user == request.user
        
        return is_rider or is_driver



