
"""
FILE LOCATION: pricing/permissions.py
Custom permissions for pricing app.
"""
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow read-only access to all, write access to admins only"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff




