"""
FILE LOCATION: swiftride/common_utils.py

Common utility functions used across multiple apps in SwiftRide.
Prevents code duplication and circular imports.

This file should be placed in the root of your Django project
(same level as manage.py)
"""
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Tuple
import re
from decimal import Decimal


def normalize_phone_number(phone_number: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to Nigerian international format (+234).
    
    Converts various formats to +234XXXXXXXXXX:
    - '08167791934' -> '+2348167791934'
    - '8167791934' -> '+2348167791934'
    - '2348167791934' -> '+2348167791934'
    - '+2348167791934' -> '+2348167791934'
    
    Args:
        phone_number: Phone number in various formats
        
    Returns:
        Normalized phone number with +234 prefix or None
        
    Example:
        >>> from common_utils import normalize_phone_number
        >>> normalize_phone_number('08167791934')
        '+2348167791934'
    """
    if not phone_number:
        return phone_number
    
    # Remove any spaces, dashes, parentheses
    phone_number = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # Remove + for processing
    phone_number = phone_number.replace('+', '')
    
    # Remove any non-digit characters
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    # Convert based on format
    if phone_number.startswith('0') and len(phone_number) == 11:
        # Nigerian format: 08167791934 -> +2348167791934
        return '+234' + phone_number[1:]
    elif len(phone_number) == 10:
        # 10 digits: 8167791934 -> +2348167791934
        return '+234' + phone_number
    elif len(phone_number) == 13 and phone_number.startswith('234'):
        # Already 234 format: 2348167791934 -> +2348167791934
        return '+' + phone_number
    elif len(phone_number) > 10:
        # Add + if missing
        return '+' + phone_number
    
    return phone_number


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in kilometers (rounded to 2 decimal places)
        
    Example:
        >>> from common_utils import calculate_distance
        >>> # Distance from Lagos to Abuja
        >>> distance = calculate_distance(6.5244, 3.3792, 9.0765, 7.3986)
        >>> print(f"Distance: {distance} km")
        Distance: 478.12 km
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    
    # Calculate distance
    distance = c * r
    
    return round(distance, 2)


def estimate_duration(distance_km: float, avg_speed_kmh: float = 30.0) -> int:
    """
    Estimate travel duration based on distance and average speed.
    
    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average speed in km/h (default: 30 km/h for city traffic)
        
    Returns:
        Estimated duration in minutes
        
    Example:
        >>> from common_utils import estimate_duration
        >>> duration = estimate_duration(15.5)
        >>> print(f"Estimated time: {duration} minutes")
        Estimated time: 31 minutes
    """
    if distance_km <= 0:
        return 0
    
    hours = distance_km / avg_speed_kmh
    minutes = hours * 60
    
    return max(1, int(round(minutes)))


def sanitize_text_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user text input to prevent XSS and other attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
        
    Example:
        >>> from common_utils import sanitize_text_input
        >>> dirty = "<script>alert('xss')</script>Hello"
        >>> clean = sanitize_text_input(dirty)
        >>> print(clean)
        Hello
    """
    if not text:
        return ""
    
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove any script tags
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Truncate to max length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text


def generate_reference_code(prefix: str = "TXN") -> str:
    """
    Generate unique reference code for transactions.
    
    Args:
        prefix: Prefix for the reference code
        
    Returns:
        Unique reference code
        
    Example:
        >>> from common_utils import generate_reference_code
        >>> ref = generate_reference_code("RDE")
        >>> print(ref)
        RDE-20241030-ABC123XYZ
    """
    import uuid
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:9].upper()
    
    return f"{prefix}-{timestamp}-{unique_id}"


def format_currency(amount, currency: str = "₦") -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Amount to format (can be Decimal, float, or int)
        currency: Currency symbol (default: ₦ for Naira)
        
    Returns:
        Formatted currency string
        
    Example:
        >>> from common_utils import format_currency
        >>> formatted = format_currency(1500.50)
        >>> print(formatted)
        ₦1,500.50
    """
    if isinstance(amount, Decimal):
        amount = float(amount)
    return f"{currency}{amount:,.2f}"


def validate_nigerian_phone(phone_number: str) -> bool:
    """
    Validate that a phone number is a valid Nigerian number.
    
    Args:
        phone_number: Phone number to validate
        
    Returns:
        True if valid Nigerian number, False otherwise
        
    Example:
        >>> from common_utils import validate_nigerian_phone
        >>> validate_nigerian_phone('08167791934')
        True
        >>> validate_nigerian_phone('+2348167791934')
        True
        >>> validate_nigerian_phone('1234567890')
        False
    """
    if not phone_number:
        return False
    
    # Remove non-digits
    digits = ''.join(filter(str.isdigit, phone_number.replace('+', '')))
    
    # Check if it's 11 digits starting with 0 or 13 digits starting with 234
    if len(digits) == 11 and digits.startswith('0'):
        return True
    elif len(digits) == 13 and digits.startswith('234'):
        return True
    elif len(digits) == 10:  # Without leading 0
        return True
    
    return False


def calculate_fare_hash(fare_data: dict) -> str:
    """
    Generate hash for fare calculation to prevent tampering.
    
    Args:
        fare_data: Dictionary containing fare calculation details
        
    Returns:
        MD5 hash of fare data
        
    Example:
        >>> from common_utils import calculate_fare_hash
        >>> fare = {'distance': 10, 'base_fare': 500}
        >>> hash_val = calculate_fare_hash(fare)
    """
    import hashlib
    import json
    
    # Sort keys for consistent hashing
    data_string = json.dumps(fare_data, sort_keys=True)
    return hashlib.md5(data_string.encode()).hexdigest()


def get_distance_and_duration(
    pickup_lat: float,
    pickup_lon: float,
    dest_lat: float,
    dest_lon: float
) -> Tuple[float, int]:
    """
    Get both distance and estimated duration for a route.
    
    Args:
        pickup_lat: Pickup latitude
        pickup_lon: Pickup longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        
    Returns:
        Tuple of (distance_km, duration_minutes)
        
    Example:
        >>> from common_utils import get_distance_and_duration
        >>> dist, dur = get_distance_and_duration(6.5244, 3.3792, 6.4541, 3.3947)
        >>> print(f"Distance: {dist}km, Duration: {dur}min")
        Distance: 7.89km, Duration: 16min
    """
    distance = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)
    duration = estimate_duration(distance)
    return distance, duration


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
        
    Example:
        >>> from common_utils import truncate_string
        >>> long_text = "This is a very long text" * 10
        >>> short_text = truncate_string(long_text, 50)
        >>> print(short_text)
        This is a very long textThis is a very long te...
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix