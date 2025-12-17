import os
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, OTPVerification


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name']


class OTPVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp = serializers.CharField(max_length=6)  # Changed from otp_code to otp
    
    def to_internal_value(self, data):
        """Convert 'otp' field to 'otp_code' for internal use"""
        internal_data = super().to_internal_value(data)
        if 'otp' in internal_data:
            internal_data['otp_code'] = internal_data.pop('otp')
        return internal_data


class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 
            'email', 'rating', 'total_rides', 'profile_picture',
            'profile_picture_url', 'is_driver', 'created_at'
        ]
        read_only_fields = ['id', 'rating', 'total_rides', 'created_at', 'profile_picture_url']
    
    def get_profile_picture_url(self, obj):
        """
        Return the full URL for the profile picture.
        If profile picture exists, return its URL; otherwise return None
        """
        if obj.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile with image upload"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'profile_picture'
        ]
    
    def validate_profile_picture(self, value):
        """Validate profile picture using settings configuration"""
        if value:
            from django.conf import settings
            
            # Get settings
            pic_settings = getattr(settings, 'PROFILE_PICTURE_SETTINGS', {})
            max_size_mb = pic_settings.get('MAX_FILE_SIZE_MB', 5)
            allowed_formats = pic_settings.get('ALLOWED_FORMATS', [
                'image/jpeg', 'image/png', 'image/jpg', 'image/webp','image/gif'
            ])
            
            # Check file size
            max_size_bytes = max_size_mb * 1024 * 1024
            if value.size > max_size_bytes:
                raise serializers.ValidationError(
                    f'Profile picture file size must not exceed {max_size_mb}MB.'
                )
            
            # Check file type (MIME type)
            if value.content_type not in allowed_formats:
                raise serializers.ValidationError(
                    f'Invalid file format. Allowed formats: JPEG, PNG, WebP'
                )
            
            # Check file extension as well
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f'Invalid file extension. Allowed: {", ".join(valid_extensions)}'
                )
        
        return value


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        
        if phone_number:
            try:
                user = User.objects.get(phone_number=phone_number)
                if not user.is_phone_verified:
                    raise serializers.ValidationError('Phone number not verified.')
            except User.DoesNotExist:
                raise serializers.ValidationError('User with this phone number does not exist.')
        else:
            raise serializers.ValidationError('Phone number is required.')
        
        attrs['user'] = user
        return attrs