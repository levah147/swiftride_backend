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
        """Validate profile picture"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError('Profile picture file size must not exceed 5MB.')
            
            # Check file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            import os
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f'Invalid file format. Allowed formats: {", ".join(valid_extensions)}'
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