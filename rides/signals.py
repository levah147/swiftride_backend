"""
FILE LOCATION: rides/signals.py
Signal handlers for rides app - FIXED VERSION v3
Removes duplicate ride status updates (handled by views)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ride, RideRequest, DriverRideResponse, MutualRating
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ride)
def ride_created_handler(sender, instance, created, **kwargs):
    """
    Handle ride creation - notify nearby drivers via RideRequest.
    Only runs on creation (created=True)
    """
    if created and instance.status == 'pending':
        logger.info(f"🚕 New ride created: #{instance.id}")
        
        # Get the RideRequest for this ride (created in perform_create)
        try:
            ride_request = RideRequest.objects.filter(ride=instance, status='available').first()
            if not ride_request:
                logger.warning(f"No RideRequest found for ride {instance.id}")
                return
        except Exception as e:
            logger.error(f"Error getting RideRequest: {str(e)}")
            return
        
        # Find nearby drivers using locations app
        from .services import find_nearby_drivers
        
        try:
            # Get vehicle_type_id if vehicle_type is set
            vehicle_type_id = None
            if instance.vehicle_type:
                vehicle_type_id = instance.vehicle_type.id
            
            nearby_drivers_data = find_nearby_drivers(
                pickup_latitude=float(instance.pickup_latitude),
                pickup_longitude=float(instance.pickup_longitude),
                vehicle_type=vehicle_type_id,
                radius_km=instance.city.minimum_driver_radius_km if instance.city else 10,
                limit=20  # Notify up to 20 nearest drivers
            )
            
            notified_count = 0
            for driver_data in nearby_drivers_data:
                driver = driver_data['driver']  # Extract driver from dict
                
                # Add driver to notified_drivers ManyToMany
                ride_request.notified_drivers.add(driver)
                
                # Send notification to driver
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
                            'ride_request_id': ride_request.id,
                            'fare': str(instance.fare_amount),
                            'distance_km': driver_data.get('distance_km', 0)
                        }
                    )
                    notified_count += 1
                except ImportError:
                    logger.warning("Notifications app not available")
                except Exception as e:
                    logger.error(f"Error sending notification to driver {driver.id}: {str(e)}")
            
            logger.info(f"📢 Notified {notified_count} drivers for ride #{instance.id}")
            
        except Exception as e:
            logger.error(f"❌ Error finding nearby drivers: {str(e)}")


@receiver(post_save, sender=DriverRideResponse)
def driver_response_handler(sender, instance, created, **kwargs):
    """
    Handle driver accepting/declining ride.
    
    ✅ IMPORTANT: The accept_ride view already updates the Ride model,
    so this signal ONLY handles cleanup tasks like canceling other requests.
    
    DO NOT update the ride status here - it's already done in the view!
    """
    if not created:
        return  # Only handle new responses
    
    ride = instance.ride_request.ride
    
    if instance.response == 'accepted':
        logger.info(f"✅ Driver {instance.driver.user.phone_number} accepted ride #{ride.id}")
        
        # ✅ Cancel OTHER pending requests for THIS RIDE
        # The ride status and driver assignment is already handled by the accept_ride view
        other_requests = RideRequest.objects.filter(
            ride=ride,
            status='available'
        ).exclude(
            id=instance.ride_request.id  # Keep the accepted request
        )
        
        cancelled_count = other_requests.update(status='cancelled')
        if cancelled_count > 0:
            logger.info(f"✅ Cancelled {cancelled_count} other ride requests for ride #{ride.id}")
        
        # Mark the accepted request as accepted (if not already done)
        if instance.ride_request.status != 'accepted':
            instance.ride_request.status = 'accepted'
            instance.ride_request.save(update_fields=['status'])
        
        # Notification handled by notifications app signals
        # Chat conversation created by chat app signals! 💬
    
    elif instance.response == 'declined':
        logger.info(f"❌ Driver {instance.driver.user.phone_number} declined ride #{ride.id}")


@receiver(post_save, sender=Ride)
def ride_status_changed_handler(sender, instance, created, **kwargs):
    """
    Handle ride status changes.
    Only runs when status is 'completed' (to avoid conflicts)
    Notifications handled by notifications app signals.
    """
    # Skip if this is a new ride (handled by ride_created_handler)
    if created:
        return
    
    # Only handle completed rides here
    if instance.status == 'completed':
        logger.info(f"✅ Ride #{instance.id} completed")
        
        # Create mutual rating placeholder
        MutualRating.objects.get_or_create(
            ride=instance
        )
        
        # Update driver/vehicle stats
        if instance.driver:
            from decimal import Decimal
            
            # Increment total rides (safely handle None)
            instance.driver.total_rides = (instance.driver.total_rides or 0) + 1
            
            # Add to total earnings (convert Decimal to float if needed)
            current_earnings = float(instance.driver.total_earnings or 0)
            fare_amount = float(instance.fare_amount) if isinstance(instance.fare_amount, Decimal) else (instance.fare_amount or 0)
            instance.driver.total_earnings = current_earnings + fare_amount
            
            # Make driver available again
            instance.driver.is_available = True
            
            instance.driver.save(update_fields=['total_rides', 'total_earnings', 'is_available'])
            logger.info(f"✅ Updated driver #{instance.driver.id} stats: {instance.driver.total_rides} rides, ₦{instance.driver.total_earnings} earned")
        
        if instance.vehicle:
            instance.vehicle.total_rides = (instance.vehicle.total_rides or 0) + 1
            instance.vehicle.save(update_fields=['total_rides'])
            logger.info(f"✅ Updated vehicle #{instance.vehicle.id} stats: {instance.vehicle.total_rides} rides")


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
                driver_profile = Driver.objects.get(id=instance.ride.driver.id)
                driver_profile.update_rating()
                logger.info(f"⭐ Updated driver rating for {instance.ride.driver.user.phone_number}")
            except Exception as e:
                logger.error(f"Error updating driver rating: {str(e)}")
    
    if instance.driver_rating and instance.driver_rating > 0:
        # Update rider rating
        logger.info(f"⭐ Rider {instance.ride.user.phone_number} received rating: {instance.driver_rating}")