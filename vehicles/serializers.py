from rest_framework import serializers
from .models import Vehicle, VehicleDocument, VehicleImage, VehicleInspection, VehicleMaintenance
import os


class VehicleDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    document_url = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = VehicleDocument
        fields = [
            'id', 'vehicle', 'document_type', 'document_type_display',
            'document', 'document_url', 'is_verified', 'expiry_date',
            'is_expired', 'notes', 'uploaded_at'
        ]
        read_only_fields = ['id', 'is_verified', 'uploaded_at']
    
    def get_document_url(self, obj):
        request = self.context.get('request')
        if obj.document:
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None
    
    def validate_document(self, value):
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Document size must not exceed 10MB')
        return value


class VehicleImageSerializer(serializers.ModelSerializer):
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleImage
        fields = [
            'id', 'vehicle', 'image_type', 'image_type_display',
            'image', 'image_url', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def validate_image(self, value):
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image size must not exceed 5MB')
        
        # Check file type
        valid_extensions = ['.jpg', '.jpeg', '.png']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(f'Invalid format. Allowed: {", ".join(valid_extensions)}')
        
        return value


class VehicleInspectionSerializer(serializers.ModelSerializer):
    inspection_status_display = serializers.CharField(source='get_inspection_status_display', read_only=True)
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    
    class Meta:
        model = VehicleInspection
        fields = [
            'id', 'vehicle', 'inspection_date', 'inspector', 'inspector_name',
            'inspection_status', 'inspection_status_display',
            'brakes_ok', 'lights_ok', 'tires_ok', 'engine_ok',
            'body_ok', 'interior_ok', 'mileage_km', 'notes',
            'next_inspection_due', 'created_at'
        ]
        read_only_fields = ['id', 'inspector', 'created_at']


class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)
    
    class Meta:
        model = VehicleMaintenance
        fields = [
            'id', 'vehicle', 'maintenance_type', 'maintenance_type_display',
            'description', 'cost', 'service_provider',
            'maintenance_date', 'mileage_km', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class VehicleSerializer(serializers.ModelSerializer):
    """Detailed vehicle serializer with all related data"""
    
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    display_name = serializers.ReadOnlyField()
    registration_expired = serializers.ReadOnlyField()
    insurance_expired = serializers.ReadOnlyField()
    inspection_overdue = serializers.ReadOnlyField()
    is_roadworthy = serializers.ReadOnlyField()
    
    documents = VehicleDocumentSerializer(many=True, read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'driver', 'driver_name', 'vehicle_type', 'vehicle_type_name',
            'make', 'model', 'year', 'color', 'display_name',
            'license_plate', 'registration_number', 'registration_expiry',
            'insurance_company', 'insurance_policy_number', 'insurance_expiry',
            'last_inspection_date', 'next_inspection_due', 'inspection_status',
            'is_active', 'is_verified', 'is_primary',
            'registration_expired', 'insurance_expired', 'inspection_overdue',
            'is_roadworthy', 'total_rides', 'total_distance_km',
            'documents', 'images', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'total_rides', 'total_distance_km',
            'created_at', 'updated_at'
        ]


class VehicleCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating vehicles"""
    
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_type', 'make', 'model', 'year', 'color',
            'license_plate', 'registration_number', 'registration_expiry',
            'insurance_company', 'insurance_policy_number', 'insurance_expiry'
        ]
    
    def validate_license_plate(self, value):
        """Check for duplicate license plates"""
        value = value.upper().strip()
        if Vehicle.objects.filter(license_plate=value).exists():
            raise serializers.ValidationError('This license plate is already registered')
        return value
    
    def validate_registration_number(self, value):
        """Check for duplicate registration numbers"""
        if Vehicle.objects.filter(registration_number=value).exists():
            raise serializers.ValidationError('This registration number is already in use')
        return value
    
    def validate_insurance_policy_number(self, value):
        """Check for duplicate insurance policy numbers"""
        if Vehicle.objects.filter(insurance_policy_number=value).exists():
            raise serializers.ValidationError('This insurance policy number is already in use')
        return value


class VehicleListSerializer(serializers.ModelSerializer):
    """Simplified vehicle list serializer"""
    
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    display_name = serializers.ReadOnlyField()
    is_roadworthy = serializers.ReadOnlyField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'vehicle_type', 'vehicle_type_name', 'display_name',
            'license_plate', 'is_primary', 'is_active', 'is_verified',
            'is_roadworthy', 'total_rides'
        ]