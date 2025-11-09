
"""
FILE LOCATION: promotions/tasks.py

Celery tasks for promotions app.
"""
from celery import shared_task
from django.utils import timezone
from .services import award_referral_rewards
import logging

logger = logging.getLogger(__name__)


@shared_task
def expire_old_promos():
    """Mark expired promos as inactive"""
    from .models import PromoCode
    
    try:
        count = PromoCode.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        ).update(is_active=False)
        
        logger.info(f"⏰ Expired {count} promo codes")
        
        return {'success': True, 'count': count}
        
    except Exception as e:
        logger.error(f"Error expiring promos: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def process_referral_rewards():
    """Process completed referrals and award rewards"""
    from .models import Referral
    
    try:
        # Get completed referrals not yet rewarded
        completed_referrals = Referral.objects.filter(status='completed')
        
        success_count = 0
        for referral in completed_referrals:
            if award_referral_rewards(referral):
                success_count += 1
        
        logger.info(f"💰 Processed {success_count} referral rewards")
        
        return {
            'success': True,
            'processed': success_count
        }
        
    except Exception as e:
        logger.error(f"Error processing referral rewards: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def process_single_referral_reward(referral_id):
    """Process single referral reward (called from signal)"""
    from .models import Referral
    
    try:
        referral = Referral.objects.get(id=referral_id)
        
        if award_referral_rewards(referral):
            logger.info(f"💰 Rewarded referral #{referral_id}")
            return {'success': True}
        
        return {'success': False, 'error': 'Failed to award'}
        
    except Referral.DoesNotExist:
        logger.error(f"Referral {referral_id} not found")
        return {'success': False, 'error': 'Not found'}
    except Exception as e:
        logger.error(f"Error processing referral reward: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_promo_reminders():
    """Send reminders about expiring promos"""
    from .models import PromoCode, PromoUsage
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Get promos expiring in 3 days
        expiring_soon = PromoCode.objects.filter(
            is_active=True,
            end_date__lte=timezone.now() + timedelta(days=3),
            end_date__gt=timezone.now()
        )
        
        # Get users who haven't used each promo
        notification_count = 0
        
        for promo in expiring_soon:
            # Get users who haven't used this promo
            used_user_ids = PromoUsage.objects.filter(
                promo_code=promo
            ).values_list('user_id', flat=True)
            
            eligible_users = User.objects.exclude(
                id__in=used_user_ids
            ).filter(is_active=True)[:100]  # Limit to 100 users
            
            for user in eligible_users:
                try:
                    from notifications.tasks import send_notification_all_channels
                    
                    send_notification_all_channels.delay(
                        user_id=user.id,
                        notification_type='promo_expiring',
                        title='Promo Expiring Soon! ⏰',
                        body=f'Use code {promo.code} before it expires!',
                        send_push=True,
                        data={
                            'promo_code': promo.code,
                            'end_date': promo.end_date.isoformat()
                        }
                    )
                    
                    notification_count += 1
                except:
                    pass
        
        logger.info(f"📧 Sent {notification_count} promo expiry reminders")
        
        return {
            'success': True,
            'notifications_sent': notification_count
        }
        
    except Exception as e:
        logger.error(f"Error sending promo reminders: {str(e)}")
        return {'success': False, 'error': str(e)}
    
    
    
    