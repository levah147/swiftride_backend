from rest_framework import serializers
from .models import Wallet, Transaction, PaymentCard, Withdrawal
from decimal import Decimal


class WalletSerializer(serializers.ModelSerializer):
    formatted_balance = serializers.ReadOnlyField()
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'phone_number', 'balance', 'formatted_balance',
            'is_active', 'is_locked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'is_locked', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    formatted_amount = serializers.ReadOnlyField()
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_phone', 'transaction_type', 'transaction_type_display',
            'payment_method', 'payment_method_display', 'amount', 'formatted_amount',
            'balance_before', 'balance_after', 'status', 'status_display',
            'reference', 'description', 'ride', 'metadata',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user', 'reference', 'balance_before', 'balance_after',
            'status', 'created_at', 'completed_at'
        ]


class DepositSerializer(serializers.Serializer):
    """Serializer for depositing money into wallet"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('100.00'))
    payment_method = serializers.ChoiceField(choices=['card', 'bank_transfer'])
    
    def validate_amount(self, value):
        if value < Decimal('100.00'):
            raise serializers.ValidationError("Minimum deposit is ₦100.00")
        if value > Decimal('500000.00'):
            raise serializers.ValidationError("Maximum deposit is ₦500,000.00 per request")
        return value
    
    def validate_account_number(self, value):
        # Basic validation for Nigerian account numbers (10 digits)
        if not value.isdigit():
            raise serializers.ValidationError("Account number must contain only digits")
        if len(value) != 10:
            raise serializers.ValidationError("Account number must be 10 digits")
        return value


class PaymentCardSerializer(serializers.ModelSerializer):
    card_type_display = serializers.CharField(source='get_card_type_display', read_only=True)
    
    class Meta:
        model = PaymentCard
        fields = [
            'id', 'card_type', 'card_type_display', 'last_four',
            'expiry_month', 'expiry_year', 'is_default', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'card_token', 'created_at']
    
    def validate(self, data):
        # Validate expiry date
        import datetime
        now = datetime.datetime.now()
        
        expiry_month = data.get('expiry_month')
        expiry_year = data.get('expiry_year')
        
        if expiry_month < 1 or expiry_month > 12:
            raise serializers.ValidationError({'expiry_month': 'Invalid month'})
        
        if expiry_year < now.year:
            raise serializers.ValidationError({'expiry_year': 'Card is expired'})
        
        if expiry_year == now.year and expiry_month < now.month:
            raise serializers.ValidationError({'expiry_month': 'Card is expired'})
        
        return data


class WithdrawalSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    driver_phone = serializers.CharField(source='driver.user.phone_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'driver', 'driver_name', 'driver_phone', 'amount',
            'bank_name', 'account_number', 'account_name',
            'status', 'status_display', 'rejection_reason',
            'created_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'driver', 'status', 'rejection_reason',
            'processed_at', 'created_at'
        ]
    
    def validate_amount(self, value):
        if value < Decimal('100.00'):
            raise serializers.ValidationError("Minimum withdrawal is ₦100.00")
        return value
    
    def validate(self, data):
        # Check if driver has sufficient balance
        request = self.context.get('request')
        if request and hasattr(request.user, 'driver_profile'):
            driver = request.user.driver_profile
            wallet = request.user.wallet
            
            if wallet.balance < data['amount']:
                raise serializers.ValidationError({
                    'amount': f"Insufficient balance. Current balance: ₦{wallet.balance}"
                })
        
        return data


class WithdrawalCreateSerializer(serializers.Serializer):
    """Simplified serializer for creating withdrawal requests"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('100.00'))
    bank_name = serializers.CharField(max_length=100)
    account_number = serializers.CharField(max_length=20)
    account_name = serializers.CharField(max_length=100)
    
    def validate_amount(self, value):
        if value < Decimal('100.00'):
            raise serializers.ValidationError("Minimum withdrawal is ₦100.00")
        return value