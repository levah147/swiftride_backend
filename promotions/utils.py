


"""
FILE LOCATION: promotions/utils.py
"""

def apply_promo_to_ride(promo_code, ride):
    """Apply promo code to ride"""
    from .models import PromoCode, PromoUsage
    
    if not promo_code.is_valid():
        return False, "Promo code is not valid"
    
    if ride.final_fare < promo_code.minimum_fare:
        return False, f"Minimum fare is ₦{promo_code.minimum_fare}"
    
    discount = promo_code.calculate_discount(ride.final_fare)
    
    # Create usage record
    PromoUsage.objects.create(
        promo_code=promo_code,
        user=ride.rider,
        ride=ride,
        discount_amount=discount
    )
    
    # Update promo usage count
    promo_code.usage_count += 1
    promo_code.save()
    
    # Update ride fare
    ride.discount_amount = discount
    ride.final_fare = ride.final_fare - discount
    ride.save()
    
    return True, "Promo applied successfully"





