"""
FILE LOCATION: backend/promotions/views.py

✅ UPDATED WITH REDEMPTION API
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
from .services import redeem_loyalty_points
import logging

logger = logging.getLogger(__name__)


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
    
    @action(detail=False, methods=['post'])
    def redeem(self, request):
        """
        Redeem loyalty points for wallet credit.
        
        POST /api/promotions/loyalty/redeem/
        {
            "points": 100
        }
        
        Returns:
        {
            "success": true,
            "data": {
                "amount": 10.0,
                "new_available_points": 900,
                "new_total_points": 1000,
                "new_wallet_balance": "5010.00",
                "transaction_id": "TXN123"
            }
        }
        """
        try:
            # Get points from request
            points = request.data.get('points')
            
            if not points:
                return Response({
                    'success': False,
                    'error': 'Points parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate points is integer
            try:
                points = int(points)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'Points must be a valid number'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate positive points
            if points <= 0:
                return Response({
                    'success': False,
                    'error': 'Points must be greater than 0'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Redeem points using service function
            success, message, amount = redeem_loyalty_points(request.user, points)
            
            if not success:
                logger.warning(f"❌ Redemption failed for {request.user.phone_number}: {message}")
                return Response({
                    'success': False,
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get updated loyalty data
            loyalty = Loyalty.objects.get(user=request.user)
            
            # Get updated wallet balance
            from payments.models import Wallet, Transaction
            wallet = Wallet.objects.get(user=request.user)
            
            # Get the transaction that was just created
            transaction = Transaction.objects.filter(
                user=request.user,
                transaction_type='loyalty_redemption',
                amount=amount
            ).order_by('-created_at').first()
            
            logger.info(
                f"✅ Redemption successful for {request.user.phone_number}: "
                f"{points} points → ₦{amount}"
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'amount': float(amount),
                    'points_redeemed': points,
                    'new_available_points': loyalty.available_points,
                    'new_total_points': loyalty.total_points,
                    'new_wallet_balance': str(wallet.balance),
                    'transaction_id': transaction.transaction_id if transaction else None,
                    'tier': loyalty.tier
                }
            }, status=status.HTTP_200_OK)
            
        except Loyalty.DoesNotExist:
            logger.error(f"❌ Loyalty account not found for {request.user.phone_number}")
            return Response({
                'success': False,
                'error': 'Loyalty account not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"❌ Error redeeming points: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to redeem points. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)