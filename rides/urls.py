from django.urls import path
from . import views

app_name = 'rides'

urlpatterns = [
    # Rider Endpoints
    path('', views.RideListCreateView.as_view(), name='ride-list-create'),
    path('<int:pk>/', views.RideDetailView.as_view(), name='ride-detail'),
    path('upcoming/', views.upcoming_rides, name='upcoming-rides'),
    path('past/', views.past_rides, name='past-rides'),
    path('<int:ride_id>/cancel/', views.cancel_ride, name='cancel-ride'),
    path('<int:ride_id>/rate/', views.rate_ride, name='rate-ride'),
    path('<int:ride_id>/rating/', views.get_ride_rating, name='get-ride-rating'),  # ✅ GET rating
    path('<int:ride_id>/driver-location/', views.get_driver_location, name='get-driver-location'),  # ✅ GET driver location
    path('<int:ride_id>/receipt/', views.get_ride_receipt, name='get-ride-receipt'),  # ✅ GET receipt
    
    # Driver Endpoints
    path('available/', views.available_rides, name='available-rides'),
    path('requests/<int:request_id>/accept/', views.accept_ride, name='accept-ride'),
    path('requests/<int:request_id>/decline/', views.decline_ride, name='decline-ride'),
    path('active/', views.driver_active_rides, name='driver-active-rides'),
    path('<int:ride_id>/start/', views.start_ride, name='start-ride'),
    path('<int:ride_id>/complete/', views.complete_ride, name='complete-ride'),
    path('<int:ride_id>/driver-cancel/', views.driver_cancel_ride, name='driver-cancel-ride'),
    path('<int:ride_id>/rate-rider/', views.driver_rate_rider, name='driver-rate-rider'),
    
    # Location Tracking
    path('<int:ride_id>/update-location/', views.update_location, name='update-location'),
    path('<int:ride_id>/tracking/', views.get_ride_tracking, name='get-ride-tracking'),
    
    # Promotions
    path('promotions/', views.ActivePromotionsView.as_view(), name='active-promotions'),
]

