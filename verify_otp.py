import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from accounts.views import send_otp, resend_otp
from accounts.models import User

def test_otp_flow():
    print("Testing OTP Flow...")
    factory = APIRequestFactory()
    
    phone_number = "+2348000000002"
    
    # 1. Test Send OTP
    print("\n1. Testing Send OTP:")
    request = factory.post('/api/accounts/auth/send-otp/', {'phone_number': phone_number}, format='json')
    response = send_otp(request)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.data}")
    
    # 2. Test Resend OTP
    print("\n2. Testing Resend OTP:")
    request = factory.post('/api/accounts/auth/resend-otp/', {'phone_number': phone_number}, format='json')
    response = resend_otp(request)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.data}")

if __name__ == "__main__":
    test_otp_flow()
