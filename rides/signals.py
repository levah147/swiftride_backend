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
            ride=instance,
            defaults={
                'rider': instance.user,
                'driver': instance.driver.user if instance.driver else None
            }
        )
        
        # Update driver/vehicle stats
        if instance.driver:
            instance.driver.total_rides += 1
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
        if instance.driver:
            try:
                from drivers.models import Driver
                driver_profile = Driver.objects.get(user=instance.driver)
                driver_profile.update_rating()
                print(f"⭐ Updated driver rating for {instance.driver.phone_number}")
            except:
                pass
    
    if instance.driver_rating and instance.driver_rating > 0:
        # Update rider rating
        print(f"⭐ Rider {instance.rider.phone_number} received rating: {instance.driver_rating}")

# """
# FILE LOCATION: rides/signals.py
# Signal handlers for rides app - WITH NOTIFICATIONS INTEGRATED!
# """
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Ride, RideRequest, DriverRideResponse, MutualRating


# @receiver(post_save, sender=Ride)
# def ride_created_handler(sender, instance, created, **kwargs):
#     """
#     Handle ride creation - send to nearby drivers.
#     """
#     if created and instance.status == 'pending':
#         print(f"🚕 New ride created: #{instance.id}")
        
#         # Create RideRequest for nearby drivers
#         from .services import find_nearby_drivers
        
#         try:
#             nearby_drivers = find_nearby_drivers(
#                 latitude=instance.pickup_latitude,
#                 longitude=instance.pickup_longitude,
#                 vehicle_type=instance.vehicle_type,
#                 radius_km=10
#             )
            
#             for driver in nearby_drivers:
#                 RideRequest.objects.create(
#                     ride=instance,
#                     driver=driver
#                 )
                
#                 # Send notification to each driver
#                 try:
#                     from notifications.tasks import send_notification_all_channels
#                     send_notification_all_channels.delay(
#                         user_id=driver.user.id,
#                         notification_type='new_ride_request',
#                         title='New Ride Request! 🚕',
#                         body=f'New ride from {instance.pickup_location} to {instance.destination_location}',
#                         send_push=True,
#                         send_sms=False,
#                         data={
#                             'ride_id': instance.id,
#                             'fare': str(instance.fare_amount)
#                         }
#                     )
#                 except ImportError:
#                     pass
                
#             print(f"📢 Notified {len(nearby_drivers)} drivers")
            
#         except Exception as e:
#             print(f"❌ Error finding nearby drivers: {str(e)}")


# @receiver(post_save, sender=DriverRideResponse)
# def driver_response_handler(sender, instance, created, **kwargs):
#     """
#     Handle driver accepting/declining ride.
#     Auto-assign driver when accepted.
#     """
#     if created:
#         ride = instance.ride_request.ride
        
#         if instance.response == 'accepted':
#             # Auto-assign driver to ride
#             ride.driver = instance.driver
#             ride.status = 'accepted'
#             ride.save()
            
#             print(f"✅ Driver {instance.driver.user.phone_number} accepted ride #{ride.id}")
            
#             # Cancel other pending requests
#             RideRequest.objects.filter(
#                 ride=ride
#             ).exclude(
#                 driver=instance.driver
#             ).update(status='cancelled')
            
#             # Notification handled by notifications app signals
        
#         elif instance.response == 'declined':
#             print(f"❌ Driver {instance.driver.user.phone_number} declined ride #{ride.id}")


# @receiver(post_save, sender=Ride)
# def ride_status_changed_handler(sender, instance, **kwargs):
#     """
#     Handle ride status changes.
#     Notifications handled by notifications app signals.
#     """
#     if instance.status == 'completed':
#         print(f"✅ Ride #{instance.id} completed")
        
#         # Create mutual rating placeholder
#         MutualRating.objects.get_or_create(
#             ride=instance,
#             defaults={
#                 'rider': instance.user,
#                 'driver': instance.driver.user if instance.driver else None
#             }
#         )
        
#         # Update driver/vehicle stats
#         if instance.driver:
#             instance.driver.total_rides += 1
#             instance.driver.total_earnings += instance.fare_amount
#             instance.driver.save(update_fields=['total_rides', 'total_earnings'])
        
#         if instance.vehicle:
#             instance.vehicle.total_rides += 1
#             instance.vehicle.save(update_fields=['total_rides'])


# @receiver(post_save, sender=MutualRating)
# def rating_submitted_handler(sender, instance, **kwargs):
#     """
#     Update driver/rider ratings when submitted.
#     """
#     if instance.rider_rating and instance.rider_rating > 0:
#         # Update driver rating
#         if instance.driver:
#             try:
#                 from drivers.models import Driver
#                 driver_profile = Driver.objects.get(user=instance.driver)
#                 driver_profile.update_rating()
#                 print(f"⭐ Updated driver rating for {instance.driver.phone_number}")
#             except:
#                 pass
    
