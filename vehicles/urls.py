from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    path('', views.VehicleListCreateView.as_view(), name='vehicle_list_create'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('<int:vehicle_id>/set-primary/', views.set_primary_vehicle, name='set_primary'),
    path('<int:vehicle_id>/upload-document/', views.upload_vehicle_document, name='upload_document'),
    path('<int:vehicle_id>/upload-image/', views.upload_vehicle_image, name='upload_image'),
]