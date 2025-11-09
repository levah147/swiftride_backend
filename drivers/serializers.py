from rest_framework import serializers
from .models import Driver, DriverVerificationDocument, VehicleImage, DriverRating
from accounts.models import User
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
    """Serializer for driver application submission"""
    
    class Meta:
        model = Driver
        fields = [
            'vehicle_type', 'vehicle_color', 'license_plate', 'vehicle_year',
            'driver_license_number', 'driver_license_expiry'
        ]
    
    def validate_license_plate(self, value):
        if Driver.objects.filter(license_plate=value).exists():
            raise serializers.ValidationError('This license plate is already registered.')
        return value
    
    def validate_driver_license_number(self, value):
        if Driver.objects.filter(driver_license_number=value).exists():
            raise serializers.ValidationError('This driver license number is already registered.')
        return value


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
    
    class Meta:
        model = Driver
        fields = [
            'id', 'user_id', 'phone_number', 'first_name', 'last_name',
            'profile_picture', 'status', 'status_display',
            'vehicle_type', 'vehicle_color', 'license_plate', 'vehicle_year',
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
    
    class Meta:
        model = Driver
        fields = ['id', 'phone_number', 'full_name', 'status', 'status_display', 'created_at']
        read_only_fields = fields


class AdminDriverApprovalSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject drivers"""
    
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    documents_verified_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Driver
        fields = [
            'id', 'phone_number', 'full_name', 'status',
            'vehicle_type', 'vehicle_color', 'license_plate',
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