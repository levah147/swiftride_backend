# Security Improvements for SwiftRide

## 🔒 Security Recommendations

This document outlines security improvements needed for the SwiftRide application.

---

## 1. Rate Limiting

### Current Status
- ✅ OTP endpoints have rate limiting (5/hour)
- ❌ Other critical endpoints lack rate limiting

### Recommendations

#### Add Rate Limiting to Ride Creation 
```python
# rides/views.py
from rest_framework.throttling import UserRateThrottle

class RideCreationThrottle(UserRateThrottle):
    rate = '10/minute'  # 10 rides per minute per user

class RideListCreateView(generics.ListCreateAPIView):
    throttle_classes = [RideCreationThrottle]
    # ... rest of the view
```

#### Add Rate Limiting to Payment Endpoints
```python
# payments/views.py
class PaymentThrottle(UserRateThrottle):
    rate = '20/minute'  # 20 payment requests per minute

class WalletViewSet(viewsets.ModelViewSet):
    throttle_classes = [PaymentThrottle]
    # ... rest of the viewset
```

#### Add Rate Limiting to Driver Acceptance
```python
# rides/views.py
class DriverActionThrottle(UserRateThrottle):
    rate = '30/minute'  # 30 actions per minute

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([DriverActionThrottle])
def accept_ride(request, request_id):
    # ... existing code
```

---

## 2. Input Validation

### Current Status
- ✅ Phone number validation
- ⚠️ Missing coordinate validation
- ⚠️ Missing fare amount validation

### Recommendations

#### Add Coordinate Validation
```python
# rides/views.py
from django.core.exceptions import ValidationError

def validate_coordinates(lat, lon):
    """Validate latitude and longitude"""
    if not (-90 <= lat <= 90):
        raise ValidationError('Invalid latitude. Must be between -90 and 90.')
    if not (-180 <= lon <= 180):
        raise ValidationError('Invalid longitude. Must be between -180 and 180.')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_ride(request):
    pickup_lat = float(request.data.get('pickup_latitude'))
    pickup_lon = float(request.data.get('pickup_longitude'))
    dest_lat = float(request.data.get('destination_latitude'))
    dest_lon = float(request.data.get('destination_longitude'))
    
    # Validate coordinates
    validate_coordinates(pickup_lat, pickup_lon)
    validate_coordinates(dest_lat, dest_lon)
    
    # Validate distance (prevent rides that are too short or too long)
    from rides.services import calculate_distance
    distance = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
    
    if distance < 0.5:  # Less than 500 meters
        return Response(
            {'error': 'Pickup and destination are too close. Minimum distance is 500 meters.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if distance > 100:  # More than 100 km
        return Response(
            {'error': 'Distance too far. Maximum distance is 100 km.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # ... rest of the view
```

#### Add Fare Amount Validation
```python
# rides/views.py
from decimal import Decimal

def validate_fare_amount(amount):
    """Validate fare amount"""
    try:
        fare = Decimal(str(amount))
        if fare < 0:
            raise ValidationError('Fare amount cannot be negative.')
        if fare > 100000:  # Maximum fare of ₦100,000
            raise ValidationError('Fare amount exceeds maximum allowed.')
        return fare
    except (ValueError, TypeError):
        raise ValidationError('Invalid fare amount.')
```

---

## 3. API Security

### Current Status
- ✅ JWT authentication
- ✅ Permission classes
- ❌ No API versioning
- ❌ No request signing

### Recommendations

#### Add API Versioning
```python
# swiftride/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/rides/', include('rides.urls')),
    path('api/v1/payments/', include('payments.urls')),
    # ... other apps
]
```

#### Add Request Signing for Critical Endpoints
```python
# payments/views.py
import hmac
import hashlib
from django.conf import settings

def verify_request_signature(request):
    """Verify request signature for payment endpoints"""
    signature = request.META.get('HTTP_X_SIGNATURE')
    if not signature:
        return False
    
    # Create signature from request body
    body = request.body
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):
    if not verify_request_signature(request):
        return Response(
            {'error': 'Invalid request signature'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    # ... rest of the view
```

---

## 4. Data Protection

### Current Status
- ✅ Password hashing (Django default)
- ❌ No encryption for sensitive data
- ❌ No audit logging

### Recommendations

#### Encrypt Sensitive Data
```python
# Use django-cryptography or django-encrypted-model-fields
# Install: pip install django-cryptography

# models.py
from encrypted_model_fields.fields import EncryptedCharField

class User(AbstractUser):
    # Encrypt phone number (if needed for compliance)
    phone_number = EncryptedCharField(max_length=17)
    
    # Encrypt payment card tokens
    # (Already using tokens from payment gateway, but add extra encryption)
```

#### Add Audit Logging
```python
# Create audit_log app
# audit_log/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model', 'object_id']),
        ]

# middleware.py
class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log sensitive actions
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'DELETE']:
            AuditLog.objects.create(
                user=request.user,
                action=request.method,
                model='Ride',  # or get from request
                object_id=0,  # or get from request
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                data={'path': request.path}
            )
        
        return response
```

