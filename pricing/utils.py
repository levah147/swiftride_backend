"""
FILE LOCATION: pricing/utils.py

Fare calculation and verification utilities for SwiftRide.

CRITICAL FEATURE: Fare verification prevents users from tampering with prices.
All fare calculations are cached and verified with a hash.
"""
import hashlib
import json
from decimal import Decimal
from typing import Dict, Tuple, Optional
from django.core.cache import cache
from django.conf import settings


def calculate_fare(
    distance_km: float,
    duration_minutes: int,
    vehicle_type_id: int,
    city_id: Optional[int] = None,
    surge_multiplier: float = 1.0,
    fuel_price_adjustment: float = 0.0
) -> Dict:
    """
    Calculate fare for a ride with full breakdown.
    
    Args:
        distance_km: Distance in kilometers
        duration_minutes: Estimated duration in minutes
        vehicle_type_id: Vehicle type ID
        city_id: City ID (optional)
        surge_multiplier: Surge pricing multiplier (default: 1.0)
        fuel_price_adjustment: Fuel price adjustment amount
        
    Returns:
        Dictionary with fare breakdown and hash for verification
        
    Example:
        >>> fare = calculate_fare(10.5, 25, 1, city_id=1)
        >>> print(fare['total_fare'])
        2500.50
    """
    from pricing.models import VehiclePricing, City
    
    # Get pricing for vehicle type and city
    pricing_query = {'vehicle_type_id': vehicle_type_id}
    if city_id:
        pricing_query['city_id'] = city_id
    
    try:
        pricing = VehiclePricing.objects.get(**pricing_query, is_active=True)
    except VehiclePricing.DoesNotExist:
        # Fallback to default pricing if city-specific not found
        pricing = VehiclePricing.objects.filter(
            vehicle_type_id=vehicle_type_id,
            is_active=True
        ).first()
        
        if not pricing:
            raise ValueError(f"No pricing found for vehicle type {vehicle_type_id}")
    
    # Calculate base components
    base_fare = float(pricing.base_fare)
    distance_fare = float(pricing.price_per_km) * distance_km
    time_fare = float(pricing.price_per_minute) * duration_minutes
    
    # Calculate subtotal before surge
    subtotal = base_fare + distance_fare + time_fare
    
    # Apply surge pricing
    surge_amount = subtotal * (surge_multiplier - 1.0) if surge_multiplier > 1.0 else 0.0
    
    # Add fuel adjustment
    fuel_adjustment_total = fuel_price_adjustment
    
    # Calculate total fare
    total_fare = subtotal + surge_amount + fuel_adjustment_total
    
    # Ensure minimum fare
    minimum_fare = float(pricing.minimum_fare)
    if total_fare < minimum_fare:
        total_fare = minimum_fare
    
    # Round to 2 decimal places
    total_fare = round(total_fare, 2)
    
    # Prepare fare breakdown
    fare_breakdown = {
        'vehicle_type_id': vehicle_type_id,
        'city_id': city_id,
        'distance_km': round(distance_km, 2),
        'estimated_duration_minutes': duration_minutes,
        'base_fare': round(base_fare, 2),
        'distance_fare': round(distance_fare, 2),
        'time_fare': round(time_fare, 2),
        'subtotal': round(subtotal, 2),
        'surge_multiplier': surge_multiplier,
        'surge_amount': round(surge_amount, 2),
        'fuel_adjustment_total': round(fuel_adjustment_total, 2),
        'minimum_fare': minimum_fare,
        'total_fare': total_fare,
        'currency': 'NGN',
        'currency_symbol': '₦'
    }
    
    # Generate hash for verification
    fare_hash = generate_fare_hash(fare_breakdown)
    fare_breakdown['fare_hash'] = fare_hash
    
    # Cache fare calculation for verification (valid for 10 minutes)
    cache_key = f'fare_{fare_hash}'
    cache.set(cache_key, fare_breakdown, timeout=600)  # 10 minutes
    
    return fare_breakdown


def generate_fare_hash(fare_data: Dict) -> str:
    """
    Generate hash for fare calculation to prevent tampering.
    
    Args:
        fare_data: Dictionary containing fare calculation details
        
    Returns:
        MD5 hash of fare data
        
    Example:
        >>> fare = {'distance_km': 10, 'total_fare': 2500}
        >>> hash_val = generate_fare_hash(fare)
        >>> print(len(hash_val))
        32
    """
    # Create deterministic string from fare data (excluding the hash itself)
    fare_copy = {k: v for k, v in fare_data.items() if k != 'fare_hash'}
    
    # Sort keys for consistent hashing
    data_string = json.dumps(fare_copy, sort_keys=True)
    
    # Generate MD5 hash
    return hashlib.md5(data_string.encode()).hexdigest()


