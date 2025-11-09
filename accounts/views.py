from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import random
import string

from .models import User, OTPVerification
from .serializers import (
    UserRegistrationSerializer, 
    OTPVerificationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    LoginSerializer
)
from .utils import SMSService


class OTPRequestThrottle(AnonRateThrottle):
    """Custom throttle for OTP requests - 5 requests per hour"""
    rate = '5/hour'


# Maximum OTP verification attempts before blocking
MAX_OTP_ATTEMPTS = 5
# OTP expiration time in minutes
OTP_EXPIRATION_MINUTES = 10


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def send_otp(request):
    """Send OTP to phone number for verification"""
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response(
            {'error': 'Phone number is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Normalize phone number before processing
    phone_number = User.objects.normalize_phone_number(phone_number)
    
    # Generate 6-digit OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    
    # Delete expired OTP records for this phone number
    OTPVerification.objects.filter(
        phone_number=phone_number,
        expires_at__lt=timezone.now()
    ).delete()
    
    # Check if there's a recent unverified OTP (within last 2 minutes)
    recent_otp = OTPVerification.objects.filter(
        phone_number=phone_number,
        is_verified=False,
        created_at__gte=timezone.now() - timedelta(minutes=2)
    ).first()
    
    if recent_otp:
        return Response({
            'error': 'OTP already sent. Please wait before requesting a new one.',
            'retry_after': 120  # seconds
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Create new OTP record
    otp_record = OTPVerification.objects.create(
        phone_number=phone_number,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRATION_MINUTES)
    )
    
    # Print OTP to terminal for testing (REMOVE IN PRODUCTION)
    print("\n" + "="*60)
    print(f"📱 OTP REQUEST")
    print(f"Phone Number: {phone_number}")
    print(f"OTP Code: {otp_code}")
    print(f"Expires At: {otp_record.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # TODO: In production, integrate with SMS service
    # Example with Africa's Talking:
    # import africastalking
    # africastalking.initialize(username='your_username', api_key='your_api_key')
    # sms = africastalking.SMS
    # response = sms.send(
    #     f"Your SwiftRide verification code is: {otp_code}. Valid for 10 minutes.",
    #     [phone_number]
    # )
    
    return Response({
        'message': 'OTP sent successfully',
        'expires_in': OTP_EXPIRATION_MINUTES * 60  # seconds
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP and create/login user"""
    serializer = OTPVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone_number = serializer.validated_data['phone_number']
    otp_code = serializer.validated_data['otp_code']
    
    # Normalize phone number
    phone_number = User.objects.normalize_phone_number(phone_number)
    
    try:
        otp_record = OTPVerification.objects.get(
            phone_number=phone_number,
            otp_code=otp_code,
            is_verified=False,
        )
        
        # Check if OTP has expired
        if otp_record.is_expired():
            return Response({
                'error': 'OTP has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if max attempts exceeded
        if otp_record.attempts >= MAX_OTP_ATTEMPTS:
            return Response({
                'error': 'Maximum verification attempts exceeded. Please request a new OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        otp_record.is_verified = True
        otp_record.save()
        
        # Get or create user
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'is_phone_verified': True,
                'first_name': request.data.get('first_name', 'User'),
                'last_name': request.data.get('last_name', '')
            }
        )
        
        if not created:
            user.is_phone_verified = True
            user.save(update_fields=['is_phone_verified'])
        
        # Print success to terminal
        print("\n" + "="*60)
        print(f"✅ OTP VERIFICATION SUCCESS")
        print(f"Phone Number: {phone_number}")
        print(f"User: {'Created' if created else 'Existing'}")
        print(f"User ID: {user.id}")
        print("="*60 + "\n")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'OTP verified successfully',
            'user_created': created,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': UserProfileSerializer(user, context={'request': request}).data
        }, status=status.HTTP_200_OK)
        
    except OTPVerification.DoesNotExist:
        # Increment attempts for existing OTP if found
        otp_record = OTPVerification.objects.filter(
            phone_number=phone_number,
            is_verified=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if otp_record:
            otp_record.increment_attempts()
            attempts_left = MAX_OTP_ATTEMPTS - otp_record.attempts
            
            return Response({
                'error': 'Invalid OTP code',
                'attempts_remaining': max(0, attempts_left)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'error': 'Invalid or expired OTP'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def resend_otp(request):
    """Resend OTP to phone number"""
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response(
            {'error': 'Phone number is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Normalize phone number
    phone_number = User.objects.normalize_phone_number(phone_number)
    
    # Invalidate previous OTP
    OTPVerification.objects.filter(
        phone_number=phone_number,
        is_verified=False
    ).update(is_verified=True)  # Mark as used
    
    # Generate new OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    
    otp_record = OTPVerification.objects.create(
        phone_number=phone_number,
        otp_code=otp_code,
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRATION_MINUTES)
    )
    
    # Print OTP to terminal for testing
    print("\n" + "="*60)
    print(f"🔄 OTP RESEND")
    print(f"Phone Number: {phone_number}")
    print(f"OTP Code: {otp_code}")
    print(f"Expires At: {otp_record.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    return Response({
        'message': 'OTP resent successfully',
        'expires_in': OTP_EXPIRATION_MINUTES * 60
    }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveAPIView):
    """Retrieve current user's profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    """Update current user's profile including profile picture upload"""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        """Override update to return full user profile after update"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return updated profile
        instance.refresh_from_db()
        return Response(
            UserProfileSerializer(instance, context={'request': request}).data,
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout endpoint.
    With JWT, consider implementing token blacklist for enhanced security.
    """
    try:
        # Optional: Blacklist the refresh token
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass
    
    return Response({
        'message': 'Logout successful'
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Delete user account permanently.
    WARNING: This action cannot be undone.
    """
    user = request.user
    phone_number = user.phone_number
    
    # Delete associated OTP records
    OTPVerification.objects.filter(phone_number=phone_number).delete()
    
    # Delete user
    user.delete()
    
    return Response({
        'message': 'Account deleted successfully',
        'deleted_phone_number': phone_number
    }, status=status.HTTP_200_OK)