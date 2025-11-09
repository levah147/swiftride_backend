
"""
FILE LOCATION: payments/permissions.py
"""
from rest_framework import permissions


class IsWalletOwner(permissions.BasePermission):
    """Only wallet owner can access"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class IsDriver(permissions.BasePermission):
    """Only drivers can withdraw"""
    def has_permission(self, request, view):
        return hasattr(request.user, 'driver_profile')



