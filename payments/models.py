"""
FILE LOCATION: payments/models.py

Payment models for SwiftRide including Wallet, Transaction, PaymentCard, and Withdrawal.

CRITICAL FIX: Wallet operations now use atomic F() expressions to prevent race conditions.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import F
from decimal import Decimal

User = get_user_model()


class Wallet(models.Model):
    """User wallet for storing balance"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Wallet Status
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False, help_text="Locked for suspicious activity")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'payments_wallet'
    
    def __str__(self):
        return f"{self.user.phone_number} - ₦{self.balance}"
    
    def add_funds(self, amount):
        """
        Add money to wallet using atomic operation (FIXED - No race condition).
        
        Args:
            amount: Amount to add (Decimal, float, or int)
            
        Returns:
            Updated balance
            
        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Atomic update using F() expression
        Wallet.objects.filter(id=self.id).update(
            balance=F('balance') + Decimal(str(amount))
        )
        
        # Refresh from database to get updated balance
        self.refresh_from_db()
        return self.balance
    
    def deduct_funds(self, amount):
        """
        Deduct money from wallet using atomic operation (FIXED - No race condition).
        
        Args:
            amount: Amount to deduct (Decimal, float, or int)
            
        Returns:
            Updated balance
            
        Raises:
            ValueError: If amount is not positive or insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Atomic update with balance check using F() expression
        updated = Wallet.objects.filter(
            id=self.id,
            balance__gte=amount
        ).update(balance=F('balance') - Decimal(str(amount)))
        
        if not updated:
            raise ValueError("Insufficient balance")
        
        # Refresh from database to get updated balance
        self.refresh_from_db()
        return self.balance
    
    @property
    def formatted_balance(self):
        """Return formatted balance as currency string"""
        return f"₦{self.balance:,.2f}"


class Transaction(models.Model):
    """Payment transaction history"""
    
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),           # Add money to wallet
        ('withdrawal', 'Withdrawal'),     # Withdraw money
        ('ride_payment', 'Ride Payment'), # Pay for ride
        ('ride_earning', 'Ride Earning'), # Driver earning from ride
        ('refund', 'Refund'),            # Refund to rider
        ('commission', 'Commission'),     # Platform commission (deducted from driver)
        ('bonus', 'Bonus'),              # Promotional bonus
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('wallet', 'Wallet'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    
    # Transaction Details
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='wallet')
    
    # Pricing breakdown fields
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    surge_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)
    surge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fuel_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Amounts
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Balances (snapshot)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    
    # Reference
    reference = models.CharField(max_length=100, unique=True, help_text="Unique transaction reference")
    description = models.TextField(null=True, blank=True)
    
    # Related Models
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'payments_transaction'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - ₦{self.amount} - {self.user.phone_number}"
    
    @property
    def formatted_amount(self):
        return f"₦{self.amount:,.2f}"


class PaymentCard(models.Model):
    """Saved payment cards"""
    
    CARD_TYPE_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('verve', 'Verve'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_cards'
    )
    
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES)
    last_four = models.CharField(max_length=4, help_text="Last 4 digits of card")
    expiry_month = models.IntegerField()
    expiry_year = models.IntegerField()
    
    # Card Token (from payment gateway)
    card_token = models.CharField(max_length=255, unique=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        db_table = 'payments_payment_card'
    
    def __str__(self):
        return f"{self.get_card_type_display()} •••• {self.last_four}"
    
    def save(self, *args, **kwargs):
        # If this card is set as default, unset all other defaults
        if self.is_default:
            PaymentCard.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Withdrawal(models.Model):
    """Driver withdrawal requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    driver = models.ForeignKey(
        'drivers.Driver',
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))]  # Minimum ₦100
    )
    
    # Bank Details
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=100)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Admin/Processing
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_withdrawals'
    )
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Related Transaction
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawal_request'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'payments_withdrawal'
    
    def __str__(self):
        return f"Withdrawal ₦{self.amount} - {self.driver.user.phone_number} - {self.status}"