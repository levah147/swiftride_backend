"""
Test script for user creation and driver application
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_user_creation():
    """Test 1: Create a new user via OTP"""
    print("=" * 60)
    print("TEST 1: USER CREATION VIA OTP")
    print("=" * 60)
    
    # Step 1: Send OTP
    print("\n📱 Step 1: Sending OTP to phone number...")
    phone = "08123456789"
    response = requests.post(
        f"{BASE_URL}/api/auth/send-otp/",
        json={
            "phone_number": phone,
            "first_name": "TestDriver",
            "last_name": "Demo"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print("\n⚠️ OTP send failed or rate limited. Check console for OTP code.")
        return None
    
    # Step 2: Get OTP from console (simulated - in real scenario, user would receive SMS)
    print("\n📋 Step 2: Enter the OTP code from the console output:")
    print("(Check the Django server console for the OTP)")
    otp = input("Enter OTP: ").strip()
    
    # Step 3: Verify OTP
    print(f"\n✅ Step 3: Verifying OTP {otp}...")
    response = requests.post(
        f"{BASE_URL}/api/auth/verify-otp/",
        json={
            "phone_number": phone,
            "otp": otp
        }
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ USER CREATED SUCCESSFULLY!")
        access_token = result.get('tokens', {}).get('access')
        print(f"Access Token: {access_token[:50]}...")
        return access_token
    else:
        print("\n❌ OTP verification failed")
        return None


def test_driver_application(access_token):
    """Test 2: Apply to become a driver"""
    print("\n" + "=" * 60)
    print("TEST 2: DRIVER APPLICATION")
    print("=" * 60)
    
    if not access_token:
        print("❌ No access token - cannot apply as driver")
        return
    
    # Apply to become a driver
    print("\n🚗 Submitting driver application...")
    response = requests.post(
        f"{BASE_URL}/api/drivers/apply/",
        json={
            "driver_license_number": "DL12345678",
            "driver_license_expiry": "2026-12-31",
            "vehicle_type": "car",
            "vehicle_color": "Black",
            "license_plate": "ABC-123-XY",
            "vehicle_year": 2020
        },
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\n✅ DRIVER APPLICATION SUBMITTED SUCCESSFULLY!")
        print("Status: Pending approval")
    else:
        print("\n❌ Driver application failed")


if __name__ == "__main__":
    print("\n🚀 SWIFTRIDE API TESTING\n")
    
    # Test 1: User creation
    token = test_user_creation()
    
    # Test 2: Driver application
    if token:
        test_driver_application(token)
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
