#!/usr/bin/env python
"""
FILE LOCATION: test_ride_flow.py (place in project root)

from locations.models import DriverLocation
   from drivers.models import Driver
   from accounts.models import User
   
   # Clear locations
   DriverLocation.objects.all().delete()
   
   # Optional: Clear test users to start fresh
   User.objects.filter(phone_number__in=['+2348100000001', '+2348022005554']).delete()
   
   exit()

COMPLETE RIDE FLOW TEST SCRIPT - FIXED VERSION
===============================================
Simulates the entire ride booking process with proper error handling.

USAGE:
    python test_ride_flow.py

REQUIREMENTS:
    pip install requests colorama
"""
import requests
import json
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Base URL - Change this to your server URL
BASE_URL = "http://localhost:8000"

# Test credentials
RIDER_PHONE = "+2348100000001"
DRIVER_PHONE = "+2348022005554"

# Abuja coordinates (real locations)
LOKOGOMA_COORDS = {
    "latitude": 9.0155,
    "longitude": 7.4474,
    "address": "Lokogoma, Abuja"
}

GUDU_COORDS = {
    "latitude": 9.0000,
    "longitude": 7.4500,
    "address": "Gudu, Abuja"
}


class Colors:
    """Color codes for terminal output"""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    INFO = Fore.CYAN
    WARNING = Fore.YELLOW
    HEADER = Fore.MAGENTA


def print_header(text):
    """Print section header"""
    print(f"\n{Colors.HEADER}{'=' * 80}")
    print(f"{Colors.HEADER}{text.center(80)}")
    print(f"{Colors.HEADER}{'=' * 80}{Style.RESET_ALL}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.SUCCESS}✅ {text}{Style.RESET_ALL}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.ERROR}❌ {text}{Style.RESET_ALL}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.INFO}ℹ️  {text}{Style.RESET_ALL}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Style.RESET_ALL}")


def print_json(data, title="Response"):
    """Pretty print JSON data"""
    print(f"{Colors.INFO}{title}:{Style.RESET_ALL}")
    print(json.dumps(data, indent=2, default=str))


def safe_request(method, url, **kwargs):
    """Make HTTP request with error handling"""
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=10, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, timeout=10, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(url, timeout=10, **kwargs)
        elif method.upper() == 'PATCH':
            response = requests.patch(url, timeout=10, **kwargs)
        else:
            response = requests.request(method, url, timeout=10, **kwargs)
        
        # Debug info
        print_info(f"Status: {response.status_code}")
        
        # Check if HTML error page
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type and response.status_code >= 400:
            print_error("Received HTML error page instead of JSON")
            print_error("Server response (first 500 chars):")
            print(response.text[:500])
            return None
        
        return response
        
    except requests.exceptions.ConnectionError:
        print_error("Connection refused. Is Django server running?")
        print_info("Start server with: python manage.py runserver")
        return None
    except requests.exceptions.Timeout:
        print_error("Request timed out")
        return None
    except Exception as e:
        print_error(f"Request error: {str(e)}")
        return None


# ============================================================================
# STEP 1: RIDER REGISTRATION & LOGIN
# ============================================================================

