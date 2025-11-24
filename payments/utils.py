"""
FILE LOCATION: payments/utils.py

Complete Payments Utilities
Includes: Paystack Integration, Helper Functions, Validators
"""
import requests
import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
from typing import Dict, Optional, Tuple, List
from django.conf import settings

logger = logging.getLogger(__name__)


# ==================== PAYSTACK CLIENT ====================

class PaystackClient:
    """
    Complete Paystack API Client for SwiftRide
    
    Features:
    - Initialize payments (Card, Bank Transfer, USSD)
    - Verify transactions
    - List Nigerian banks
    - Validate bank accounts
    - Create transfer recipients
    - Process withdrawals
    - Verify webhooks
    """
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        
        if not self.secret_key:
            logger.warning("PAYSTACK_SECRET_KEY not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make HTTP request to Paystack API"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get('status'):
                raise Exception(result.get('message', 'Paystack request failed'))
            
            logger.info(f"✅ Paystack {method} {endpoint}: Success")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Paystack API error: {str(e)}")
            raise Exception(f"Payment gateway error: {str(e)}")
    
    # ==================== INITIALIZE PAYMENT ====================
    
    def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        callback_url: Optional[str] = None,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Initialize payment transaction
        
        Args:
            email: Customer email
            amount: Amount in Naira
            reference: Unique reference
            callback_url: Redirect URL after payment
            channels: ['card', 'bank', 'ussd', 'bank_transfer']
            metadata: Additional data
            
        Returns:
            {
                'authorization_url': 'https://checkout.paystack.com/...',
                'access_code': 'xxx',
                'reference': 'xxx'
            }
        """
        amount_kobo = int(amount * 100)
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'reference': reference,
            'currency': 'NGN',
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        if channels:
            payload['channels'] = channels
        if metadata:
            payload['metadata'] = metadata
        
        logger.info(f"💳 Initializing payment: {reference} - ₦{amount}")
        
        result = self._make_request('POST', '/transaction/initialize', data=payload)
        return result['data']
    
    # ==================== VERIFY PAYMENT ====================
    
    def verify_transaction(self, reference: str) -> Dict:
        """
        Verify payment transaction
        
        Returns:
            {
                'status': 'success' | 'failed',
                'amount': 100000,  # kobo
                'channel': 'card',
                'paid_at': '2024-01-01...',
                'customer': {...},
                'authorization': {...}
            }
        """
        logger.info(f"🔍 Verifying transaction: {reference}")
        result = self._make_request('GET', f'/transaction/verify/{reference}')
        return result['data']
    
    # ==================== NIGERIAN BANKS ====================
    
    def list_banks(self, country: str = 'nigeria') -> List[Dict]:
        """
        Get list of Nigerian banks
        
        Returns:
            [
                {'name': 'Access Bank', 'code': '044', 'active': True},
                ...
            ]
        """
        result = self._make_request(
            'GET', 
            '/bank',
            params={'country': country, 'perPage': 100}
        )
        return result['data']
    
    # ==================== ACCOUNT VALIDATION ====================
    
    def resolve_account_number(
        self, 
        account_number: str, 
        bank_code: str
    ) -> Dict:
        """
        Validate Nigerian bank account
        
        Returns:
            {
                'account_number': '0123456789',
                'account_name': 'JOHN DOE',
                'bank_id': 1
            }
        """
        logger.info(f"🏦 Validating account: {account_number} - Bank: {bank_code}")
        
        result = self._make_request(
            'GET',
            '/bank/resolve',
            params={
                'account_number': account_number,
                'bank_code': bank_code
            }
        )
        return result['data']
    
    # ==================== TRANSFER RECIPIENTS ====================
    
    def create_transfer_recipient(
        self,
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = 'NGN',
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create transfer recipient for withdrawals
        
        Returns:
            {
                'recipient_code': 'RCP_xxx',
                'name': 'JOHN DOE',
                'account_number': '0123456789',
                'bank_name': 'Access Bank'
            }
        """
        payload = {
            'type': 'nuban',
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': currency
        }
        
        if metadata:
            payload['metadata'] = metadata
        
        logger.info(f"📝 Creating recipient: {name} - {account_number}")
        
        result = self._make_request('POST', '/transferrecipient', data=payload)
        return result['data']
    
    # ==================== TRANSFERS ====================
    
    def initiate_transfer(
        self,
        amount: Decimal,
        recipient_code: str,
        reason: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Initiate bank transfer
        
        Returns:
            {
                'transfer_code': 'TRF_xxx',
                'reference': 'xxx',
                'status': 'pending',
                'amount': 100000
            }
        """
        amount_kobo = int(amount * 100)
        
        payload = {
            'source': 'balance',
            'amount': amount_kobo,
            'recipient': recipient_code,
            'reason': reason,
            'currency': 'NGN'
        }
        
        if reference:
            payload['reference'] = reference
        if metadata:
            payload['metadata'] = metadata
        
        logger.info(f"💸 Initiating transfer: ₦{amount} to {recipient_code}")
        
        result = self._make_request('POST', '/transfer', data=payload)
        return result['data']
    
    def verify_transfer(self, reference: str) -> Dict:
        """Verify transfer status"""
        result = self._make_request('GET', f'/transfer/verify/{reference}')
        return result['data']
    
    # ==================== WEBHOOK VERIFICATION ====================
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header
            
        Returns:
            True if valid
        """
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        
        if not secret_key:
            logger.error("PAYSTACK_SECRET_KEY not configured")
            return False
        
        computed = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        is_valid = hmac.compare_digest(computed, signature)
        
        if is_valid:
            logger.info("✅ Webhook signature verified")
        else:
            logger.warning("⚠️ Invalid webhook signature")
        
        return is_valid


# ==================== HELPER FUNCTIONS ====================

def generate_transaction_reference(prefix: str = 'TXN') -> str:
    """
    Generate unique transaction reference
    
    Args:
        prefix: Prefix for reference (TXN, DEP, WD, etc.)
        
    Returns:
        Unique reference string
    """
    unique_id = uuid.uuid4().hex[:12].upper()
    return f"{prefix}-{unique_id}"


def kobo_to_naira(amount_kobo: int) -> Decimal:
    """Convert kobo to Naira"""
    return Decimal(amount_kobo) / Decimal('100')


def naira_to_kobo(amount_naira: Decimal) -> int:
    """Convert Naira to kobo"""
    return int(amount_naira * 100)


def format_currency(amount: Decimal) -> str:
    """Format amount as Nigerian Naira"""
    return f"₦{amount:,.2f}"


def validate_nigerian_account(
    account_number: str, 
    bank_code: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate Nigerian bank account
    
    Returns:
        (is_valid, account_name, error_message)
    """
    # Basic validation
    if not account_number.isdigit():
        return False, None, "Account number must contain only digits"
    
    if len(account_number) != 10:
        return False, None, "Account number must be 10 digits"
    
    # Verify with Paystack
    try:
        client = PaystackClient()
        result = client.resolve_account_number(account_number, bank_code)
        account_name = result.get('account_name')
        return True, account_name, None
    except Exception as e:
        logger.error(f"Account validation failed: {str(e)}")
        return False, None, str(e)


def calculate_commission(total_amount: Decimal, rate: Decimal = Decimal('20.0')) -> Decimal:
    """
    Calculate platform commission from total amount
    
    Args:
        total_amount: Total transaction amount
        rate: Commission rate percentage (default 20%)
        
    Returns:
        Commission amount
    """
    return (total_amount * rate) / Decimal('100')


def calculate_driver_earnings(total_amount: Decimal, commission_rate: Decimal = Decimal('20.0')) -> Decimal:
    """
    Calculate driver earnings after commission
    
    Args:
        total_amount: Total ride amount
        commission_rate: Platform commission rate
        
    Returns:
        Driver earnings amount
    """
    commission = calculate_commission(total_amount, commission_rate)
    return total_amount - commission


def validate_amount(amount: Decimal, min_amount: Decimal = Decimal('0.01'), 
                    max_amount: Decimal = Decimal('1000000.00')) -> Tuple[bool, Optional[str]]:
    """
    Validate transaction amount
    
    Returns:
        (is_valid, error_message)
    """
    if amount < min_amount:
        return False, f"Amount must be at least ₦{min_amount}"
    
    if amount > max_amount:
        return False, f"Amount cannot exceed ₦{max_amount}"
    
    return True, None


# ==================== PAYMENT CARD UTILITIES ====================

def mask_card_number(card_number: str) -> str:
    """
    Mask card number for security
    
    Args:
        card_number: Full card number
        
    Returns:
        Masked card number (e.g., **** **** **** 1234)
    """
    if len(card_number) < 4:
        return '****'
    
    last_four = card_number[-4:]
    return f"**** **** **** {last_four}"


def get_card_type(card_number: str) -> str:
    """
    Detect card type from card number
    
    Returns:
        Card type: 'visa', 'mastercard', 'verve', 'unknown'
    """
    if not card_number:
        return 'unknown'
    
    # Remove spaces and dashes
    card_number = card_number.replace(' ', '').replace('-', '')
    
    # Visa: starts with 4
    if card_number.startswith('4'):
        return 'visa'
    
    # Mastercard: starts with 51-55 or 2221-2720
    if card_number.startswith(('51', '52', '53', '54', '55')):
        return 'mastercard'
    
    if len(card_number) >= 4:
        first_four = int(card_number[:4])
        if 2221 <= first_four <= 2720:
            return 'mastercard'
    
    # Verve: starts with 506 or 650
    if card_number.startswith(('506', '650')):
        return 'verve'
    
    return 'unknown'


# ==================== LOGGING UTILITIES ====================

def log_transaction(transaction_type: str, amount: Decimal, user_id: int, 
                   status: str = 'success', reference: str = '', **kwargs):
    """
    Log transaction for monitoring and debugging
    
    Args:
        transaction_type: Type of transaction
        amount: Transaction amount
        user_id: User ID
        status: Transaction status
        reference: Transaction reference
        **kwargs: Additional data to log
    """
    logger.info(
        f"Transaction: {transaction_type} | "
        f"User: {user_id} | "
        f"Amount: ₦{amount} | "
        f"Status: {status} | "
        f"Ref: {reference} | "
        f"Data: {kwargs}"
    )


def log_payment_error(error_type: str, user_id: int, amount: Decimal, 
                     error_message: str, **kwargs):
    """
    Log payment errors for debugging
    
    Args:
        error_type: Type of error
        user_id: User ID
        amount: Transaction amount
        error_message: Error description
        **kwargs: Additional context
    """
    logger.error(
        f"Payment Error: {error_type} | "
        f"User: {user_id} | "
        f"Amount: ₦{amount} | "
        f"Error: {error_message} | "
        f"Context: {kwargs}"
    )


# ==================== VALIDATION UTILITIES ====================

def validate_phone_number(phone_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Nigerian phone number
    
    Returns:
        (is_valid, error_message)
    """
    if not phone_number:
        return False, "Phone number is required"
    
    # Remove spaces and special characters
    phone = phone_number.replace(' ', '').replace('-', '').replace('+', '')
    
    # Check if only digits
    if not phone.isdigit():
        return False, "Phone number must contain only digits"
    
    # Nigerian numbers: 11 digits starting with 0, or 13 digits starting with 234
    if len(phone) == 11 and phone.startswith('0'):
        return True, None
    elif len(phone) == 13 and phone.startswith('234'):
        return True, None
    else:
        return False, "Invalid Nigerian phone number format"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Basic email validation
    
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if '@' not in email or '.' not in email:
        return False, "Invalid email format"
    
    return True, None


# ==================== CONSTANTS ====================

# Payment Methods
PAYMENT_METHOD_CARD = 'card'
PAYMENT_METHOD_BANK_TRANSFER = 'bank_transfer'
PAYMENT_METHOD_USSD = 'ussd'
PAYMENT_METHOD_WALLET = 'wallet'

PAYMENT_METHODS = [
    (PAYMENT_METHOD_CARD, 'Card'),
    (PAYMENT_METHOD_BANK_TRANSFER, 'Bank Transfer'),
    (PAYMENT_METHOD_USSD, 'USSD'),
    (PAYMENT_METHOD_WALLET, 'Wallet'),
]

# Transaction Types
TRANSACTION_TYPE_DEPOSIT = 'deposit'
TRANSACTION_TYPE_WITHDRAWAL = 'withdrawal'
TRANSACTION_TYPE_RIDE_PAYMENT = 'ride_payment'
TRANSACTION_TYPE_RIDE_EARNING = 'ride_earning'
TRANSACTION_TYPE_COMMISSION = 'commission'
TRANSACTION_TYPE_REFUND = 'refund'

# Transaction Statuses
TRANSACTION_STATUS_PENDING = 'pending'
TRANSACTION_STATUS_COMPLETED = 'completed'
TRANSACTION_STATUS_FAILED = 'failed'
TRANSACTION_STATUS_CANCELLED = 'cancelled'

# Withdrawal Statuses
WITHDRAWAL_STATUS_PENDING = 'pending'
WITHDRAWAL_STATUS_PROCESSING = 'processing'
WITHDRAWAL_STATUS_COMPLETED = 'completed'
WITHDRAWAL_STATUS_REJECTED = 'rejected'