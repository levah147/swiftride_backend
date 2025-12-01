from decimal import Decimal
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
import os
import uuid
from django.utils.text import slugify


from common_utils import normalize_phone_number



def user_profile_picture_path(instance, filename):
    """
    Generate file path for user profile pictures.
    Format: profile_pictures/{uuid}/{filename}
    Using UUID instead of user.id to avoid None for unsaved users
    """
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('profile_pictures', unique_filename)


class UserManager(BaseUserManager):
    """Custom user manager for phone number authentication."""
        # Then in UserManager:
    def normalize_phone_number(self, phone_number):
        from common_utils import normalize_phone_number
        return normalize_phone_number(phone_number)    
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and return a regular user with a phone number."""
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        # Normalize the phone number
        phone_number = self.normalize_phone_number(phone_number)
        
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Create and return a superuser with a phone number."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_phone_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone_number, password, **extra_fields)
    
    def get_by_natural_key(self, phone_number):
        """
        Override to normalize phone number during authentication.
        This allows login with either 08167791934 or +2348167791934
        """
        phone_number = self.normalize_phone_number(phone_number)
        return self.get(**{self.model.USERNAME_FIELD: phone_number})


class User(AbstractUser):
    """Custom user model using phone number as username."""
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        unique=True,
        help_text="Phone number in international format"
    )
    is_phone_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_rides = models.IntegerField(default=0)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True,
        help_text="User's profile picture"
    )
    is_driver = models.BooleanField(
        default=False,
        help_text="Whether this user is registered as a driver"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Override username requirement
    username = None
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    # Assign the custom manager
    objects = UserManager()
    
    # ==================== USER PROPERTIES ====================
    
    @property
    def wallet_balance(self):
        """Get user's wallet balance"""
        try:
            return self.wallet.balance
        except:
            return Decimal('0.00')
    
    @property
    def total_transactions(self):
        """Get total transaction count"""
        try:
            from payments.models import Transaction
            return Transaction.objects.filter(user=self).count()
        except:
            return 0

    @property
    def total_deposits(self):
        """Get total deposits count"""
        try:
            from payments.models import Transaction
            return Transaction.objects.filter(
                user=self,
                transaction_type='deposit',
                status='completed'
            ).count()
        except:
            return 0

    @property
    def formatted_wallet_balance(self):
        """Get formatted wallet balance"""
        try:
            return self.wallet.formatted_balance
        except:
            return '₦0.00'
    
    # ==================== META CLASS ====================
    
    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Override save to normalize phone number before saving."""
        if self.phone_number:
            self.phone_number = User.objects.normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} - {self.phone_number}"
    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number


class OTPVerification(models.Model):
    """Store OTP verification codes for phone number authentication."""
    
    phone_number = models.CharField(max_length=17, db_index=True)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0, help_text="Number of verification attempts")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'accounts_otp_verification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_verified', 'expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Normalize phone number before saving."""
        if self.phone_number:
            self.phone_number = User.objects.normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if OTP has expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def increment_attempts(self):
        """Increment verification attempts counter."""
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def __str__(self):
        return f"OTP for {self.phone_number} - {'Verified' if self.is_verified else 'Pending'}"