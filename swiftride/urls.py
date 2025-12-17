"""
FILE LOCATION: swiftride/urls.py

✅ FIXED VERSION - URL configuration for swiftride project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI documentation setup
schema_view = get_schema_view(
    openapi.Info(
        title="SwiftRide API",
        default_version='v1',
        description="""
        SwiftRide Ride-Hailing Platform API Documentation
        
        ## Authentication
        Most endpoints require JWT authentication. Include the token in the header:
        ```
        Authorization: Bearer <your_access_token>
        ```
        
        ## Getting Started
        1. Send OTP: POST /api/accounts/send-otp/
        2. Verify OTP: POST /api/accounts/verify-otp/
        3. Use the returned access token for authenticated requests
        
        ## Apps
        - **Accounts**: User authentication and profile management
        - **Payments**: Wallet, deposits, withdrawals, transactions
        - **Rides**: Ride booking and management
        - **Drivers**: Driver profiles and vehicle management
        - **Notifications**: Push notifications and preferences
        """,
        terms_of_service="https://swiftride.com/terms/",
        contact=openapi.Contact(email="support@swiftride.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

# Customize admin site
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation (Swagger/OpenAPI)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # Core Apps (in dependency order)
    path('api/auth/', include('accounts.urls')),              # 1. Authentication
    path('api/drivers/', include('drivers.urls')),            # 2. Driver management
    path('api/vehicles/', include('vehicles.urls')),          # 3. Vehicle management
    path('api/pricing/', include('pricing.urls')),            # 4. Pricing/fares
    path('api/locations/', include('locations.urls')),        # 5. Location services
    path('api/rides/', include('rides.urls')),                # 6. Ride booking/management
    path('api/payments/', include('payments.urls')),          # 7. Payment processing
    
    # Support Apps
    path('api/notifications/', include('notifications.urls')),  # 8. Push notifications
    path('api/chat/', include('chat.urls')),                   # 9. Real-time chat
    path('api/support/', include('support.urls')),             # 10. Customer support
    
    # Advanced Features
    path('api/analytics/', include('analytics.urls')),         # 11. Analytics & reports
    path('api/promotions/', include('promotions.urls')),       # 12. Promos & referrals
    path('api/safety/', include('safety.urls')),               # 13. Safety features
    
    # Admin Dashboard
    path('api/admin-dashboard/', include('admin_dashboard.urls')),  # 14. Admin API (⚠️ FIXED)
    
    # Audit Logging (Admin only)
    path('api/audit/', include('audit_logging.urls')),  # 15. Audit logs & security events
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)