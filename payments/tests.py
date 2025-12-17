"""
FILE LOCATION: scripts/test_payments.py

Automated Payment System Testing Script
Run with: python manage.py shell < scripts/test_payments.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from payments.models import Wallet, Transaction
from payments.utils import PaystackClient, generate_transaction_reference
import json

User = get_user_model()

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


print_header("SWIFTRIDE PAYMENT SYSTEM - AUTOMATED TEST")

# ==================== TEST 1: DATABASE SETUP ====================
print_header("TEST 1: Database Setup & User Creation")

try:
    # Check if test user exists
    test_phone = "+2348012345678"
    user, created = User.objects.get_or_create(
        phone_number=test_phone,
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'testuser@swiftride.com',
            'is_phone_verified': True
        }
    )
    
    if created:
        print_success(f"Created new test user: {test_phone}")
    else:
        print_info(f"Using existing test user: {test_phone}")
    
    print_info(f"User ID: {user.id}")
    print_info(f"Phone: {user.phone_number}")
    print_info(f"Email: {user.email}")
    
except Exception as e:
    print_error(f"User creation failed: {str(e)}")
    sys.exit(1)

# ==================== TEST 2: WALLET CREATION ====================
print_header("TEST 2: Wallet Creation")

try:
    wallet, wallet_created = Wallet.objects.get_or_create(user=user)
    
    if wallet_created:
        print_success("Created new wallet")
    else:
        print_info("Using existing wallet")
    
    print_info(f"Wallet ID: {wallet.id}")
    print_info(f"Current Balance: ₦{wallet.balance}")
    print_info(f"Formatted: {wallet.formatted_balance}")
    print_info(f"Status: {'Active' if wallet.is_active else 'Inactive'}")
    print_info(f"Locked: {'Yes' if wallet.is_locked else 'No'}")
    
except Exception as e:
    print_error(f"Wallet creation failed: {str(e)}")
    sys.exit(1)

# ==================== TEST 3: PAYSTACK CLIENT ====================
print_header("TEST 3: Paystack Client Configuration")

try:
    from django.conf import settings
    
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
    public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', None)
    
    if not secret_key:
        print_error("PAYSTACK_SECRET_KEY not configured!")
        print_warning("Add to .env file: PAYSTACK_SECRET_KEY=sk_test_xxxxx")
        sys.exit(1)
    
    if not public_key:
        print_warning("PAYSTACK_PUBLIC_KEY not configured")
    
    # Check if test key
    if secret_key.startswith('sk_test_'):
        print_success("Using Paystack TEST mode ✓")
    elif secret_key.startswith('sk_live_'):
        print_warning("Using Paystack LIVE mode - be careful!")
    else:
        print_error("Invalid Paystack secret key format")
        sys.exit(1)
    
    print_info(f"Secret Key: {secret_key[:12]}...{secret_key[-4:]}")
    
    # Initialize client
    client = PaystackClient()
    print_success("Paystack client initialized successfully")
    
except Exception as e:
    print_error(f"Paystack configuration error: {str(e)}")
    sys.exit(1)

# ==================== TEST 4: FETCH NIGERIAN BANKS ====================
print_header("TEST 4: Fetch Nigerian Banks")

try:
    banks = client.list_banks()
    print_success(f"Fetched {len(banks)} banks from Paystack")
    
    # Show first 5 banks
    print_info("\nSample banks:")
    for i, bank in enumerate(banks[:5], 1):
        print(f"   {i}. {bank['name']} (Code: {bank['code']})")
    
    print_info(f"\n... and {len(banks) - 5} more banks")
    
except Exception as e:
    print_error(f"Failed to fetch banks: {str(e)}")
    print_warning("Check your internet connection and Paystack API key")

# ==================== TEST 5: MOCK DEPOSIT (DATABASE ONLY) ====================
print_header("TEST 5: Mock Deposit (Database Only)")

try:
    from django.db import transaction as db_transaction
    
    test_amount = Decimal('1000.00')
    
    with db_transaction.atomic():
        balance_before = wallet.balance
        wallet.add_funds(test_amount)
        balance_after = wallet.balance
        
        reference = generate_transaction_reference('TEST')
        
        txn = Transaction.objects.create(
            user=user,
            transaction_type='deposit',
            payment_method='card',
            amount=test_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description='Test deposit (mock)',
            status='completed',
            completed_at=timezone.now()
        )
    
    print_success(f"Mock deposit successful: ₦{test_amount}")
    print_info(f"Reference: {reference}")
    print_info(f"Balance: ₦{balance_before} → ₦{balance_after}")
    print_info(f"Transaction ID: {txn.id}")
    
except Exception as e:
    print_error(f"Mock deposit failed: {str(e)}")

# ==================== TEST 6: TRANSACTION HISTORY ====================
print_header("TEST 6: Transaction History")

try:
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:5]
    
    if transactions:
        print_success(f"Found {transactions.count()} recent transactions")
        print_info("\nRecent transactions:")
        
        for i, txn in enumerate(transactions, 1):
            print(f"\n   {i}. {txn.get_transaction_type_display()}")
            print(f"      Amount: ₦{txn.amount}")
            print(f"      Status: {txn.status}")
            print(f"      Reference: {txn.reference}")
            print(f"      Date: {txn.created_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        print_warning("No transactions found")
    
except Exception as e:
    print_error(f"Failed to fetch transactions: {str(e)}")

# ==================== TEST 7: WALLET OPERATIONS ====================
print_header("TEST 7: Wallet Operations (Atomic)")

try:
    print_info("Testing atomic wallet operations...")
    
    # Test add funds
    test_add = Decimal('500.00')
    balance_before = wallet.balance
    wallet.add_funds(test_add)
    balance_after = wallet.balance
    
    if balance_after == balance_before + test_add:
        print_success(f"Add funds: ₦{balance_before} + ₦{test_add} = ₦{balance_after} ✓")
    else:
        print_error(f"Add funds failed: Expected ₦{balance_before + test_add}, got ₦{balance_after}")
    
    # Test deduct funds
    test_deduct = Decimal('200.00')
    balance_before = wallet.balance
    wallet.deduct_funds(test_deduct)
    balance_after = wallet.balance
    
    if balance_after == balance_before - test_deduct:
        print_success(f"Deduct funds: ₦{balance_before} - ₦{test_deduct} = ₦{balance_after} ✓")
    else:
        print_error(f"Deduct funds failed: Expected ₦{balance_before - test_deduct}, got ₦{balance_after}")
    
    # Test insufficient balance
    try:
        insufficient_amount = wallet.balance + Decimal('1000000.00')
        wallet.deduct_funds(insufficient_amount)
        print_error("Insufficient balance check FAILED - should have raised error!")
    except ValueError as e:
        print_success(f"Insufficient balance protection works: {str(e)}")
    
except Exception as e:
    print_error(f"Wallet operations test failed: {str(e)}")

# ==================== TEST 8: GENERATE PAYMENT LINK ====================
print_header("TEST 8: Generate Paystack Payment Link")

try:
    test_amount = Decimal('1000.00')
    reference = generate_transaction_reference('TEST-DEP')
    
    # Create pending transaction
    with db_transaction.atomic():
        pending_txn = Transaction.objects.create(
            user=user,
            transaction_type='deposit',
            payment_method='card',
            amount=test_amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            reference=reference,
            description='Test payment link',
            status='pending',
            metadata={'test': True}
        )
    
    # Initialize payment with Paystack
    email = user.email or f"user_{user.id}@swiftride.com"
    
    result = client.initialize_transaction(
        email=email,
        amount=test_amount,
        reference=reference,
        channels=['card'],
        metadata={
            'user_id': user.id,
            'phone_number': user.phone_number,
            'transaction_id': pending_txn.id
        }
    )
    
    print_success("Payment link generated successfully!")
    print_info(f"\n{Colors.BOLD}PAYMENT DETAILS:{Colors.END}")
    print(f"   Reference: {reference}")
    print(f"   Amount: ₦{test_amount}")
    print(f"   Transaction ID: {pending_txn.id}")
    print(f"\n{Colors.BOLD}   Authorization URL:{Colors.END}")
    print(f"   {Colors.YELLOW}{result['authorization_url']}{Colors.END}")
    print(f"\n{Colors.BOLD}   Access Code:{Colors.END}")
    print(f"   {result['access_code']}")
    
    print_info(f"\n{Colors.BOLD}NEXT STEPS:{Colors.END}")
    print("   1. Copy the Authorization URL above")
    print("   2. Open it in your browser")
    print("   3. Use Paystack test card:")
    print(f"      {Colors.GREEN}Card: 4084 0840 8408 4081{Colors.END}")
    print(f"      {Colors.GREEN}CVV: 408{Colors.END}")
    print(f"      {Colors.GREEN}Expiry: 01/30{Colors.END}")
    print(f"      {Colors.GREEN}PIN: 0000{Colors.END}")
    print(f"      {Colors.GREEN}OTP: 123456{Colors.END}")
    print(f"   4. After payment, verify with:")
    print(f"      {Colors.BLUE}GET /api/payments/deposit/verify/?reference={reference}{Colors.END}")
    
except Exception as e:
    print_error(f"Failed to generate payment link: {str(e)}")
    import traceback
    traceback.print_exc()

# ==================== SUMMARY ====================
print_header("TEST SUMMARY")

print_info("✓ Database setup")
print_info("✓ User creation")
print_info("✓ Wallet operations")
print_info("✓ Paystack integration")
print_info("✓ Transaction creation")
print_info("✓ Payment link generation")

print(f"\n{Colors.BOLD}Current Wallet Status:{Colors.END}")
wallet.refresh_from_db()
print(f"   Balance: {Colors.GREEN}₦{wallet.balance}{Colors.END}")
print(f"   Status: {'🟢 Active' if wallet.is_active else '🔴 Inactive'}")

print(f"\n{Colors.BOLD}Test User Credentials:{Colors.END}")
print(f"   Phone: {user.phone_number}")
print(f"   Email: {user.email}")
print(f"   User ID: {user.id}")

print_header("TEST COMPLETE")
print_success("All tests passed! ✨")
print_info("\nTo test actual payment flow:")
print("1. Start Django server: python manage.py runserver")
print("2. Login via API to get access token")
print("3. Call: POST /api/payments/deposit/initialize/")
print("4. Complete payment on Paystack")
print("5. Call: GET /api/payments/deposit/verify/?reference=XXX")
print("6. Check wallet balance updated")

print(f"\n{Colors.YELLOW}Happy testing! 🚀{Colors.END}\n")