


"""
FILE LOCATION: vehicles/utils.py
Helper functions for vehicles app.
"""


from datetime import timedelta, timezone


def validate_vehicle_roadworthiness(vehicle):
    """
    Check if vehicle meets all requirements for operation.
    
    Returns:
        tuple: (is_roadworthy, list_of_issues)
    """
    issues = []
    
    if not vehicle.is_active:
        issues.append("Vehicle is inactive")
    
    if not vehicle.is_verified:
        issues.append("Vehicle not verified by admin")
    
    if vehicle.registration_expired:
        issues.append("Registration expired")
    
    if vehicle.insurance_expired:
        issues.append("Insurance expired")
    
    if vehicle.inspection_overdue:
        issues.append("Inspection overdue")
    
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
    recent_maintenance = vehicle.maintenance_records.filter(
        maintenance_date__gte=timezone.now().date() - timedelta(days=90)
    ).count()
    score += min(recent_maintenance * 5, 20)
    
    # Ride statistics (20 points)
    if vehicle.total_rides > 0:
        score += min(vehicle.total_rides / 10, 20)
    
    return min(int(score), 100)