def register_and_login_rider():
    """Register and login as rider"""
    print_header("STEP 1: RIDER REGISTRATION & LOGIN")
    
    # Send OTP (FIXED URL)
    print_info(f"Sending OTP to rider: {RIDER_PHONE}")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/auth/send-otp/",  # ✅ FIXED: Changed from /api/accounts/
        json={"phone_number": RIDER_PHONE}
    )
    
    if not response or response.status_code != 200:
        if response:
            print_error(f"Failed to send OTP: {response.text}")
        return None
    
    print_success("OTP sent successfully")
    
    # Get OTP from user
    otp = input(f"{Colors.WARNING}Enter OTP from console/SMS: {Style.RESET_ALL}")
    
    # Verify OTP and register (FIXED URL)
    print_info("Verifying OTP and registering...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/auth/verify-otp/",  # ✅ FIXED
        json={
            "phone_number": RIDER_PHONE,
            "otp": otp,
            "first_name": "John",
            "last_name": "Rider"
        }
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                print_error(f"OTP verification failed: {response.json()}")
            except:
                print_error(f"OTP verification failed: {response.text}")
        return None
    
    data = response.json()
    print_success("Rider registered and logged in")
    rider_token = data['tokens']['access']
    print_info(f"Rider Token: {rider_token[:50]}...")
    return rider_token


# ============================================================================
# STEP 2: DRIVER REGISTRATION & APPROVAL
# ============================================================================

def register_and_setup_driver():
    """Register driver, create vehicle, and approve"""
    print_header("STEP 2: DRIVER REGISTRATION & SETUP")
    
    # Send OTP for driver (FIXED URL)
    print_info(f"Sending OTP to driver: {DRIVER_PHONE}")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/auth/send-otp/",  # ✅ FIXED
        json={"phone_number": DRIVER_PHONE}
    )
    
    if not response or response.status_code != 200:
        if response:
            print_error(f"Failed to send driver OTP: {response.text}")
        return None
    
    print_success("Driver OTP sent")
    otp = input(f"{Colors.WARNING}Enter driver OTP: {Style.RESET_ALL}")
    
    # Verify OTP and register driver (FIXED URL)
    print_info("Verifying OTP and registering driver...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/auth/verify-otp/",  # ✅ FIXED
        json={
            "phone_number": DRIVER_PHONE,
            "otp": otp,
            "first_name": "Mike",
            "last_name": "Driver"
        }
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                print_error(f"Driver registration failed: {response.json()}")
            except:
                print_error(f"Driver registration failed: {response.text}")
        return None
    
    driver_token = response.json()['tokens']['access']
    print_success("Driver registered and logged in")
    
    # Apply to become a driver
    print_info("Submitting driver application...")
    tomorrow = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/drivers/apply/",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={
            "driver_license_number": "ABJ123456789",
            "driver_license_expiry": tomorrow,
            "vehicle_type": "car",
            "vehicle_color": "Blue",
            "license_plate": "ABC-123-XY",
            "vehicle_year": 2020
        }
    )
    
    if not response or response.status_code != 201:
        if response:
            try:
                print_error(f"Driver application failed: {response.json()}")
            except:
                print_error(f"Driver application failed: {response.text}")
        return None
    
    print_success("Driver application submitted")
    driver_id = response.json()['driver']['id']
    
    # Manual approval instructions
    print_warning("Driver needs manual approval via Django admin")
    print_info("Instructions:")
    print("   1. Go to http://localhost:8000/admin/drivers/driver/")
    print(f"   2. Find driver with phone {DRIVER_PHONE}")
    print("   3. Set status to 'approved'")
    print("   4. Set background_check_passed to True")
    print("   5. Save")
    
    input(f"\n{Colors.WARNING}Press Enter after approving driver in admin...{Style.RESET_ALL}")
    
    return driver_token, driver_id


# ============================================================================
# STEP 3: DRIVER GOES ONLINE
# ============================================================================

