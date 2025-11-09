
"""
FILE LOCATION: safety/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmergencySOSViewSet, TripShareViewSet, EmergencyContactViewSet

app_name = 'safety'

router = DefaultRouter()
router.register(r'sos', EmergencySOSViewSet, basename='sos')
router.register(r'trip-share', TripShareViewSet, basename='trip-share')
router.register(r'emergency-contacts', EmergencyContactViewSet, basename='emergency-contacts')

urlpatterns = [
    path('', include(router.urls)),
]