def verify_fare(fare_hash: str, expected_amount: Decimal) -> Tuple[bool, Optional[Dict]]:
    """
    Verify that a fare hash is valid and matches the expected amount.
    
    Args:
        fare_hash: Hash from fare calculation
        expected_amount: Expected total fare amount
        
    Returns:
        Tuple of (is_valid: bool, fare_data: Dict or None)
        
    Example:
        >>> is_valid, data = verify_fare('abc123...', Decimal('2500.50'))
        >>> if is_valid:
        ...     print("Fare verified!")
        ... else:
        ...     print("Fare tampering detected!")
    """
    cache_key = f'fare_{fare_hash}'
    cached_fare = cache.get(cache_key)
    
    if not cached_fare:
        return False, None
    
    # Verify the amount matches
    cached_amount = Decimal(str(cached_fare['total_fare']))
    if cached_amount != expected_amount:
        return False, None
    
    return True, cached_fare


def get_surge_multiplier(city_id: Optional[int] = None) -> float:
    """
    Get current surge multiplier for a city based on demand.
    
    Args:
        city_id: City ID (optional)
        
    Returns:
        Surge multiplier (1.0 = no surge, 1.5 = 50% surge, etc.)
        
    Example:
        >>> surge = get_surge_multiplier(city_id=1)
        >>> print(f"Current surge: {surge}x")
        Current surge: 1.2x
    """
    from pricing.models import SurgePricing
    from django.utils import timezone
    
    now = timezone.now()
    current_time = now.time()
    
    # Query for active surge pricing
    surge_query = {'is_active': True}
    if city_id:
        surge_query['city_id'] = city_id
    
    # Find applicable surge pricing based on time
    surge_pricings = SurgePricing.objects.filter(
        **surge_query,
        start_time__lte=current_time,
        end_time__gte=current_time
    ).order_by('-priority')
    
    if surge_pricings.exists():
        return float(surge_pricings.first().multiplier)
    
    return 1.0  # No surge


def get_fuel_adjustment(city_id: Optional[int] = None) -> float:
    """
    Get current fuel price adjustment for a city.
    
    Args:
        city_id: City ID (optional)
        
    Returns:
        Fuel adjustment amount
        
    Example:
        >>> adjustment = get_fuel_adjustment(city_id=1)
        >>> print(f"Fuel adjustment: ₦{adjustment}")
        Fuel adjustment: ₦50.00
    """
    from pricing.models import FuelPriceAdjustment
    
    try:
        query = {'is_active': True}
        if city_id:
            query['city_id'] = city_id
        
        fuel_adj = FuelPriceAdjustment.objects.filter(**query).first()
        if fuel_adj:
            return float(fuel_adj.calculate_adjustment())
    except Exception:
        pass
    
    return 0.0


def calculate_platform_commission(total_fare: Decimal, commission_rate: float = 20.0) -> Tuple[Decimal, Decimal]:
    """
    Calculate platform commission and driver earnings.
    
    Args:
        total_fare: Total ride fare
        commission_rate: Commission rate as percentage (default: 20%)
        
    Returns:
        Tuple of (commission_amount, driver_earnings)
        
    Example:
        >>> commission, earnings = calculate_platform_commission(Decimal('2500'), 20.0)
        >>> print(f"Commission: ₦{commission}, Driver gets: ₦{earnings}")
        Commission: ₦500.00, Driver gets: ₦2000.00
    """
    commission_amount = total_fare * Decimal(str(commission_rate / 100))
    driver_earnings = total_fare - commission_amount
    
    return (
        round(commission_amount, 2),
        round(driver_earnings, 2)
    )


def invalidate_fare_cache(fare_hash: str) -> None:
    """
    Invalidate a fare hash from cache (e.g., after ride is completed).
    
    Args:
        fare_hash: Hash to invalidate
    """
    cache_key = f'fare_{fare_hash}'
    cache.delete(cache_key)


def get_estimated_fare_range(
    distance_km: float,
    vehicle_type_id: int,
    city_id: Optional[int] = None
) -> Dict:
    """
    Get estimated fare range (low to high) considering potential surge.
    
    Args:
        distance_km: Distance in kilometers
        vehicle_type_id: Vehicle type ID
        city_id: City ID (optional)
        
    Returns:
        Dictionary with low and high fare estimates
        
    Example:
        >>> range_data = get_estimated_fare_range(10.5, 1)
        >>> print(f"Fare range: ₦{range_data['low']} - ₦{range_data['high']}")
        Fare range: ₦2000 - ₦3000
    """
    from common_utils import estimate_duration
    
    duration = estimate_duration(distance_km)
    
    # Calculate base fare (no surge)
    base_fare = calculate_fare(
        distance_km=distance_km,
        duration_minutes=duration,
        vehicle_type_id=vehicle_type_id,
        city_id=city_id,
        surge_multiplier=1.0
    )
    
    # Calculate max surge fare (e.g., 2.0x)
    surge_fare = calculate_fare(
        distance_km=distance_km,
        duration_minutes=duration,
        vehicle_type_id=vehicle_type_id,
        city_id=city_id,
        surge_multiplier=2.0
    )
    
    return {
        'low': base_fare['total_fare'],
        'high': surge_fare['total_fare'],
        'currency': '₦',
        'note': 'Final fare depends on traffic and demand'
    }