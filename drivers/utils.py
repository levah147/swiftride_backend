

"""
FILE LOCATION: drivers/utils.py

Helper functions for drivers app.
"""
from django.core.files.storage import default_storage
from PIL import Image
import io


def validate_vehicle_image(image_file):
    """
    Validate uploaded vehicle image.
    
    Checks:
    - File size (max 5MB)
    - Image format (JPG, PNG)
    - Image dimensions (min 800x600)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Check file size
        if image_file.size > 5 * 1024 * 1024:
            return False, "Image size must not exceed 5MB"
        
        # Open image
        img = Image.open(image_file)
        
        # Check format
        if img.format not in ['JPEG', 'PNG']:
            return False, "Only JPG and PNG images are allowed"
        
        # Check dimensions
        width, height = img.size
        if width < 800 or height < 600:
            return False, "Image must be at least 800x600 pixels"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def compress_image(image_file, max_size_mb=2):
    """
    Compress image if it's too large.
    
    Args:
        image_file: Uploaded image file
        max_size_mb: Maximum size in MB
    
    Returns:
        Compressed image file
    """
    try:
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save with compression
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output
        
    except Exception as e:
        return image_file


def calculate_driver_score(driver):
    """
    Calculate driver performance score (0-100).
    
    Based on:
    - Rating (40%)
    - Completion rate (30%)
    - Total rides (20%)
    - Response time (10%)
    
    Args:
        driver: Driver instance
    
    Returns:
        int: Score from 0-100
    """
    score = 0
    
    # Rating score (40 points max)
    rating_score = (float(driver.rating) / 5.0) * 40
    score += rating_score
    
    # Completion rate (30 points max)
    if driver.total_rides > 0:
        completion_rate = driver.completed_rides / driver.total_rides
        score += completion_rate * 30
    
    # Total rides (20 points max)
    rides_score = min(driver.total_rides / 100, 1.0) * 20
    score += rides_score
    
    # TODO: Response time score (10 points max)
    score += 5  # Placeholder
    
    return int(score)


def get_nearby_drivers(latitude, longitude, radius_km=5, vehicle_type=None):
    """
    Get available drivers near a location.
    
    Args:
        latitude: Pickup latitude
        longitude: Pickup longitude
        radius_km: Search radius in kilometers
        vehicle_type: Filter by vehicle type
    
    Returns:
        QuerySet of available drivers
    """
    from .models import Driver
    from common_utils import calculate_distance
    
    # Get all available drivers
    drivers = Driver.objects.filter(
        status='approved',
        is_online=True,
        is_available=True
    )
    
    if vehicle_type:
        drivers = drivers.filter(vehicle_type=vehicle_type)
    
    # TODO: Filter by actual location using PostGIS or similar
    # For now, return all available drivers
    
    return drivers[:10]  # Limit to 10 nearest