---

## 5. Error Handling

### Current Status
- ⚠️ Some errors are silently caught
- ⚠️ Error messages may leak sensitive information

### Recommendations

#### Improve Error Handling
```python
# rides/views.py
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_ride(request):
    try:
        # ... ride creation logic
    except ValidationError as e:
        logger.warning(f"Validation error for user {request.user.id}: {str(e)}")
        return Response(
            {'error': 'Invalid ride data. Please check your input.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error creating ride for user {request.user.id}: {str(e)}")
        return Response(
            {'error': 'An error occurred. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

#### Add Error Monitoring
```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False
    )
```

---

## 6. Authentication Security

### Current Status
- ✅ JWT authentication
- ✅ Token rotation
- ✅ Token blacklist
- ⚠️ No 2FA

### Recommendations

#### Add Two-Factor Authentication (2FA)
```python
# accounts/models.py
class User(AbstractUser):
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)

# accounts/views.py
import pyotp

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_2fa(request):
    """Enable 2FA for user"""
    secret = pyotp.random_base32()
    request.user.two_factor_enabled = True
    request.user.two_factor_secret = secret
    request.user.save()
    
    # Generate QR code for authenticator app
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=request.user.phone_number,
        issuer_name='SwiftRide'
    )
    
    return Response({
        'secret': secret,
        'qr_code': generate_qr_code(totp_uri)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_2fa(request):
    """Verify 2FA code"""
    code = request.data.get('code')
    totp = pyotp.TOTP(request.user.two_factor_secret)
    
    if totp.verify(code, valid_window=1):
        return Response({'message': '2FA verified'})
    else:
        return Response(
            {'error': 'Invalid 2FA code'},
            status=status.HTTP_400_BAD_REQUEST
        )
```

---

## 7. Session Security

### Current Status
- ✅ Secure cookies in production
- ✅ HttpOnly cookies
- ⚠️ No session timeout

### Recommendations

#### Add Session Timeout
```python
# settings.py
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

---

## 8. File Upload Security

### Current Status
- ✅ File type validation
- ⚠️ No file size limits enforced in views
- ⚠️ No virus scanning

### Recommendations

#### Add File Size Validation
```python
# drivers/views.py
from django.core.exceptions import ValidationError

def validate_file_size(file):
    """Validate file size"""
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(f'File size exceeds {max_size / 1024 / 1024}MB limit.')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    file = request.FILES.get('document')
    validate_file_size(file)
    # ... rest of the view
```

#### Add Virus Scanning
```python
# Use ClamAV or similar
# Install: pip install pyclamd

import pyclamd

def scan_file(file):
    """Scan file for viruses"""
    cd = pyclamd.ClamdUnixSocket()
    result = cd.scan_stream(file.read())
    if result:
        raise ValidationError('File failed virus scan.')
    file.seek(0)  # Reset file pointer
```

---

## 9. SQL Injection Prevention

### Current Status
- ✅ Using Django ORM (prevents SQL injection)
- ✅ Using parameterized queries

### Recommendations
- ✅ Continue using Django ORM
- ✅ Never use raw SQL with user input
- ✅ Use `extra()` and `raw()` with caution

---

## 10. XSS Prevention

### Current Status
- ✅ Django templates escape by default
- ✅ DRF serializes data safely
- ⚠️ User-generated content not sanitized

### Recommendations

#### Sanitize User Input
```python
# Use bleach to sanitize HTML
# Install: pip install bleach

import bleach

def sanitize_html(html):
    """Sanitize HTML content"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u']
    return bleach.clean(html, tags=allowed_tags, strip=True)

# rides/models.py
class Ride(models.Model):
    cancellation_reason = models.TextField()
    
    def clean(self):
        if self.cancellation_reason:
            self.cancellation_reason = sanitize_html(self.cancellation_reason)
```

---

## Implementation Priority

### Priority 1: Critical (Do Immediately)
1. ✅ Add rate limiting to ride creation
2. ✅ Add coordinate validation
3. ✅ Add fare amount validation
4. ✅ Improve error handling

### Priority 2: Important (Do Soon)
5. ✅ Add API versioning
6. ✅ Add audit logging
7. ✅ Add file size validation
8. ✅ Add error monitoring (Sentry)

### Priority 3: Nice to Have
9. ✅ Add 2FA
10. ✅ Add request signing
11. ✅ Add virus scanning
12. ✅ Add data encryption

---

## Testing Security

### Security Testing Checklist
- [ ] Test rate limiting
- [ ] Test input validation
- [ ] Test authentication
- [ ] Test authorization
- [ ] Test SQL injection prevention
- [ ] Test XSS prevention
- [ ] Test CSRF protection
- [ ] Test file upload security
- [ ] Test session security
- [ ] Test error handling

---

## Resources

- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

---

*Last Updated: $(date)*

