"""
FILE LOCATION: swiftride/urls.py

✅ FIXED VERSION - Main URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Customize admin site
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
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