
"""
FILE LOCATION: promotions/views.py
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import PromoCode, Referral, Loyalty
from .serializers import (
    PromoCodeSerializer, PromoValidationSerializer,
    ReferralSerializer, LoyaltySerializer
)

class PromoCodeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated]
    queryset = PromoCode.objects.filter(is_active=True)
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate promo code"""
        serializer = PromoValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['promo_code']
        fare = serializer.validated_data['fare_amount']
        
        try:
            promo = PromoCode.objects.get(code=code.upper())
        except PromoCode.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid promo code'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not promo.is_valid():
            return Response({
                'success': False,
                'error': 'Promo code has expired or reached usage limit'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if fare < promo.minimum_fare:
            return Response({
                'success': False,
                'error': f'Minimum fare is ₦{promo.minimum_fare}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        discount = promo.calculate_discount(fare)
        
        return Response({
            'success': True,
            'data': {
                'code': promo.code,
                'discount_amount': discount,
                'final_fare': fare - discount
            }
        })

class ReferralViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_code(self, request):
        """Get user's referral code"""
        # Get or create referral code
        code = f"REF{request.user.phone_number[-6:]}"
        
        return Response({
            'success': True,
            'data': {
                'referral_code': code,
                'referrals_count': self.get_queryset().count()
            }
        })

class LoyaltyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_points(self, request):
        """Get user's loyalty points"""
        loyalty, _ = Loyalty.objects.get_or_create(user=request.user)
        serializer = LoyaltySerializer(loyalty)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


