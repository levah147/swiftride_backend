"""
NEW vehicles app - Manages physical vehicle assets
Separated from pricing configuration
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import os


def vehicle_document_path(instance, filename):
    """Generate file path for vehicle documents"""
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('vehicle_documents', unique_filename)


def vehicle_image_path(instance, filename):
    """Generate file path for vehicle images"""
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('vehicle_images', unique_filename)


class Vehicle(models.Model):
    """
    Physical vehicle registered on the platform.
    Represents actual cars, bikes, keke, SUVs that drivers use.
    """
    
    # Owner/Driver
    driver = models.ForeignKey(
        'drivers.Driver',
        on_delete=models.CASCADE,
        related_name='vehicles',
        help_text="Driver who owns/operates this vehicle"
    )
    
    # Vehicle Category (links to pricing configuration)
    vehicle_type = models.ForeignKey(
        'pricing.VehicleType',
        on_delete=models.PROTECT,
        related_name='registered_vehicles',
        help_text="Category: bike, keke, car, suv"
    )
    
    # Vehicle Details
    make = models.CharField(
        max_length=50,
        help_text="Manufacturer: Toyota, Honda, TVS, etc."
    )
    model = models.CharField(
        max_length=50,
        help_text="Model: Camry, Accord, Keke Napep, etc."
    )
    year = models.IntegerField(
        validators=[
            MinValueValidator(1990),
            MaxValueValidator(timezone.now().year + 1)
        ],
        help_text="Year of manufacture"
    )
    color = models.CharField(max_length=50)
    
    # Registration
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        help_text="Vehicle license plate number"
    )
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Vehicle registration number"
    )
    registration_expiry = models.DateField(
        help_text="Registration expiry date"
    )
    
    # Insurance
    insurance_company = models.CharField(max_length=100)
    insurance_policy_number = models.CharField(max_length=50, unique=True)
    insurance_expiry = models.DateField()
    
    # Inspection
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_due = models.DateField(null=True, blank=True)
    inspection_status = models.CharField(
        max_length=20,
        choices=[
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
            ('overdue', 'Overdue'),
        ],
        default='pending'
    )
    
    # Vehicle Status
    is_active = models.BooleanField(
        default=True,
        help_text="Vehicle is active and can be used"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Vehicle documents verified by admin"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Driver's primary vehicle for rides"
    )
    
    # Operational Data
    total_rides = models.IntegerField(default=0)
    total_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_vehicle'
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['driver', 'is_active']),
            models.Index(fields=['license_plate']),
            models.Index(fields=['is_verified', 'is_active']),
        ]
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
    
    def clean(self):
        """Validate vehicle data"""
        super().clean()
        
        # Uppercase license plate
        if self.license_plate:
            self.license_plate = self.license_plate.upper().strip()
        
        # Validate registration expiry
        if self.registration_expiry and self.registration_expiry <= timezone.now().date():
            raise ValidationError({
                'registration_expiry': 'Registration has expired'
            })
        
        # Validate insurance expiry
        if self.insurance_expiry and self.insurance_expiry <= timezone.now().date():
            raise ValidationError({
                'insurance_expiry': 'Insurance has expired'
            })
        
        # Only one primary vehicle per driver
        if self.is_primary:
            existing_primary = Vehicle.objects.filter(
                driver=self.driver,
                is_primary=True
            ).exclude(pk=self.pk)
            
            if existing_primary.exists():
                # Automatically unset other primary vehicles
                existing_primary.update(is_primary=False)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} - {self.license_plate}"
    
    @property
    def display_name(self):
        """Human-readable vehicle name"""
        return f"{self.color} {self.year} {self.make} {self.model}"
    
    @property
    def registration_expired(self):
        """Check if registration has expired"""
        return self.registration_expiry <= timezone.now().date()
    
    @property
    def insurance_expired(self):
        """Check if insurance has expired"""
        return self.insurance_expiry <= timezone.now().date()
    
    @property
    def inspection_overdue(self):
        """Check if inspection is overdue"""
        if not self.next_inspection_due:
            return False
        return self.next_inspection_due <= timezone.now().date()
    
    @property
    def is_roadworthy(self):
        """Check if vehicle is roadworthy and can be used"""
        return (
            self.is_active and
            self.is_verified and
            not self.registration_expired and
            not self.insurance_expired and
            not self.inspection_overdue
        )


class VehicleDocument(models.Model):
    """Vehicle-related documents"""
    
    DOCUMENT_TYPES = [
        ('registration', 'Vehicle Registration'),
        ('insurance', 'Insurance Certificate'),
        ('inspection', 'Inspection Report'),
        ('roadworthiness', 'Road Worthiness Certificate'),
        ('proof_of_ownership', 'Proof of Ownership'),
    ]
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document = models.FileField(
        upload_to=vehicle_document_path,
        help_text="Upload document (PDF, JPG, PNG)"
    )
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_vehicle_documents'
    )
    verified_date = models.DateTimeField(null=True, blank=True)
    
    # Expiry (for documents that expire)
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Document expiry date (if applicable)"
    )
    
    notes = models.TextField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_document'
        unique_together = ('vehicle', 'document_type')
        ordering = ['-uploaded_at']
        verbose_name = 'Vehicle Document'
        verbose_name_plural = 'Vehicle Documents'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_document_type_display()}"
    
    @property
    def is_expired(self):
        """Check if document has expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date <= timezone.now().date()


