from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # OTP & Authentication
    path('send-otp/', views.send_otp, name='send_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),  # NEW
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('logout/', views.logout, name='logout'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', views.UserProfileUpdateView.as_view(), name='user_profile_update'),
    path('delete-account/', views.delete_account, name='delete_account'),
]