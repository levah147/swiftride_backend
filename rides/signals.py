"""
FILE LOCATION: rides/signals.py
Signal handlers for rides app - WITH CHAT & NOTIFICATIONS INTEGRATED!
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ride, RideRequest, DriverRideResponse, MutualRating


@receiver(post_save, sender=Ride)
def ride_created_handler(sender, instance, created, **kwargs):
    """
    Handle ride creation - send to nearby drivers.
    """
    if created and instance.status == 'pending':
        print(f"🚕 New ride created: #{instance.id}")
        
        # Create RideRequest for nearby drivers
        from .services import find_nearby_drivers
        
        try:
            nearby_drivers = find_nearby_drivers(
                latitude=instance.pickup_latitude,
                longitude=instance.pickup_longitude,
                vehicle_type=instance.vehicle_type,
                radius_km=10
            )
            
            for driver in nearby_drivers:
                RideRequest.objects.create(
                    ride=instance,
                    driver=driver
                )
                
                # Send notification to each driver
                try:
                    from notifications.tasks import send_notification_all_channels
                    send_notification_all_channels.delay(
                        user_id=driver.user.id,
                        notification_type='new_ride_request',
                        title='New Ride Request! 🚕',
                        body=f'New ride from {instance.pickup_location} to {instance.destination_location}',
                        send_push=True,
                        send_sms=False,
                        data={
                            'ride_id': instance.id,
                            'fare': str(instance.fare_amount)
                        }
                    )
                except ImportError:
                    pass
                
            print(f"📢 Notified {len(nearby_drivers)} drivers")
            
        except Exception as e:
            print(f"❌ Error finding nearby drivers: {str(e)}")


@receiver(post_save, sender=DriverRideResponse)
def driver_response_handler(sender, instance, created, **kwargs):
    """
    Handle driver accepting/declining ride.
    Auto-assign driver when accepted.
    ALSO CREATES CHAT CONVERSATION! 💬
    """
    if created:
        ride = instance.ride_request.ride
        
        if instance.response == 'accepted':
            # Auto-assign driver to ride
            ride.driver = instance.driver
            ride.status = 'accepted'
            ride.save()
            
            print(f"✅ Driver {instance.driver.user.phone_number} accepted ride #{ride.id}")
            
            # Cancel other pending requests
            RideRequest.objects.filter(
                ride=ride
            ).exclude(
                driver=instance.driver
            ).update(status='cancelled')
            
            # Notification handled by notifications app signals
            # Chat conversation created by chat app signals! 💬
        
        elif instance.response == 'declined':
            print(f"❌ Driver {instance.driver.user.phone_number} declined ride #{ride.id}")


@receiver(post_save, sender=Ride)
def ride_status_changed_handler(sender, instance, **kwargs):
    """
    Handle ride status changes.
    Notifications handled by notifications app signals.
    """
    if instance.status == 'completed':
        print(f"✅ Ride #{instance.id} completed")
        
        # Create mutual rating placeholder
        MutualRating.objects.get_or_create(
            ride=instance
        )
        
        # Update driver/vehicle stats
        if instance.driver:
            instance.driver.total_rides += 1
            # Convert Decimal to float for total_earnings
            from decimal import Decimal
            if isinstance(instance.fare_amount, Decimal):
                instance.driver.total_earnings += float(instance.fare_amount)
            else:
                instance.driver.total_earnings += instance.fare_amount
            instance.driver.save(update_fields=['total_rides', 'total_earnings'])
        
        if instance.vehicle:
            instance.vehicle.total_rides += 1
            instance.vehicle.save(update_fields=['total_rides'])


@receiver(post_save, sender=MutualRating)
def rating_submitted_handler(sender, instance, **kwargs):
    """
    Update driver/rider ratings when submitted.
    """
    if instance.rider_rating and instance.rider_rating > 0:
        # Update driver rating
        if instance.ride.driver:
            try:
                from drivers.models import Driver
                driver_profile = Driver.objects.get(user=instance.ride.driver.user)
                driver_profile.update_rating()
                print(f"⭐ Updated driver rating for {instance.ride.driver.user.phone_number}")
            except:
                pass
    
    if instance.driver_rating and instance.driver_rating > 0:
        # Update rider rating
        print(f"⭐ Rider {instance.ride.user.phone_number} received rating: {instance.driver_rating}")