
"""
FILE LOCATION: pricing/tasks.py
Celery tasks for pricing app.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_surge_pricing():
    """Update surge multipliers based on demand"""
    from .models import SurgePricing, City
    from django.utils import timezone
    
    # This would analyze current demand and activate/deactivate surge
    # For now, just log
    logger.info("Checking surge pricing conditions")
    return {'success': True}


@shared_task
def sync_fuel_prices():
    """Sync fuel prices from external source or admin input"""
    from .models import FuelPriceAdjustment
    from django.utils import timezone
    
    # Get the most recent active fuel adjustments
    active_adjustments = FuelPriceAdjustment.objects.filter(
        is_active=True
    ).select_related('city')
    
    updated_count = 0
    for adjustment in active_adjustments:
        # Check if adjustment needs updating (older than 7 days)
        days_since_update = (timezone.now().date() - adjustment.effective_date).days
        
        if days_since_update > 7:
            logger.warning(
                f"Fuel adjustment for {adjustment.city.name if adjustment.city else 'Global'} "
                f"is {days_since_update} days old. Consider updating."
            )
        else:
            logger.info(
                f"Fuel adjustment for {adjustment.city.name if adjustment.city else 'Global'} "
                f"is current ({days_since_update} days old)"
            )
        updated_count += 1
    
    # NOTE: For API integration, add external fuel price fetching here:
    # Example:
    # import requests
    # response = requests.get('https://api.fuelprices.ng/current')
    # data = response.json()
    # for city_data in data['cities']:
    #     FuelPriceAdjustment.objects.create(
    #         city=City.objects.get(name=city_data['name']),
    #         fuel_price_per_liter=Decimal(city_data['price']),
    #         effective_date=timezone.now().date()
    #     )
    
    logger.info(f"Checked {updated_count} fuel price adjustments")
    return {
        'success': True, 
        'checked': updated_count,
        'message': 'Fuel prices checked. Update manually in admin if needed.'
    }



