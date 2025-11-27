from django.db import models
from django.core.validators import (
    RegexValidator, FileExtensionValidator, 
    MinValueValidator, MaxValueValidator
)
from django.core.exceptions import ValidationError
from accounts.models import User
import os
import uuid
from django.utils import timezone
from datetime import datetime, date


def driver_document_path(instance, filename):
    """Generate file path for driver documents using UUID"""
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}_{instance.document_type}{ext}"
    return os.path.join('driver_documents', unique_filename)


def vehicle_image_path(instance, filename):
    """Generate file path for vehicle images using UUID"""
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}_{instance.image_type}{ext}"
    return os.path.join('vehicle_images', unique_filename)


class Driver(models.Model):
    """Driver profile model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='driver_profile'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    
    # Vehicle Info (Now linked to Vehicle model)
    current_vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_driver',
        help_text="The vehicle currently being driven"
    )
    
    # Driver Information
    driver_license_number = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True
    )
    driver_license_expiry = models.DateField()
    
    # Background Check
    background_check_passed = models.BooleanField(default=False)
    background_check_date = models.DateTimeField(null=True, blank=True)
    background_check_notes = models.TextField(null=True, blank=True)
        
    # Approval Information
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_drivers'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Driver Availability & Status
    is_available = models.BooleanField(
        default=False,
        help_text="Whether driver is currently available for rides"
    )
    is_online = models.BooleanField(
        default=False,
        help_text="Whether driver is currently online"
    )
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_rides = models.IntegerField(default=0)
    completed_rides = models.IntegerField(default=0)
    cancelled_rides = models.IntegerField(default=0)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=5.00,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ]
    )
    total_ratings = models.IntegerField(
        default=0,
        help_text="Total number of ratings received"
    )
    total_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total earnings in Naira"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'drivers_driver'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'is_available']),
            models.Index(fields=['driver_license_number']),
        ]
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'
    
    def clean(self):
        """Validate model data"""
        super().clean()
        
        # Validate license expiry is in the future
        if self.driver_license_expiry:
            expiry = self.driver_license_expiry
            if isinstance(expiry, str):
                try:
                    expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
                except ValueError:
                    pass # Let standard validation handle invalid format
            
            if isinstance(expiry, (datetime, date)) and expiry <= timezone.now().date():
                raise ValidationError({
                    'driver_license_expiry': 'Driver license has expired or expiry date is invalid'
                })
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_status_display()}"
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_suspended(self):
        return self.status == 'suspended'
    
    @property
    def license_expired(self):
        """Check if driver's license has expired"""
        if not self.driver_license_expiry:
            return False
        expiry = self.driver_license_expiry
        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
            except ValueError:
                return True # Treat invalid date as expired/invalid
        return expiry <= timezone.now().date()
    
    @property
    def can_accept_rides(self):
        """Check if driver can accept rides"""
        return (
            self.is_approved and 
            not self.is_suspended and 
            not self.license_expired and
            self.background_check_passed
        )
    
    def update_rating(self):
        """Recalculate average rating from all ratings"""
        from django.db.models import Avg
        avg_rating = self.ratings.aggregate(Avg('rating'))['rating__avg']
        if avg_rating is not None:
            self.rating = round(avg_rating, 2)
            self.total_ratings = self.ratings.count()
            self.save(update_fields=['rating', 'total_ratings', 'updated_at'])
    
    def go_online(self):
        """Mark driver as online"""
        if self.can_accept_rides:
            self.is_online = True
            self.save(update_fields=['is_online', 'updated_at'])
            return True
        return False
    
    def go_offline(self):
        """Mark driver as offline"""
        self.is_online = False
        self.is_available = False
        self.save(update_fields=['is_online', 'is_available', 'updated_at'])


class DriverVerificationDocument(models.Model):
    """Store driver verification documents"""
    
    DOCUMENT_TYPES = [
        ('license', 'Driver License'),
        ('registration', 'Vehicle Registration'),
        ('insurance', 'Insurance Document'),
        ('id_card', 'National ID Card'),
        ('vehicle_inspection', 'Vehicle Inspection Certificate'),
    ]
    
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='verification_documents'
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document = models.FileField(
        upload_to=driver_document_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
            )
        ]
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verified_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(
        null=True, 
        blank=True,
        help_text="Admin notes about document verification"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'drivers_verification_document'
        unique_together = ('driver', 'document_type')
        ordering = ['-uploaded_at']
        verbose_name = 'Verification Document'
        verbose_name_plural = 'Verification Documents'
    
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.get_document_type_display()}"
    
    @property
    def document_url(self):
        """Return full URL for the document"""
        return self.document.url if self.document else None


class VehicleImage(models.Model):
    """Store vehicle images"""
    
    IMAGE_TYPES = [
        ('front', 'Front View'),
        ('back', 'Back View'),
        ('left_side', 'Left Side View'),
        ('right_side', 'Right Side View'),
        ('interior', 'Interior'),
        ('registration', 'Registration Plate'),
        ('dashboard', 'Dashboard'),
    ]
    
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='vehicle_images'
    )
    image_type = models.CharField(max_length=50, choices=IMAGE_TYPES)
    image = models.ImageField(
        upload_to=vehicle_image_path,
        help_text="Vehicle image (max 5MB)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'drivers_vehicle_image'
        unique_together = ('driver', 'image_type')
        ordering = ['-uploaded_at']
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'
    
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.get_image_type_display()}"
    
    @property
    def image_url(self):
        """Return full URL for the image"""
        return self.image.url if self.image else None


class DriverRating(models.Model):
    """Store individual driver ratings from passengers"""
    
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rider = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='given_driver_ratings'
    )
    ride = models.OneToOneField(
        'rides.Ride',  # Forward reference to avoid circular import
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='driver_rating'
    )
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ],
        choices=[(i/2, str(i/2)) for i in range(2, 11)]  # 1.0 to 5.0 in 0.5 steps
    )
    comment = models.TextField(null=True, blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'drivers_rating'
        ordering = ['-created_at']
        verbose_name = 'Driver Rating'
        verbose_name_plural = 'Driver Ratings'
        indexes = [
            models.Index(fields=['driver', '-created_at']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.rating} stars for {self.driver.user.get_full_name()}"