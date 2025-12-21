

"""
FILE LOCATION: promotions/signals.py

Signal handlers for promotions app.
Connects promotions/referrals to ALL apps automatically.

CRITICAL INTEGRATIONS:
- Auto-apply referral rewards
- Track loyalty points on rides
- Send promo notifications
- Calculate referral bonuses
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def create_loyalty_account_handler(sender, instance, created, **kwargs):
    """
    Auto-create loyalty account for new users.
    Give welcome bonus points.
    """
    if created:
        from .models import Loyalty
        
        try:
            loyalty, created = Loyalty.objects.get_or_create(
                user=instance,
                defaults={
                    'total_points': 100,  # Welcome bonus
                    'available_points': 100,
                    'tier': 'bronze'
                }
            )
            
            if created:
                logger.info(f" Loyalty account created for {instance.phone_number} with 100 welcome points")
                
                # Send welcome notification
                try:
                    from notifications.tasks import send_notification_all_channels
                    
                    send_notification_all_channels.delay(
                        user_id=instance.id,
                        notification_type='loyalty_welcome',
                        title='Welcome Bonus! 🎁',
                        body='You earned 100 loyalty points! Start riding to earn more.',
                        send_push=True,
                        data={'points': 100}
                    )
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error creating loyalty account: {str(e)}")


@receiver(post_save, sender='rides.Ride')
def ride_completed_loyalty_handler(sender, instance, **kwargs):
    """
    Award loyalty points when ride completes.
    1 point per ₦100 spent.
    """
    if instance.status == 'completed':
        from .models import Loyalty
        
        try:
            loyalty, _ = Loyalty.objects.get_or_create(user=instance.user)
            
            # Calculate points (1 point per ₦100)
            points = int(instance.fare_amount / Decimal('100'))
            
            if points > 0:
                loyalty.total_points += points
                loyalty.available_points += points
                
                # Update tier based on total points
                if loyalty.total_points >= 10000:
                    loyalty.tier = 'platinum'
                elif loyalty.total_points >= 5000:
                    loyalty.tier = 'gold'
                elif loyalty.total_points >= 2000:
                    loyalty.tier = 'silver'
                else:
                    loyalty.tier = 'bronze'
                
                loyalty.save()
                
                logger.info(f" {points} loyalty points awarded to {instance.user.phone_number}")
                
                # Send notification
                try:
                    from notifications.tasks import send_notification_all_channels
                    
                    send_notification_all_channels.delay(
                        user_id=instance.user.id,
                        notification_type='loyalty_points_earned',
                        title='Points Earned! 🎁',
                        body=f'You earned {points} loyalty points on your ride!',
                        send_push=True,
                        data={
                            'points': points,
                            'total_points': loyalty.total_points,
                            'tier': loyalty.tier
                        }
                    )
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error awarding loyalty points: {str(e)}")


@receiver(post_save, sender='rides.Ride')
def track_referral_completion_handler(sender, instance, **kwargs):
    """
    Track referee ride completion for referral rewards.
    Award referral bonus when conditions met.
    """
    if instance.status == 'completed':
        from .models import Referral, ReferralProgram
        
        try:
            # Check if user was referred
            referral = Referral.objects.filter(
                referee=instance.user,
                status='pending'
            ).first()
            
            if referral:
                # Increment rides completed
                referral.referee_rides_completed += 1
                
                # Check if requirements met
                if referral.referee_rides_completed >= referral.program.minimum_rides:
                    referral.status = 'completed'
                    
                    logger.info(
                        f"🎉 Referral completed! {referral.referrer.phone_number} "
                        f"referred {referral.referee.phone_number}"
                    )
                    
                    # Process rewards (will be handled by Celery task)
                    from .tasks import process_single_referral_reward
                    process_single_referral_reward.delay(referral.id)
                
                referral.save()
                
        except Exception as e:
            logger.error(f"Error tracking referral: {str(e)}")


@receiver(post_save, sender='payments.Transaction')
def promo_wallet_credit_handler(sender, instance, **kwargs):
    """
    Track promo-based wallet credits.
    Award referral rewards to wallet.
    """
    if instance.status == 'completed' and instance.transaction_type == 'referral_reward':
        try:
            # Send notification
            from notifications.tasks import send_notification_all_channels
            
            send_notification_all_channels.delay(
                user_id=instance.user.id,
                notification_type='referral_reward_received',
                title='Referral Reward! 🎉',
                body=f'₦{instance.amount} added to your wallet for referring a friend!',
                send_push=True,
                send_sms=False,
                data={
                    'amount': str(instance.amount),
                    'transaction_id': instance.transaction_id
                }
            )
            
            logger.info(f" Referral reward of ₦{instance.amount} credited to {instance.user.phone_number}")
            
        except Exception as e:
            logger.error(f"Error notifying referral reward: {str(e)}")
