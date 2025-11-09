

"""
FILE LOCATION: admin_dashboard/filters.py
"""
from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(filters.FilterSet):
    """Filter users"""
    phone = filters.CharFilter(field_name='phone_number', lookup_expr='icontains')
    is_driver = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    
    class Meta:
        model = User
        fields = ['phone', 'is_driver', 'is_active']



