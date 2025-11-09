

"""
FILE LOCATION: promotions/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromoCodeViewSet, ReferralViewSet, LoyaltyViewSet

app_name = 'promotions'

router = DefaultRouter()
router.register(r'promos', PromoCodeViewSet, basename='promo')
router.register(r'referrals', ReferralViewSet, basename='referral')
router.register(r'loyalty', LoyaltyViewSet, basename='loyalty')

urlpatterns = [
    path('', include(router.urls)),
]



