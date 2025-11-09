"""
FILE LOCATION: promotions/serializers.py
"""
from rest_framework import serializers
from .models import PromoCode, PromoUsage, ReferralProgram, Referral, Loyalty

class PromoCodeSerializer(serializers.ModelSerializer):
    is_valid_now = serializers.SerializerMethodField()
    
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'name', 'description', 'discount_type', 'discount_value',
                  'max_discount', 'minimum_fare', 'start_date', 'end_date', 'is_valid_now']
        read_only_fields = fields
    
    def get_is_valid_now(self, obj):
        return obj.is_valid()

class PromoValidationSerializer(serializers.Serializer):
    promo_code = serializers.CharField(max_length=50)
    fare_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class ReferralSerializer(serializers.ModelSerializer):
    referrer_name = serializers.CharField(source='referrer.phone_number', read_only=True)
    referee_name = serializers.CharField(source='referee.phone_number', read_only=True)
    
    class Meta:
        model = Referral
        fields = ['id', 'referral_code', 'referrer_name', 'referee_name', 'status',
                  'referee_rides_completed', 'referred_at']
        read_only_fields = fields

class LoyaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = Loyalty
        fields = ['id', 'total_points', 'available_points', 'tier', 'created_at']
        read_only_fields = fields

