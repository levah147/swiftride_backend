
"""
FILE LOCATION: payments/utils.py
Payment utility functions.
"""
from decimal import Decimal
import hashlib
import uuid


def generate_transaction_reference(prefix='TXN'):
    """Generate unique transaction reference"""
    unique_id = uuid.uuid4().hex[:12].upper()
    return f"{prefix}-{unique_id}"


def format_currency(amount):
    """Format amount as Nigerian Naira"""
    return f"₦{amount:,.2f}"


def calculate_commission(total_amount, rate=20.0):
    """
    Calculate platform commission.
    
    Args:
        total_amount: Total ride fare
        rate: Commission rate (default 20%)
    
    Returns:
        tuple: (commission, driver_earnings)
    """
    commission = Decimal(str(total_amount)) * Decimal(str(rate)) / Decimal('100')
    driver_earnings = Decimal(str(total_amount)) - commission
    
    return (
        round(commission, 2),
        round(driver_earnings, 2)
    )


def validate_bank_account(account_number, bank_code):
    """
    Validate Nigerian bank account.
    TODO: Integrate with bank verification API
    
    Args:
        account_number: 10-digit account number
        bank_code: Bank code
    
    Returns:
        dict: Account details or None
    """
    if not account_number.isdigit() or len(account_number) != 10:
        return None
    
    # TODO: Call bank API for verification
    return {
        'valid': True,
        'account_name': 'Account Holder Name'  # From API
    }


def get_payment_gateway_config(gateway='paystack'):
    """
    Get payment gateway configuration.
    
    Args:
        gateway: Gateway name (paystack, flutterwave)
    
    Returns:
        dict: Gateway configuration
    """
    from django.conf import settings
    
    configs = {
        'paystack': {
            'public_key': getattr(settings, 'PAYSTACK_PUBLIC_KEY', ''),
            'secret_key': getattr(settings, 'PAYSTACK_SECRET_KEY', ''),
            'callback_url': getattr(settings, 'PAYSTACK_CALLBACK_URL', ''),
        },
        'flutterwave': {
            'public_key': getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', ''),
            'secret_key': getattr(settings, 'FLUTTERWAVE_SECRET_KEY', ''),
            'encryption_key': getattr(settings, 'FLUTTERWAVE_ENCRYPTION_KEY', ''),
        }
    }
    
    return configs.get(gateway, {})


