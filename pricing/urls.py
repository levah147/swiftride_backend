from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    # Cities
    path('cities/', views.CityListView.as_view(), name='cities_list'),
    path('detect-city/', views.detect_city, name='detect_city'),
    
    # Vehicles
    # path('types/', views.get_available_vehicles, name='vehicle_types'),
    
    # Vehicles - ✅ FIXED: Changed 'types/' to 'vehicle-types/'
    path('vehicle-types/', views.get_available_vehicles, name='vehicle_types'),  # ✅ MATCH FRONTEND
    
    # Fare calculation
    path('calculate-fare/', views.calculate_fare, name='calculate_fare'),
    path('verify-fare/', views.verify_fare, name='verify_fare'),
    
    # Surge info
    path('surge-info/', views.get_surge_info, name='surge_info'),
]