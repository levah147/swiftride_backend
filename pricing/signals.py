"""
FILE LOCATION: pricing/signals.py
Signal handlers for pricing app - WITH NOTIFICATIONS INTEGRATED!
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FuelPriceAdjustment, SurgePricing


@receiver(post_save, sender=FuelPriceAdjustment)
def fuel_price_updated(sender, instance, created, **kwargs):
    """Handle fuel price adjustments"""
    if created or instance.is_active:
        print(f"⛽ Fuel price updated for {instance.city.name}: ₦{instance.fuel_price_per_litre}")


@receiver(post_save, sender=SurgePricing)
def surge_pricing_activated(sender, instance, created, **kwargs):
    """Handle surge pricing activation"""
    if instance.is_active:
        print(f"📈 Surge {instance.multiplier}x active for {instance.city.name}")
        
        # Notify all active drivers in the city
        try:
            from notifications.tasks import send_push_notification_task
            from drivers.models import Driver
            
            # Get online drivers in the city
            drivers = Driver.objects.filter(
                is_online=True,
                status='approved'
            ).values_list('user_id', flat=True)
            
            if drivers:
                send_push_notification_task.delay(
                    user_ids=list(drivers),
                    title=f'Surge Pricing Active! 📈',
                    body=f'{instance.multiplier}x surge in {instance.city.name}. More earnings available!',
                    notification_type='surge_active',
                    data_payload={
                        'surge_multiplier': str(instance.multiplier),
                        'city': instance.city.name
                    }
                )
        except ImportError:
            pass




# """
# FILE LOCATION: pricing/signals.py
# Signal handlers for pricing app.
# """
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import FuelPriceAdjustment, SurgePricing


# @receiver(post_save, sender=FuelPriceAdjustment)
# def fuel_price_updated(sender, instance, created, **kwargs):
#     """Handle fuel price adjustments"""
#     if created or instance.is_active:
#         print(f"⛽ Fuel price updated for {instance.city.name}: ₦{instance.fuel_price_per_litre}")


# @receiver(post_save, sender=SurgePricing)
# def surge_pricing_activated(sender, instance, created, **kwargs):
#     """Handle surge pricing activation"""
#     if instance.is_active:
#         print(f"📈 Surge {instance.multiplier}x active for {instance.city.name}")


