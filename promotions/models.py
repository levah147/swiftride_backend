"""
FILE LOCATION: promotions/models.py

Promotions and referrals models for SwiftRide.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import random
import string

User = get_user_model()


class PromoCode(models.Model):
    """Promotional discount codes"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    USER_TYPE_CHOICES = [
        ('all', 'All Users'),
        ('new', 'New Users Only'),
        ('existing', 'Existing Users Only'),
    ]
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_per_user = models.IntegerField(default=1)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='all')
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions_promo_code'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def is_valid(self):
        now = timezone.now()
        if not self.is_active or now < self.start_date or now > self.end_date:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True
    
    def calculate_discount(self, fare_amount):
        if self.discount_type == 'percentage':
            discount = (fare_amount * self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        return min(discount, fare_amount)


class PromoUsage(models.Model):
    """Track promo usage"""
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_usages')
    ride = models.OneToOneField('rides.Ride', on_delete=models.CASCADE)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions_promo_usage'


class ReferralProgram(models.Model):
    """Referral program configuration"""
    name = models.CharField(max_length=200)
    referrer_reward = models.DecimalField(max_digits=10, decimal_places=2)
    referee_reward = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_rides = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions_referral_program'
    
    def __str__(self):
        return self.name


class Referral(models.Model):
    """User referrals"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('rewarded', 'Rewarded'),
    ]
    
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE)
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_received')
    referral_code = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    referee_rides_completed = models.IntegerField(default=0)
    referred_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions_referral'
        unique_together = [['referrer', 'referee']]


class Loyalty(models.Model):
    """User loyalty points"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty')
    total_points = models.IntegerField(default=0)
    available_points = models.IntegerField(default=0)
    tier = models.CharField(
        max_length=20,
        choices=[
            ('bronze', 'Bronze'),
            ('silver', 'Silver'),
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
        ],
        default='bronze'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions_loyalty'
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.tier}"