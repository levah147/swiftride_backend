
"""
FILE LOCATION: pricing/services.py

Service layer for pricing business logic.
Fare calculations, surge pricing, fuel adjustments, etc.
"""
from django.db.models import Q, F
from django.utils import timezone
from decimal import Decimal
import math
import logging

logger = logging.getLogger(__name__)


def calculate_fare(vehicle_type_id, distance_km, duration_minutes=None, city_id=None):
    """
    Calculate ride fare based on distance, time, and other factors.
    
    Args:
        vehicle_type_id: Vehicle type ID
        distance_km: Distance in kilometers
        duration_minutes: Duration in minutes (optional)
        city_id: City ID (optional)
    
    Returns:
        dict: Fare breakdown
    """
    from .models import VehicleType, City, SurgePricing, FuelPriceAdjustment
    
    try:
        # Get vehicle type
        vehicle_type = VehicleType.objects.get(id=vehicle_type_id)
        
        # Base fare
        base_fare = vehicle_type.base_fare
        
        # Distance fare
        distance_fare = Decimal(str(distance_km)) * vehicle_type.per_km_rate
        
        # Time fare (if duration provided)
        time_fare = Decimal('0.00')
        if duration_minutes and vehicle_type.per_minute_rate:
            time_fare = Decimal(str(duration_minutes)) * vehicle_type.per_minute_rate
        
        # Subtotal
        subtotal = base_fare + distance_fare + time_fare
        
        # Apply surge pricing if active
        surge_multiplier = Decimal('1.0')
        if city_id:
            active_surge = SurgePricing.objects.filter(
                city_id=city_id,
                vehicle_type=vehicle_type,
                is_active=True,
                start_time__lte=timezone.now(),
                end_time__gte=timezone.now()
            ).first()
            
            if active_surge:
                surge_multiplier = active_surge.multiplier
        
        # Apply fuel adjustment if active
        fuel_adjustment = Decimal('0.00')
        if city_id:
            active_fuel = FuelPriceAdjustment.objects.filter(
                city_id=city_id,
                is_active=True,
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
            
            if active_fuel:
                fuel_adjustment = subtotal * (active_fuel.adjustment_percentage / Decimal('100'))
        
        # Calculate total
        surge_amount = subtotal * (surge_multiplier - Decimal('1.0'))
        total_fare = subtotal + surge_amount + fuel_adjustment
        
        # Apply minimum fare
        if total_fare < vehicle_type.minimum_fare:
            total_fare = vehicle_type.minimum_fare
        
        # Round to 2 decimal places
        return {
            'vehicle_type': vehicle_type.name,
            'base_fare': round(base_fare, 2),
            'distance_km': round(Decimal(str(distance_km)), 2),
            'distance_fare': round(distance_fare, 2),
            'duration_minutes': duration_minutes,
            'time_fare': round(time_fare, 2),
            'subtotal': round(subtotal, 2),
            'surge_multiplier': float(surge_multiplier),
            'surge_amount': round(surge_amount, 2),
            'fuel_adjustment': round(fuel_adjustment, 2),
            'total_fare': round(total_fare, 2),
            'minimum_fare': round(vehicle_type.minimum_fare, 2),
            'currency': 'NGN'
        }
        
    except VehicleType.DoesNotExist:
        logger.error(f"Vehicle type {vehicle_type_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error calculating fare: {str(e)}")
        return None


def calculate_distance_fare(vehicle_type_id, distance_km):
    """
    Calculate fare based on distance only.
    
    Args:
        vehicle_type_id: Vehicle type ID
        distance_km: Distance in kilometers
    
    Returns:
        Decimal: Total fare
    """
    result = calculate_fare(vehicle_type_id, distance_km)
    return Decimal(str(result['total_fare'])) if result else Decimal('0.00')


def get_fare_estimate(pickup_lat, pickup_lng, dest_lat, dest_lng, vehicle_type_id, city_id=None):
    """
    Get fare estimate for a trip.
    
    Args:
        pickup_lat, pickup_lng: Pickup coordinates
        dest_lat, dest_lng: Destination coordinates
        vehicle_type_id: Vehicle type ID
        city_id: City ID (optional)
    
    Returns:
        dict: Fare estimate with breakdown
    """
    # Calculate distance (use haversine formula)
    from rides.services import calculate_distance
    
    distance_km = calculate_distance(pickup_lat, pickup_lng, dest_lat, dest_lng)
    
    # Estimate duration (average speed 30 km/h in city)
    duration_minutes = int((distance_km / 30) * 60)
    
    # Calculate fare
    fare_data = calculate_fare(
        vehicle_type_id=vehicle_type_id,
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        city_id=city_id
    )
    
    if fare_data:
        fare_data['estimated_duration_minutes'] = duration_minutes
    
    return fare_data


def apply_surge_pricing(city_id, vehicle_type_id, multiplier, duration_hours=2):
    """
    Activate surge pricing for a city and vehicle type.
    
    Args:
        city_id: City ID
        vehicle_type_id: Vehicle type ID
        multiplier: Surge multiplier (e.g., 1.5 for 50% increase)
        duration_hours: How long surge will be active
    
    Returns:
        SurgePricing: Created surge pricing object
    """
    from .models import SurgePricing
    from datetime import timedelta
    
    try:
        # Deactivate existing surge for same city/vehicle
        SurgePricing.objects.filter(
            city_id=city_id,
            vehicle_type_id=vehicle_type_id,
            is_active=True
        ).update(is_active=False)
        
        # Create new surge
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        surge = SurgePricing.objects.create(
            city_id=city_id,
            vehicle_type_id=vehicle_type_id,
            multiplier=Decimal(str(multiplier)),
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        
        logger.info(f"Surge pricing activated: {multiplier}x for city {city_id}, vehicle {vehicle_type_id}")
        
        return surge
        
    except Exception as e:
        logger.error(f"Error applying surge pricing: {str(e)}")
        return None


def deactivate_surge_pricing(city_id, vehicle_type_id=None):
    """
    Deactivate surge pricing for a city.
    
    Args:
        city_id: City ID
        vehicle_type_id: Vehicle type ID (optional, if None deactivates all)
    
    Returns:
        int: Number of surge pricings deactivated
    """
    from .models import SurgePricing
    
    try:
        query = SurgePricing.objects.filter(
            city_id=city_id,
            is_active=True
        )
        
        if vehicle_type_id:
            query = query.filter(vehicle_type_id=vehicle_type_id)
        
        count = query.update(is_active=False)
        
        logger.info(f"Deactivated {count} surge pricings for city {city_id}")
        
        return count
        
    except Exception as e:
        logger.error(f"Error deactivating surge: {str(e)}")
        return 0


def get_active_surge(city_id, vehicle_type_id):
    """
    Get active surge pricing for city and vehicle type.
    
    Args:
        city_id: City ID
        vehicle_type_id: Vehicle type ID
    
    Returns:
        SurgePricing or None
    """
    from .models import SurgePricing
    
    try:
        return SurgePricing.objects.filter(
            city_id=city_id,
            vehicle_type_id=vehicle_type_id,
            is_active=True,
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).first()
        
    except Exception as e:
        logger.error(f"Error getting active surge: {str(e)}")
        return None


def update_fuel_adjustment(city_id, fuel_price_per_litre, adjustment_percentage):
    """
    Update fuel price adjustment for a city.
    
    Args:
        city_id: City ID
        fuel_price_per_litre: Current fuel price
        adjustment_percentage: Adjustment percentage
    
    Returns:
        FuelPriceAdjustment: Created adjustment object
    """
    from .models import FuelPriceAdjustment
    from datetime import timedelta
    
    try:
        # Deactivate existing adjustments
        FuelPriceAdjustment.objects.filter(
            city_id=city_id,
            is_active=True
        ).update(is_active=False)
        
        # Create new adjustment
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)  # Valid for 30 days
        
        adjustment = FuelPriceAdjustment.objects.create(
            city_id=city_id,
            fuel_price_per_litre=Decimal(str(fuel_price_per_litre)),
            adjustment_percentage=Decimal(str(adjustment_percentage)),
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        logger.info(f"Fuel adjustment updated for city {city_id}: {adjustment_percentage}%")
        
        return adjustment
        
    except Exception as e:
        logger.error(f"Error updating fuel adjustment: {str(e)}")
        return None


def get_vehicle_types_with_fares(city_id=None):
    """
    Get all vehicle types with their fare information.
    
    Args:
        city_id: City ID (optional, for surge info)
    
    Returns:
        list: Vehicle types with fare data
    """
    from .models import VehicleType
    
    try:
        vehicle_types = VehicleType.objects.filter(is_active=True)
        
        results = []
        for vt in vehicle_types:
            data = {
                'id': vt.id,
                'name': vt.name,
                'description': vt.description,
                'base_fare': float(vt.base_fare),
                'per_km_rate': float(vt.per_km_rate),
                'per_minute_rate': float(vt.per_minute_rate) if vt.per_minute_rate else 0,
                'minimum_fare': float(vt.minimum_fare),
                'max_passengers': vt.max_passengers,
                'surge_active': False,
                'surge_multiplier': 1.0
            }
            
            # Check for active surge
            if city_id:
                surge = get_active_surge(city_id, vt.id)
                if surge:
                    data['surge_active'] = True
                    data['surge_multiplier'] = float(surge.multiplier)
            
            results.append(data)
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting vehicle types: {str(e)}")
        return []


def validate_fare(ride_id, expected_fare, actual_fare, tolerance_percentage=5):
    """
    Validate that actual fare matches expected fare.
    
    Args:
        ride_id: Ride ID
        expected_fare: Expected fare amount
        actual_fare: Actual fare amount
        tolerance_percentage: Allowed difference percentage
    
    Returns:
        tuple: (is_valid, difference)
    """
    try:
        expected = Decimal(str(expected_fare))
        actual = Decimal(str(actual_fare))
        
        difference = abs(actual - expected)
        tolerance = expected * (Decimal(str(tolerance_percentage)) / Decimal('100'))
        
        is_valid = difference <= tolerance
        
        if not is_valid:
            logger.warning(
                f"Fare validation failed for ride {ride_id}: "
                f"Expected {expected}, Actual {actual}, Difference {difference}"
            )
        
        return is_valid, float(difference)
        
    except Exception as e:
        logger.error(f"Error validating fare: {str(e)}")
        return False, 0


def calculate_driver_earnings(total_fare, commission_percentage=20):
    """
    Calculate driver earnings after platform commission.
    
    Args:
        total_fare: Total ride fare
        commission_percentage: Platform commission percentage
    
    Returns:
        dict: Earnings breakdown
    """
    try:
        total = Decimal(str(total_fare))
        commission = total * (Decimal(str(commission_percentage)) / Decimal('100'))
        driver_earnings = total - commission
        
        return {
            'total_fare': round(total, 2),
            'commission_percentage': commission_percentage,
            'commission_amount': round(commission, 2),
            'driver_earnings': round(driver_earnings, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating driver earnings: {str(e)}")
        return None
