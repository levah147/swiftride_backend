
"""
FILE LOCATION: analytics/utils.py
"""
from decimal import Decimal
from datetime import timedelta

def calculate_growth_rate(current, previous):
    """Calculate percentage growth rate"""
    if previous == 0:
        return Decimal('0.00')
    
    growth = ((current - previous) / previous) * 100
    return round(Decimal(str(growth)), 2)

def get_demand_level(ride_count):
    """Determine demand level based on ride count"""
    if ride_count >= 50:
        return 'peak'
    elif ride_count >= 30:
        return 'high'
    elif ride_count >= 15:
        return 'medium'
    else:
        return 'low'

def calculate_performance_metrics(current_data, previous_data):
    """Calculate performance metrics with trends"""
    metrics = []
    
    for key in current_data:
        if key in previous_data:
            current = float(current_data[key])
            previous = float(previous_data[key])
            
            change = calculate_growth_rate(current, previous)
            
            if change > 5:
                trend = 'up'
            elif change < -5:
                trend = 'down'
            else:
                trend = 'stable'
            
            metrics.append({
                'metric_name': key,
                'current_value': current,
                'previous_value': previous,
                'change_percentage': float(change),
                'trend': trend
            })
    
    return metrics

def aggregate_location_data(rides, location_type='pickup'):
    """Aggregate location data for heat maps"""
    from .models import PopularLocation
    from collections import defaultdict
    
    grid_data = defaultdict(lambda: {'count': 0, 'coords': None})
    
    for ride in rides:
        if location_type == 'pickup':
            lat, lng = ride.pickup_latitude, ride.pickup_longitude
            address = ride.pickup_address
        else:
            lat, lng = ride.dropoff_latitude, ride.dropoff_longitude
            address = ride.dropoff_address
        
        grid_cell = PopularLocation.get_grid_cell(lat, lng)
        grid_data[grid_cell]['count'] += 1
        grid_data[grid_cell]['coords'] = (lat, lng)
        grid_data[grid_cell]['address'] = address
    
    return grid_data