#     if instance.driver_rating and instance.driver_rating > 0:
#         # Update rider rating
#         print(f"⭐ Rider {instance.rider.phone_number} received rating: {instance.driver_rating}")
        
#   /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////      # 
        
# """
# FILE LOCATION: rides/signals.py

# Signal handlers for rides app - THE INTEGRATION HUB!
# """
# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
# from django.utils import timezone
# from .models import Ride, RideRequest, MutualRating, DriverRideResponse


# @receiver(post_save, sender=Ride)
# def ride_created_handler(sender, instance, created, **kwargs):
#     """
#     Handle ride creation.
    
#     Actions:
#     - Create RideRequest (already done in views)
#     - Notify nearby drivers
#     - Log ride creation
#     """
#     if created:
#         print(f"🚗 New ride requested: #{instance.id} by {instance.user.phone_number}")
        
#         # TODO: Trigger driver notifications
#         # from notifications.services import notify_nearby_drivers
#         # notify_nearby_drivers(instance)


# @receiver(post_save, sender=Ride)
# def ride_status_changed(sender, instance, created, **kwargs):
#     """
#     Handle ride status changes.
    
#     Status flow:
#     pending → accepted → arriving → in_progress → completed
#                      ↓
#                  cancelled
#     """
#     if not created and instance.status:
#         print(f"🔄 Ride #{instance.id} status: {instance.status}")
        
#         if instance.status == 'accepted':
#             # Driver accepted ride
#             # TODO: Notify rider that driver is coming
#             pass
        
#         elif instance.status == 'arriving':
#             # Driver is on the way
#             # TODO: Send ETA updates to rider
#             pass
        
#         elif instance.status == 'in_progress':
#             # Ride started
#             # TODO: Enable live tracking
#             # TODO: Notify emergency contacts
#             pass
        
#         elif instance.status == 'completed':
#             # Ride finished
#             print(f"✅ Ride #{instance.id} completed!")
            
#             # Create MutualRating object for both to rate each other
#             MutualRating.objects.get_or_create(ride=instance)
            
#             # TODO: Process payment
#             # TODO: Send completion notifications
#             # TODO: Prompt for ratings
        
#         elif instance.status == 'cancelled':
#             # Ride cancelled
#             print(f"❌ Ride #{instance.id} cancelled by {instance.cancelled_by}")
            
#             # TODO: Apply cancellation fees if needed
#             # TODO: Update driver availability
#             # TODO: Send cancellation notifications


# @receiver(post_save, sender=DriverRideResponse)
# def driver_response_handler(sender, instance, created, **kwargs):
#     """
#     Handle driver responses to ride requests.
    
#     Actions:
#     - If accepted: Assign driver to ride
#     - If declined: Continue searching
#     """
#     if created:
#         if instance.response == 'accepted':
#             print(f"✅ Driver {instance.driver.user.phone_number} accepted ride request #{instance.ride_request.id}")
            
#             # Assign driver to ride
#             ride = instance.ride_request.ride
#             ride.driver = instance.driver
#             ride.status = 'accepted'
#             ride.accepted_at = timezone.now()
#             ride.save()
            
#             # Mark request as accepted
#             instance.ride_request.status = 'accepted'
#             instance.ride_request.save()
            
#             # TODO: Cancel other pending requests
#             # TODO: Notify rider that driver is assigned
            
#         elif instance.response == 'declined':
#             print(f"❌ Driver {instance.driver.user.phone_number} declined ride request #{instance.ride_request.id}")
            
#             # TODO: Continue searching for other drivers
#             # TODO: If all decline, notify rider


# @receiver(post_save, sender=MutualRating)
# def rating_submitted_handler(sender, instance, created, **kwargs):
#     """
#     Handle rating submissions.
    
#     Actions:
#     - Update user/driver ratings
#     - Check if both parties rated
#     """
#     if not created:
#         ride = instance.ride
        
#         # Rider rated driver
#         if instance.rider_rating and instance.rider_rated_at:
#             print(f"⭐ Rider rated driver: {instance.rider_rating}/5 for ride #{ride.id}")
            
#             # Update driver's rating (already done in drivers.models)
#             if ride.driver:
#                 ride.driver.update_rating()
        
#         # Driver rated rider
#         if instance.driver_rating and instance.driver_rated_at:
#             print(f"⭐ Driver rated rider: {instance.driver_rating}/5 for ride #{ride.id}")
            
#             # Update user's rating
#             rider = ride.user
#             from django.db.models import Avg
#             avg_rating = MutualRating.objects.filter(
#                 ride__user=rider,
#                 driver_rating__isnull=False
#             ).aggregate(Avg('driver_rating'))['driver_rating__avg']
            
#             if avg_rating:
#                 rider.rating = round(avg_rating, 2)
#                 rider.save(update_fields=['rating'])
        
#         # Both rated - ride fully complete
#         if instance.is_complete:
#             print(f"✅ Both parties rated each other for ride #{ride.id}")
#             # TODO: Send thank you notifications

