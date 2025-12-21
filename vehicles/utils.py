"""
FILE LOCATION: vehicles/utils.py
Helper functions for vehicles app.
"""
from django.utils import timezone
from datetime import timedelta


def validate_vehicle_roadworthiness(vehicle):
    """
    Check if vehicle meets all requirements for operation.
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        tuple: (is_roadworthy: bool, issues: list)
    
    Example:
        >>> is_ok, issues = validate_vehicle_roadworthiness(vehicle)
        >>> if not is_ok:
        ...     print(f"Issues: {', '.join(issues)}")
    """
    issues = []
    
    if not vehicle.is_active:
        issues.append("Vehicle is inactive")
    
    if not vehicle.is_verified:
        issues.append("Vehicle not verified by admin")
    
    if vehicle.registration_expired:
        issues.append(f"Registration expired on {vehicle.registration_expiry}")
    
    if vehicle.insurance_expired:
        issues.append(f"Insurance expired on {vehicle.insurance_expiry}")
    
    if vehicle.inspection_overdue:
        issues.append(f"Inspection overdue (due: {vehicle.next_inspection_due})")
    
    is_roadworthy = len(issues) == 0
    
    return is_roadworthy, issues


def calculate_vehicle_health_score(vehicle):
    """
    Calculate vehicle health score (0-100).
    
    Based on:
    - Document validity (30%)
    - Inspection status (30%)
    - Maintenance history (20%)
    - Ride statistics (20%)
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        int: Health score from 0-100
    
    Example:
        >>> score = calculate_vehicle_health_score(vehicle)
        >>> print(f"Health Score: {score}/100")
    """
    score = 0
    
    # Documents (30 points)
    if not vehicle.registration_expired:
        score += 10
    if not vehicle.insurance_expired:
        score += 10
    if vehicle.is_verified:
        score += 10
    
    # Inspection (30 points)
    if not vehicle.inspection_overdue:
        score += 15
    if vehicle.inspection_status == 'passed':
        score += 15
    
    # Maintenance (20 points)
    # Check for recent maintenance (within 90 days)
    ninety_days_ago = timezone.now().date() - timedelta(days=90)
    recent_maintenance = vehicle.maintenance_records.filter(
        maintenance_date__gte=ninety_days_ago
    ).count()
    score += min(recent_maintenance * 5, 20)
    
    # Ride statistics (20 points)
    # More rides = better maintained (assumption)
    if vehicle.total_rides > 0:
        ride_score = min(vehicle.total_rides / 10, 20)
        score += ride_score
    
    return min(int(score), 100)


def get_vehicle_expiry_warnings(vehicle):
    """
    Get warnings for documents expiring soon.
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        list: List of warning messages
    
    Example:
        >>> warnings = get_vehicle_expiry_warnings(vehicle)
        >>> for warning in warnings:
        ...     print(f"⚠️ {warning}")
    """
    warnings = []
    today = timezone.now().date()
    
    # Check registration expiry (warn 30 days before)
    if vehicle.registration_expiry:
        days_until_expiry = (vehicle.registration_expiry - today).days
        if 0 < days_until_expiry <= 30:
            warnings.append(
                f"Registration expires in {days_until_expiry} days ({vehicle.registration_expiry})"
            )
        elif days_until_expiry <= 0:
            warnings.append(f"Registration EXPIRED on {vehicle.registration_expiry}")
    
    # Check insurance expiry (warn 30 days before)
    if vehicle.insurance_expiry:
        days_until_expiry = (vehicle.insurance_expiry - today).days
        if 0 < days_until_expiry <= 30:
            warnings.append(
                f"Insurance expires in {days_until_expiry} days ({vehicle.insurance_expiry})"
            )
        elif days_until_expiry <= 0:
            warnings.append(f"Insurance EXPIRED on {vehicle.insurance_expiry}")
    
    # Check inspection due date (warn 14 days before)
    if vehicle.next_inspection_due:
        days_until_inspection = (vehicle.next_inspection_due - today).days
        if 0 < days_until_inspection <= 14:
            warnings.append(
                f"Inspection due in {days_until_inspection} days ({vehicle.next_inspection_due})"
            )
        elif days_until_inspection <= 0:
            warnings.append(f"Inspection OVERDUE since {vehicle.next_inspection_due}")
    
    return warnings


def format_vehicle_display_name(vehicle):
    """
    Format vehicle name for display.
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        str: Formatted vehicle name
    
    Example:
        >>> format_vehicle_display_name(vehicle)
        'Blue 2020 Toyota Camry (ABC-123-XY)'
    """
    return f"{vehicle.color} {vehicle.year} {vehicle.make} {vehicle.model} ({vehicle.license_plate})"


def check_vehicle_documents_complete(vehicle):
    """
    Check if vehicle has all required documents uploaded.
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        tuple: (all_complete: bool, missing_docs: list)
    """
    required_docs = ['registration', 'insurance', 'roadworthiness']
    uploaded_docs = vehicle.documents.values_list('document_type', flat=True)
    
    missing_docs = [doc for doc in required_docs if doc not in uploaded_docs]
    all_complete = len(missing_docs) == 0
    
    return all_complete, missing_docs


def check_vehicle_images_complete(vehicle):
    """
    Check if vehicle has all required images uploaded.
    
    Args:
        vehicle: Vehicle instance
    
    Returns:
        tuple: (all_complete: bool, missing_images: list)
    """
    required_images = ['front', 'back', 'left_side', 'right_side', 'license_plate']
    uploaded_images = vehicle.images.values_list('image_type', flat=True)
    
    missing_images = [img for img in required_images if img not in uploaded_images]
    all_complete = len(missing_images) == 0
    
    return all_complete, missing_images