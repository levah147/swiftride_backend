from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    # Driver Application & Profile
    path('apply/', views.DriverApplicationView.as_view(), name='driver_apply'),
    path('profile/', views.DriverProfileView.as_view(), name='driver_profile'),
    path('status/', views.DriverStatusView.as_view(), name='driver_status'),
    path('documents-status/', views.get_driver_documents_status, name='driver_documents_status'),
    path('toggle-availability/', views.toggle_driver_availability, name='toggle_availability'),
    
    # Document & Image Upload
    path('upload-document/', views.UploadVerificationDocumentView.as_view(), name='upload_document'),
    path('upload-vehicle-image/', views.UploadVehicleImageView.as_view(), name='upload_vehicle_image'),
    
    # Admin Endpoints
    path('admin/list/', views.AdminDriverListView.as_view(), name='admin_driver_list'),
    path('admin/approve/<int:pk>/', views.AdminApproveDriverView.as_view(), name='admin_approve_driver'),
    path('admin/reject/<int:pk>/', views.AdminRejectDriverView.as_view(), name='admin_reject_driver'),
    path('admin/verify-document/<int:pk>/', views.AdminVerifyDocumentView.as_view(), name='admin_verify_document'),
    path('admin/background-check/<int:pk>/', views.admin_run_background_check, name='admin_background_check'),
    
    # Real-time Location Updates
    path('update-location/', views.update_driver_location, name='update_location'),
    path('get-location/', views.get_driver_location, name='get_location'),
   
]