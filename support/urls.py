
"""
FILE LOCATION: support/urls.py

URL routing for support app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupportCategoryViewSet,
    SupportTicketViewSet,
    TicketMessageViewSet,
    FAQViewSet
)

app_name = 'support'

router = DefaultRouter()
router.register(r'categories', SupportCategoryViewSet, basename='category')
router.register(r'tickets', SupportTicketViewSet, basename='ticket')
router.register(r'messages', TicketMessageViewSet, basename='message')
router.register(r'faq', FAQViewSet, basename='faq')

urlpatterns = [
    path('', include(router.urls)),
] 

"""
FILE LOCATION: support/urls.py

URL routing for support app.
"""
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import (
#     SupportCategoryViewSet,
#     SupportTicketViewSet,
#     TicketMessageViewSet,
#     FAQViewSet
# )

# app_name = 'support'

# router = DefaultRouter()
# router.register(r'categories', SupportCategoryViewSet, basename='category')
# router.register(r'tickets', SupportTicketViewSet, basename='ticket')
# router.register(r'messages', TicketMessageViewSet, basename='message')
# router.register(r'faq', FAQViewSet, basename='faq')

# urlpatterns = [
#     path('', include(router.urls)),
# ]