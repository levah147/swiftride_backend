"""
FILE LOCATION: promotions/services.py

Service layer for promotions business logic.
Promo codes, referrals, loyalty points management.

✅ FIXED: All Transaction.objects.create() calls now include unique 'reference' field
"""
import uuid
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import random
import string
import logging

logger = logging.getLogger(__name__)


def generate_referral_code(user):
    """
    Generate unique referral code for user.
    
    Args:
        user: User object
    
    Returns:
        str: Referral code
    """
    # Use last 6 digits of phone + random 2 chars
    phone_suffix = user.phone_number[-6:] if len(user.phone_number) >= 6 else user.phone_number
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
    
    return f"REF{phone_suffix}{random_suffix}"


def validate_promo_code(code, user, fare_amount):
    """
    Validate promo code for user and fare.
    
    Args:
        code: Promo code string
        user: User object
        fare_amount: Fare amount
    
    Returns:
        tuple: (is_valid, promo_code_or_error_message, discount_amount)
    """
    from .models import PromoCode, PromoUsage
    
    try:
        promo = PromoCode.objects.get(code=code.upper())
        
        # Check if promo is valid
        if not promo.is_valid():
            return False, "Promo code has expired or reached usage limit", Decimal('0.00')
        
        # Check minimum fare
        if fare_amount < promo.minimum_fare:
            return False, f"Minimum fare is ₦{promo.minimum_fare}", Decimal('0.00')
        
        # Check usage per user
        user_usage_count = PromoUsage.objects.filter(
            promo_code=promo,
            user=user
        ).count()
        
        if user_usage_count >= promo.usage_per_user:
            return False, "You've already used this promo code", Decimal('0.00')
        
        # Check user type eligibility
        if promo.user_type == 'new':
            # Check if user has completed any rides
            from rides.models import Ride
            if Ride.objects.filter(user=user, status='completed').exists():
                return False, "This promo is for new users only", Decimal('0.00')
        
        # Calculate discount
        discount = promo.calculate_discount(fare_amount)
        
        return True, promo, discount
        
    except PromoCode.DoesNotExist:
        return False, "Invalid promo code", Decimal('0.00')
    except Exception as e:
        logger.error(f"Error validating promo: {str(e)}")
        return False, "Error validating promo code", Decimal('0.00')


def apply_promo_to_ride(promo_code, ride):
    """
    Apply validated promo code to ride.
    
    Args:
        promo_code: PromoCode object
        ride: Ride object
    
    Returns:
        tuple: (success, message)
    """
    from .models import PromoUsage
    
    try:
        with transaction.atomic():
            # Calculate discount
            discount = promo_code.calculate_discount(ride.fare_amount)
            
            # Create usage record
            PromoUsage.objects.create(
                promo_code=promo_code,
                user=ride.user,
                ride=ride,
                discount_amount=discount
            )
            
            # Update promo usage count
            promo_code.usage_count += 1
            promo_code.save()
            
            # Update ride fare
            ride.discount_amount = discount
            ride.fare_amount = ride.fare_amount - discount
            ride.save()
            
            logger.info(f"Promo {promo_code.code} applied to ride #{ride.id}, discount: ₦{discount}")
            
            return True, f"₦{discount} discount applied!"
            
    except Exception as e:
        logger.error(f"Error applying promo: {str(e)}")
        return False, "Failed to apply promo code"


def create_referral(referrer, referee_phone):
    """
    Create referral when someone signs up with referral code.
    
    Args:
        referrer: User who referred (owner of code)
        referee_phone: Phone number of referee
    
    Returns:
        Referral or None
    """
    from .models import Referral, ReferralProgram
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Get active referral program
        program = ReferralProgram.objects.filter(is_active=True).first()
        
        if not program:
            logger.warning("No active referral program")
            return None
        
        # Get referee user
        referee = User.objects.filter(phone_number=referee_phone).first()
        
        if not referee:
            logger.warning(f"Referee {referee_phone} not found")
            return None
        
        # Check if already referred
        if Referral.objects.filter(referee=referee).exists():
            logger.warning(f"User {referee_phone} already referred")
            return None
        
        # Can't refer yourself
        if referrer == referee:
            logger.warning("Cannot refer yourself")
            return None
        
        # Generate referral code
        referral_code = generate_referral_code(referrer)
        
        # Create referral
        referral = Referral.objects.create(
            program=program,
            referrer=referrer,
            referee=referee,
            referral_code=referral_code,
            status='pending'
        )
        
        logger.info(f"Referral created: {referrer.phone_number} → {referee.phone_number}")
        
        # Send notifications
        try:
            from notifications.tasks import send_notification_all_channels
            
            # Notify referrer
            send_notification_all_channels.delay(
                user_id=referrer.id,
                notification_type='referral_created',
                title='Friend Joined!',
                body=f'{referee.phone_number} joined using your referral code!',
                send_push=True,
                data={'referee': referee.phone_number}
            )
            
            # Notify referee
            send_notification_all_channels.delay(
                user_id=referee.id,
                notification_type='referral_received',
                title='Referral Bonus',
                body=f'Complete {program.minimum_rides} ride(s) to get ₦{program.referee_reward} bonus!',
                send_push=True,
                data={'reward': str(program.referee_reward)}
            )
        except:
            pass
        
        return referral
        
    except Exception as e:
        logger.error(f"Error creating referral: {str(e)}")
        return None