class VehicleImage(models.Model):
    """Vehicle photos for verification"""
    
    IMAGE_TYPES = [
        ('front', 'Front View'),
        ('back', 'Back View'),
        ('left_side', 'Left Side'),
        ('right_side', 'Right Side'),
        ('interior', 'Interior'),
        ('dashboard', 'Dashboard'),
        ('license_plate', 'License Plate'),
        ('registration_doc', 'Registration Document Photo'),
    ]
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image_type = models.CharField(max_length=50, choices=IMAGE_TYPES)
    image = models.ImageField(
        upload_to=vehicle_image_path,
        help_text="Vehicle photo (max 5MB)"
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_image'
        unique_together = ('vehicle', 'image_type')
        ordering = ['-uploaded_at']
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_image_type_display()}"


class VehicleInspection(models.Model):
    """Vehicle inspection history"""
    
    INSPECTION_STATUS = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('conditional', 'Conditional Pass'),
    ]
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='inspections'
    )
    
    inspection_date = models.DateField()
    inspector = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicle_inspections'
    )
    
    inspection_status = models.CharField(
        max_length=20,
        choices=INSPECTION_STATUS
    )
    
    # Inspection Checklist
    brakes_ok = models.BooleanField(default=False)
    lights_ok = models.BooleanField(default=False)
    tires_ok = models.BooleanField(default=False)
    engine_ok = models.BooleanField(default=False)
    body_ok = models.BooleanField(default=False)
    interior_ok = models.BooleanField(default=False)
    
    # Mileage at inspection
    mileage_km = models.IntegerField(
        null=True,
        blank=True,
        help_text="Vehicle mileage at inspection"
    )
    
    notes = models.TextField()
    next_inspection_due = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_inspection'
        ordering = ['-inspection_date']
        verbose_name = 'Vehicle Inspection'
        verbose_name_plural = 'Vehicle Inspections'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.inspection_date} - {self.inspection_status}"
    
    def save(self, *args, **kwargs):
        """Update vehicle inspection status"""
        super().save(*args, **kwargs)
        
        # Update vehicle's inspection data
        self.vehicle.last_inspection_date = self.inspection_date
        self.vehicle.next_inspection_due = self.next_inspection_due
        self.vehicle.inspection_status = self.inspection_status
        self.vehicle.save(update_fields=[
            'last_inspection_date',
            'next_inspection_due',
            'inspection_status'
        ])


class VehicleMaintenance(models.Model):
    """Vehicle maintenance records"""
    
    MAINTENANCE_TYPES = [
        ('routine', 'Routine Service'),
        ('repair', 'Repair'),
        ('tire_change', 'Tire Change'),
        ('oil_change', 'Oil Change'),
        ('brake_service', 'Brake Service'),
        ('other', 'Other'),
    ]
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='maintenance_records'
    )
    
    maintenance_type = models.CharField(max_length=50, choices=MAINTENANCE_TYPES)
    description = models.TextField()
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maintenance cost in Naira"
    )
    
    service_provider = models.CharField(
        max_length=100,
        help_text="Mechanic/Service center name"
    )
    
    maintenance_date = models.DateField()
    mileage_km = models.IntegerField(
        null=True,
        blank=True,
        help_text="Vehicle mileage at maintenance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehicles_vehicle_maintenance'
        ordering = ['-maintenance_date']
        verbose_name = 'Maintenance Record'
        verbose_name_plural = 'Maintenance Records'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_maintenance_type_display()} - {self.maintenance_date}"