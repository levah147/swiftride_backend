
"""
FILE LOCATION: accounts/validators.py

Custom validators for accounts app.
"""
import re
from django.core.exceptions import ValidationError


def validate_nigerian_phone(phone_number):
    """
    Validate Nigerian phone number format.
    
    Accepted formats:
    - +2348012345678
    - 08012345678
    - 8012345678
    """
    # Remove spaces and special characters
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Check format
    if cleaned.startswith('+234'):
        if len(cleaned) != 14:
            raise ValidationError('Nigerian phone must be 14 chars with +234')
    elif cleaned.startswith('0'):
        if len(cleaned) != 11:
            raise ValidationError('Nigerian phone must be 11 digits starting with 0')
    elif len(cleaned) == 10:
        pass  # Valid
    else:
        raise ValidationError('Invalid Nigerian phone number format')
    
    return cleaned


def validate_profile_picture(image):
    """Validate uploaded profile picture"""
    if image:
        # Max 5MB
        if image.size > 5 * 1024 * 1024:
            raise ValidationError('Image size must not exceed 5MB')
        
        # Check extension
        import os
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            raise ValidationError('Only JPG, PNG, GIF allowed')
    
    return image