def award_referral_rewards(referral):
    """
    Award referral rewards to both users.
    
    Args:
        referral: Referral object
    
    Returns:
        bool: Success status
    """
    from payments.models import Transaction, Wallet
    
    try:
        with transaction.atomic():
            program = referral.program
            
            # Get/create wallets
            referrer_wallet, _ = Wallet.objects.get_or_create(user=referral.referrer)
            referee_wallet, _ = Wallet.objects.get_or_create(user=referral.referee)
            
            # Award referrer
            referrer_wallet.balance += program.referrer_reward
            referrer_wallet.save()
            
            # Generate unique reference for referrer transaction
            referrer_reference = f"REF-{referral.id}-{referral.referrer.id}-{int(timezone.now().timestamp())}"
            
            Transaction.objects.create(
                user=referral.referrer,
                transaction_type='referral_reward',
                amount=program.referrer_reward,
                status='completed',
                reference=referrer_reference,
                description=f'Referral reward for {referral.referee.phone_number}'
            )
            
            # Award referee
            referee_wallet.balance += program.referee_reward
            referee_wallet.save()
            
            # Generate unique reference for referee transaction
            referee_reference = f"REF-{referral.id}-{referral.referee.id}-{int(timezone.now().timestamp())}"
            
            Transaction.objects.create(
                user=referral.referee,
                transaction_type='referral_reward',
                amount=program.referee_reward,
                status='completed',
                reference=referee_reference,
                description='Referral bonus for joining'
            )
            
            # Update referral status
            referral.status = 'rewarded'
            referral.save()
            
            logger.info(
                f"Referral rewards awarded: "
                f"₦{program.referrer_reward} to {referral.referrer.phone_number}, "
                f"₦{program.referee_reward} to {referral.referee.phone_number}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Error awarding referral rewards: {str(e)}")
        return False


def redeem_loyalty_points(user, points):
    """
    Redeem loyalty points for wallet credit.
    
    Args:
        user: User object
        points: Points to redeem
    
    Returns:
        tuple: (success, message, amount)
    """
    from .models import Loyalty
    from payments.models import Wallet, Transaction
    
    try:
        # Get loyalty account
        loyalty = Loyalty.objects.get(user=user)
        
        # Check if enough points
        if loyalty.available_points < points:
            return False, "Not enough points", Decimal('0.00')
        
        # Convert points to money (100 points = ₦10)
        amount = Decimal(points) / Decimal('10')
        
        with transaction.atomic():
            # Deduct points
            loyalty.available_points -= points
            loyalty.save()
            
            # Add to wallet
            wallet, _ = Wallet.objects.get_or_create(user=user)
            wallet.balance += amount
            wallet.save()
            
            # Generate unique reference for this transaction
            reference = f"LPR-{user.id}-{int(timezone.now().timestamp())}-{str(uuid.uuid4())[:8]}"
            
            # Create transaction with unique reference
            Transaction.objects.create(
                user=user,
                transaction_type='loyalty_redemption',
                amount=amount,
                status='completed',
                reference=reference,
                description=f'Redeemed {points} loyalty points'
            )
            
            logger.info(f"Redemption successful for {user.phone_number}: {points} points redeemed for ₦{amount}")
            
            return True, f"₦{amount} added to your wallet!", amount
            
    except Loyalty.DoesNotExist:
        return False, "Loyalty account not found", Decimal('0.00')
    except Exception as e:
        logger.error(f"Error redeeming points: {str(e)}")
        return False, "Failed to redeem points", Decimal('0.00')


def get_user_referral_stats(user):
    """
    Get user's referral statistics.
    
    Args:
        user: User object
    
    Returns:
        dict: Referral stats
    """
    from .models import Referral
    
    try:
        referrals = Referral.objects.filter(referrer=user)
        
        stats = {
            'referral_code': generate_referral_code(user),
            'total_referrals': referrals.count(),
            'pending_referrals': referrals.filter(status='pending').count(),
            'completed_referrals': referrals.filter(status='completed').count(),
            'rewarded_referrals': referrals.filter(status='rewarded').count(),
            'total_earned': Decimal('0.00')
        }
        
        # Calculate total earned
        from payments.models import Transaction
        
        referral_transactions = Transaction.objects.filter(
            user=user,
            transaction_type='referral_reward',
            status='completed'
        )
        
        stats['total_earned'] = referral_transactions.aggregate(
            total=transaction.models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting referral stats: {str(e)}")
        return {}


def get_active_promos_for_user(user):
    """
    Get active promo codes available for user.
    
    Args:
        user: User object
    
    Returns:
        QuerySet: Active promo codes
    """
    from .models import PromoCode, PromoUsage
    from rides.models import Ride
    
    try:
        now = timezone.now()
        
        # Get all active promos
        promos = PromoCode.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Filter by user type
        user_rides = Ride.objects.filter(user=user, status='completed').count()
        
        if user_rides == 0:
            # New user
            promos = promos.filter(user_type__in=['all', 'new'])
        else:
            # Existing user
            promos = promos.exclude(user_type='new')
        
        # Exclude fully used promos
        available_promos = []
        for promo in promos:
            user_usage = PromoUsage.objects.filter(
                promo_code=promo,
                user=user
            ).count()
            
            if user_usage < promo.usage_per_user:
                if not promo.usage_limit or promo.usage_count < promo.usage_limit:
                    available_promos.append(promo)
        
        return available_promos
        
    except Exception as e:
        logger.error(f"Error getting active promos: {str(e)}")
        return []
    