def driver_goes_online(driver_token):
    """Driver sets status to online and updates location"""
    print_header("STEP 3: DRIVER GOES ONLINE")
    
    # Toggle availability to online
    print_info("Driver going online...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/drivers/toggle-availability/",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={"action": "online"}
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                print_error(f"Failed to go online: {response.json()}")
            except:
                print_error(f"Failed to go online: {response.text}")
        return False
    
    print_success("Driver is now ONLINE")
    
    # Update driver location (near Lokogoma)
    print_info("Updating driver location...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/drivers/update-location/",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={
            "latitude": 9.0180,
            "longitude": 7.4490,
            "heading": 180,
            "speed": 0,
            "accuracy": 10
        }
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                print_error(f"Failed to update location: {response.json()}")
            except:
                print_error(f"Failed to update location: {response.text}")
        return False
    
    print_success("Driver location updated (near Lokogoma)")
    return True


# ============================================================================
# STEP 4: CALCULATE FARE
# ============================================================================

def calculate_fare(rider_token, vehicle_type="car"):
    """Calculate fare for the ride"""
    print_header(f"STEP 4: CALCULATE FARE ({vehicle_type.upper()})")
    
    print_info(f"Calculating fare from Lokogoma to Gudu ({vehicle_type})...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/pricing/calculate-fare/",
        headers={"Authorization": f"Bearer {rider_token}"},
        json={
            "vehicle_type": vehicle_type,
            "pickup_latitude": LOKOGOMA_COORDS["latitude"],
            "pickup_longitude": LOKOGOMA_COORDS["longitude"],
            "destination_latitude": GUDU_COORDS["latitude"],
            "destination_longitude": GUDU_COORDS["longitude"],
            "city_name": "Abuja"
        }
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                print_error(f"Fare calculation failed: {response.json()}")
            except:
                print_error(f"Fare calculation failed: {response.text}")
        return None
    
    fare_data = response.json()
    print_success("Fare calculated successfully")
    print_json(fare_data, "Fare Breakdown")
    return fare_data


# ============================================================================
# STEP 5: BOOK RIDE
# ============================================================================

def book_ride(rider_token, fare_data):
    """Book a ride using fare hash"""
    print_header("STEP 5: BOOK RIDE")
    
    print_info("Creating ride request...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/",
        headers={"Authorization": f"Bearer {rider_token}"},
        json={
            "pickup_location": LOKOGOMA_COORDS["address"],
            "pickup_latitude": LOKOGOMA_COORDS["latitude"],
            "pickup_longitude": LOKOGOMA_COORDS["longitude"],
            "destination_location": GUDU_COORDS["address"],
            "destination_latitude": GUDU_COORDS["latitude"],
            "destination_longitude": GUDU_COORDS["longitude"],
            "ride_type": "immediate",
            "fare_hash": fare_data['fare_hash']
        }
    )
    
    if not response or response.status_code != 201:
        if response:
            try:
                print_error(f"Ride booking failed: {response.json()}")
            except:
                print_error(f"Ride booking failed: {response.text}")
        return None
    
    ride = response.json()
    print_success(f"Ride booked successfully! Ride ID: {ride['id']}")
    print_info(f"Status: {ride['status']}")
    print_info(f"Fare: ₦{ride['fare_amount']}")
    return ride['id']


# ============================================================================
# Continue with remaining steps...
# (The rest of the functions remain the same, just use safe_request)
# ============================================================================

def check_available_rides(driver_token):
    """Driver checks for available ride requests"""
    print_header("STEP 6: DRIVER CHECKS AVAILABLE RIDES")
    
    print_info("Fetching available rides...")
    response = safe_request(
        'GET',
        f"{BASE_URL}/api/rides/available/",
        headers={"Authorization": f"Bearer {driver_token}"},
        params={
            "latitude": 9.0180,
            "longitude": 7.4490,
            "max_distance": 10
        }
    )
    
    if not response or response.status_code != 200:
        return None
    
    rides = response.json()
    if rides:
        print_success(f"Found {len(rides)} available ride(s)")
        for ride in rides:
            print_json(ride, f"Ride Request #{ride['id']}")
        return rides[0]['id'] if rides else None
    else:
        print_warning("No available rides found")
        return None


def accept_ride(driver_token, request_id):
    """Driver accepts the ride request"""
    print_header("STEP 7: DRIVER ACCEPTS RIDE")
    
    print_info(f"Accepting ride request #{request_id}...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/requests/{request_id}/accept/",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    
    if not response or response.status_code != 200:
        if response:
            try:
                error_data = response.json()
                print_error(f"Failed to accept ride:")
                print_json(error_data)  # ✅ Print full error with details
            except:
                print_error(f"Failed to accept ride: {response.text}")
        return None
    
    # if not response or response.status_code != 200:
    #     if response:
    #         try:
    #             print_error(f"Failed to accept ride: {response.json()}")
    #         except:
    #             print_error(f"Failed to accept ride: {response.text}")
    #     return None
    
    data = response.json()
    print_success("Ride accepted successfully!")
    print_json(data, "Accepted Ride")
    return data['ride']['id']


def simulate_driver_approaching(driver_token, ride_id):
    """Simulate driver driving to pickup location"""
    print_header("STEP 8: DRIVER APPROACHING PICKUP")
    
    waypoints = [
        (9.0180, 7.4490, "Starting location"),
        (9.0170, 7.4480, "0.5km away"),
        (9.0160, 7.4475, "0.3km away"),
        (9.0155, 7.4474, "Arrived at pickup")
    ]
    
    for lat, lng, status in waypoints:
        print_info(f"{status} - Updating location...")
        
        response = safe_request(
            'POST',
            f"{BASE_URL}/api/drivers/update-location/",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={
                "latitude": lat,
                "longitude": lng,
                "heading": 180,
                "speed": 30
            }
        )
        
        if response and response.status_code == 200:
            print_success(f"Location updated: ({lat}, {lng})")
        else:
            print_warning("Location update failed")
        
        time.sleep(2)
    
    print_success("Driver arrived at pickup location!")


def start_ride(driver_token, ride_id):
    """Driver starts the ride"""
    print_header("STEP 9: START RIDE")
    
    print_info("Starting ride (passenger picked up)...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/{ride_id}/start/",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    
    if not response or response.status_code != 200:
        return False
    
    print_success("Ride started successfully!")
    print_json(response.json(), "Ride Status")
    return True


def simulate_ride_to_destination(driver_token, ride_id):
    """Simulate driving to destination"""
    print_header("STEP 10: DRIVING TO DESTINATION")
    
    waypoints = [
        (9.0150, 7.4474, "Leaving Lokogoma"),
        (9.0120, 7.4485, "Passing through Apo"),
        (9.0080, 7.4495, "Approaching Gudu"),
        (9.0000, 7.4500, "Arrived at Gudu")
    ]
    
    for lat, lng, status in waypoints:
        print_info(f"{status}...")
        safe_request(
            'POST',
            f"{BASE_URL}/api/drivers/update-location/",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"latitude": lat, "longitude": lng, "heading": 180, "speed": 40}
        )
        time.sleep(2)
    
    print_success("Arrived at destination!")


def complete_ride(driver_token, ride_id):
    """Driver completes the ride"""
    print_header("STEP 11: COMPLETE RIDE")
    
    print_info("Completing ride...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/{ride_id}/complete/",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={
            "end_latitude": GUDU_COORDS["latitude"],
            "end_longitude": GUDU_COORDS["longitude"]
        }
    )
    
    if not response or response.status_code != 200:
        return False
    
    print_success("Ride completed successfully!")
    print_json(response.json(), "Completed Ride")
    return True


def rate_ride_mutual(rider_token, driver_token, ride_id):
    """Both parties rate each other"""
    print_header("STEP 12: MUTUAL RATING")
    
    # Rider rates driver
    print_info("Rider rating driver...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/{ride_id}/rate/",
        headers={"Authorization": f"Bearer {rider_token}"},
        json={"rating": 5, "comment": "Great driver!"}
    )
    
    if response and response.status_code == 200:
        print_success("Rider rated driver: ⭐⭐⭐⭐⭐")
    
    # Driver rates rider
    print_info("Driver rating rider...")
    response = safe_request(
        'POST',
        f"{BASE_URL}/api/rides/{ride_id}/rate-rider/",
        headers={"Authorization": f"Bearer {driver_token}"},
        json={"rating": 5, "comment": "Excellent passenger!"}
    )
    
    if response and response.status_code == 200:
        print_success("Driver rated rider: ⭐⭐⭐⭐⭐")


# ============================================================================
# MAIN TEST FLOW
# ============================================================================

def main():
    """Main test execution"""
    print_header("🚗 SWIFTRIDE COMPLETE RIDE FLOW TEST 🚗")
    
    try:
        # Step 1: Rider Registration
        rider_token = register_and_login_rider()
        if not rider_token:
            print_error("Rider registration failed. Exiting.")
            return
        
        # Step 2: Driver Registration
        driver_result = register_and_setup_driver()
        if not driver_result:
            print_error("Driver registration failed. Exiting.")
            return
        
        driver_token, driver_id = driver_result
        
        # Step 3: Driver Goes Online
        if not driver_goes_online(driver_token):
            print_error("Driver failed to go online. Exiting.")
            return
        
        # Step 4: Calculate Fare
        fare_data = calculate_fare(rider_token, vehicle_type="car")
        if not fare_data:
            print_error("Fare calculation failed. Exiting.")
            return
        
        # Step 5: Book Ride
        ride_id = book_ride(rider_token, fare_data)
        if not ride_id:
            print_error("Ride booking failed. Exiting.")
            return
        
        time.sleep(3)
        
        # Steps 6-12: Continue ride flow
        request_id = check_available_rides(driver_token)
        if not request_id:
            print_error("No available rides. Exiting.")
            return
        
        accepted_ride_id = accept_ride(driver_token, request_id)
        if not accepted_ride_id:
            print_error("Ride acceptance failed. Exiting.")
            return
        
        simulate_driver_approaching(driver_token, accepted_ride_id)
        
        if not start_ride(driver_token, accepted_ride_id):
            print_error("Failed to start ride. Exiting.")
            return
        
        simulate_ride_to_destination(driver_token, accepted_ride_id)
        
        if not complete_ride(driver_token, accepted_ride_id):
            print_error("Failed to complete ride. Exiting.")
            return
        
        rate_ride_mutual(rider_token, driver_token, accepted_ride_id)
        
        # Success
        print_header("🎉 TEST COMPLETED SUCCESSFULLY 🎉")
        print_success("Full ride flow executed!")
        print_info(f"Ride ID: {accepted_ride_id}")
        print_info(f"Route: Lokogoma → Gudu (Abuja)")
        print_info(f"Fare: ₦{fare_data['total_fare']}")
        
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()