from rest_framework import serializers
from .models import Driver, DriverVerificationDocument, VehicleImage, DriverRating
from accounts.models import User
from vehicles.models import Vehicle
from pricing.models import VehicleType  # VehicleType is in pricing app
from vehicles.serializers import VehicleSerializer
import os
 

class DriverVerificationDocumentSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = DriverVerificationDocument
        fields = [
            'id', 'driver', 'document_type', 'document_type_display',
            'document', 'document_url', 'is_verified', 'notes', 'uploaded_at'
        ]
        read_only_fields = ['id', 'is_verified', 'verified_by', 'verified_date', 'uploaded_at']
    
    def get_document_url(self, obj):
        request = self.context.get('request')
        if obj.document:
            if request is not None:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None
    
    def validate_document(self, value):
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Document file size must not exceed 10MB.')
        return value


class VehicleImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)
    
    class Meta:
        model = VehicleImage
        fields = ['id', 'driver', 'image_type', 'image_type_display', 'image', 'image_url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def validate_image(self, value):
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image file size must not exceed 5MB.')
        
        # Check file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(f'Invalid image format. Allowed formats: {", ".join(valid_extensions)}')
        
        return value


class DriverRatingSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    
    class Meta:
        model = DriverRating
        fields = ['id', 'driver', 'rating', 'comment', 'rider_name', 'created_at']
        read_only_fields = ['id', 'driver', 'rider', 'created_at']


class DriverApplicationSerializer(serializers.ModelSerializer):
    """Serializer for driver application submission - accepts flat vehicle fields"""
    
    # Vehicle fields at the top level (matching Flutter app)
    vehicle_type = serializers.CharField(
        max_length=50, 
        write_only=True,
        help_text="Vehicle type (e.g., sedan, suv, van)"
    )
    vehicle_color = serializers.CharField(
        max_length=50, 
        write_only=True,
        help_text="Vehicle color"
    )
    license_plate = serializers.CharField(
        max_length=20, 
        write_only=True,
        help_text="Vehicle license plate number"
    )
    vehicle_year = serializers.IntegerField(
        required=False, 
        allow_null=True,
        write_only=True,
        help_text="Vehicle year (optional)"
    )
    
    class Meta:
        model = Driver
        fields = [
            'driver_license_number', 
            'driver_license_expiry',
            'vehicle_type',
            'vehicle_color', 
            'license_plate',
            'vehicle_year'
        ]
    
    def validate_driver_license_number(self, value):
        """Check if license number is already registered"""
        if Driver.objects.filter(driver_license_number=value).exists():
            raise serializers.ValidationError('This driver license number is already registered.')
        return value
    
    def validate_license_plate(self, value):
        """Check if license plate is already registered"""
        if Vehicle.objects.filter(license_plate=value).exists():
            raise serializers.ValidationError('This license plate is already registered.')
        return value.upper().strip()
    
    def validate_vehicle_type(self, value):
        """Validate and get VehicleType instance"""
        value_lower = value.lower()
        try:
            vehicle_type = VehicleType.objects.get(name__iexact=value_lower)
            return vehicle_type  # Return the instance
        except VehicleType.DoesNotExist:
            # List available vehicle types
            available_types = list(VehicleType.objects.values_list('name', flat=True))
            raise serializers.ValidationError(
                f'Invalid vehicle type "{value}". Available types: {", ".join(available_types) if available_types else "None configured - please contact support"}'
            )
    
    def create(self, validated_data):
        """Create driver profile and associated vehicle"""
        from django.db import transaction
        from datetime import date, timedelta
        
        # Extract vehicle data
        vehicle_type = validated_data.pop('vehicle_type')  # This is a VehicleType instance
        vehicle_color = validated_data.pop('vehicle_color')
        license_plate = validated_data.pop('license_plate')
        vehicle_year = validated_data.pop('vehicle_year', 2020)
        
        user = self.context['request'].user
        
        try:
            with transaction.atomic():
                # Step 1: Create driver profile first (without vehicle)
                driver = Driver.objects.create(
                    user=user,
                    driver_license_number=validated_data['driver_license_number'],
                    driver_license_expiry=validated_data['driver_license_expiry'],
                    current_vehicle=None,  # Will be set after vehicle creation
                    status='pending',
                    is_available=False,
                    is_online=False
                )
                
                # Step 2: Create vehicle with driver reference
                # Set placeholder dates for registration and insurance
                today = date.today()
                vehicle = Vehicle.objects.create(
                    driver=driver,  # Now we have a driver to reference
                    vehicle_type=vehicle_type,
                    make='To be updated',
                    model='To be updated',
                    year=vehicle_year if vehicle_year else 2020,
                    color=vehicle_color,
                    license_plate=license_plate,
                    registration_number=f'REG-{license_plate}',  # Placeholder
                    registration_expiry=today + timedelta(days=365),  # 1 year from now
                    insurance_company='To be provided',
                    insurance_policy_number=f'INS-{license_plate}',  # Placeholder
                    insurance_expiry=today + timedelta(days=365),  # 1 year from now
                    is_active=False,  # Will be activated after verification
                    is_verified=False,
                    is_primary=True
                )
                
                # Step 3: Update driver with vehicle reference
                driver.current_vehicle = vehicle
                driver.save(update_fields=['current_vehicle'])
                
                return driver
                
        except VehicleType.DoesNotExist:
            raise serializers.ValidationError({
                'vehicle_type': 'Invalid vehicle type. Please contact support.'
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise serializers.ValidationError({
                'error': f'Failed to create driver application: {str(e)}'
            })


class DriverProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing driver profile"""
    
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    profile_picture = serializers.SerializerMethodField()
    verification_documents = DriverVerificationDocumentSerializer(many=True, read_only=True)
    vehicle_images = VehicleImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_vehicle = VehicleSerializer(read_only=True)
    
    class Meta:
        model = Driver
        fields = [
            'id', 'user_id', 'phone_number', 'first_name', 'last_name',
            'profile_picture', 'status', 'status_display',
            'current_vehicle',
            'driver_license_number', 'driver_license_expiry',
            'background_check_passed', 'total_rides', 'rating',
            'verification_documents', 'vehicle_images',
            'rejection_reason', 'approved_date', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'background_check_passed', 'total_rides',
            'rating', 'rejection_reason', 'approved_date', 'created_at'
        ]
    
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.user.profile_picture:
            if request is not None:
                return request.build_absolute_uri(obj.user.profile_picture.url)
            return obj.user.profile_picture.url
        return None


class DriverStatusSerializer(serializers.ModelSerializer):
    """Lightweight serializer for checking driver status"""
    
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_vehicle = VehicleSerializer(read_only=True)
    
    class Meta:
        model = Driver
        fields = ['id', 'phone_number', 'full_name', 'status', 'status_display', 'current_vehicle', 'created_at']
        read_only_fields = fields


class AdminDriverApprovalSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject drivers"""
    
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    documents_verified_count = serializers.SerializerMethodField()
    current_vehicle = VehicleSerializer(read_only=True)
    
    class Meta:
        model = Driver
        fields = [
            'id', 'phone_number', 'full_name', 'status',
            'current_vehicle',
            'driver_license_number', 'background_check_passed',
            'documents_verified_count', 'rejection_reason',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'phone_number', 'full_name', 'documents_verified_count']
    
    def get_documents_verified_count(self, obj):
        return obj.verification_documents.filter(is_verified=True).count()
    
    def validate(self, data):
        status = data.get('status')
        rejection_reason = data.get('rejection_reason')
        
        if status == 'rejected' and not rejection_reason:
            raise serializers.ValidationError({'rejection_reason': 'Rejection reason is required when rejecting an application.'})
        
        return data