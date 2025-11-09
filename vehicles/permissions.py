
"""
FILE LOCATION: vehicles/permissions.py
Custom permissions for vehicles app.
"""
from rest_framework import permissions


class IsVehicleOwner(permissions.BasePermission):
    """Allow only vehicle owner (driver) to access"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        if hasattr(request.user, 'driver_profile'):
            return obj.driver == request.user.driver_profile
        
        return False

