
"""
FILE LOCATION: locations/urls.py

URL routing for locations app.
"""
from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # Saved locations
    path('saved/', views.SavedLocationListCreateView.as_view(), name='saved-locations'),
    path('saved/<int:pk>/', views.SavedLocationDetailView.as_view(), name='saved-location-detail'),
    
    # Recent locations
    path('recent/', views.RecentLocationListView.as_view(), name='recent-locations'),
    path('recent/add/', views.add_recent_location, name='add-recent-location'),
    
    # City detection
    path('detect-city/', views.detect_city_from_coordinates, name='detect-city'),
    
    # Driver location tracking
    path('driver/update/', views.update_driver_location_api, name='update-driver-location'),
    path('driver/nearby/', views.get_nearby_drivers_api, name='get-nearby-drivers'),
    
    # Ride tracking
    path('ride/track/', views.track_ride_location_api, name='track-ride-location'),
    path('ride/<int:ride_id>/route/', views.get_ride_route_api, name='get-ride-route'),
]