"""
FILE LOCATION: rides/common_utils.py

Common utility functions for rides app.
"""
import math
from decimal import Decimal


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
    
    Returns:
        float: Distance in kilometers
    """
    R = 6371.0  # Earth radius in km
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = (math.sin(dlat / 2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return round(distance, 2)


def estimate_duration(distance_km, avg_speed_kmh=30.0):
    """
    Estimate travel duration based on distance and average speed.
    
    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average speed in km/h (default: 30 km/h for city)
    
    Returns:
        int: Estimated duration in minutes
    """
    if avg_speed_kmh <= 0:
        return 0
    
    hours = distance_km / avg_speed_kmh
    minutes = hours * 60
    
    return int(minutes)


def format_currency(amount):
    """
    Format currency amount.
    
    Args:
        amount: Decimal or float amount
    
    Returns:
        str: Formatted currency string
    """
    if isinstance(amount, (int, float, Decimal)):
        return f"₦{amount:,.2f}"
    return "₦0.00"


def validate_coordinates(latitude, longitude):
    """
    Validate if coordinates are within valid range.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        if not (-90 <= lat <= 90):
            return False
        if not (-180 <= lon <= 180):
            return False
        
        return True
    except (ValueError, TypeError):
        return False