from django.utils import timezone
from django.contrib import admin
from .models import Wallet, Transaction, PaymentCard, Withdrawal


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """
    Admin interface for Wallet model.
    
    FIXED: Moved 'formatted_balance' from fieldsets to readonly_fields
    - formatted_balance is a @property method, not a database field
    - Can only be displayed in readonly_fields, not edited in forms
    """
    list_display = ['user', 'balance', 'is_active', 'is_locked', 'updated_at']
    list_filter = ['is_active', 'is_locked', 'created_at']
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'formatted_balance']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Balance', {
            'fields': ('balance',)  # ✅ FIXED: Removed 'formatted_balance' - it's a property
        }),
        ('Status', {
            'fields': ('is_active', 'is_locked')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def formatted_balance(self, obj):
        """Display formatted balance in readonly field"""
        return obj.formatted_balance
    formatted_balance.short_description = 'Formatted Balance'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for Transaction model.
    
    FIXED: Moved 'formatted_amount' from fieldsets to readonly_fields
    - formatted_amount is a @property method, not a database field
    - Can only be displayed in readonly_fields, not edited in forms
    """
    list_display = [
        'reference', 'user', 'transaction_type', 'amount',
        'payment_method', 'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'payment_method', 'status', 'created_at']
    search_fields = [
        'reference', 'user__phone_number', 'user__first_name',
        'user__last_name', 'description'
    ]
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'formatted_amount']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'transaction_type', 'payment_method', 'reference')
        }),
        ('Amount', {
            'fields': ('amount', 'balance_before', 'balance_after')  # ✅ FIXED: Removed 'formatted_amount'
        }),
        ('Commission & Pricing', {
            'fields': ('base_fare', 'surge_multiplier', 'surge_amount', 'fuel_adjustment', 'commission_rate', 'commission_amount'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'description')
        }),
        ('Related', {
            'fields': ('ride', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def formatted_amount(self, obj):
        """Display formatted amount in readonly field"""
        return obj.formatted_amount
    formatted_amount.short_description = 'Formatted Amount'


@admin.register(PaymentCard)
class PaymentCardAdmin(admin.ModelAdmin):
    """Admin interface for PaymentCard model"""
    list_display = ['user', 'card_type', 'last_four', 'is_default', 'is_active', 'created_at']
    list_filter = ['card_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__phone_number', 'last_four', 'card_token']
    readonly_fields = ['created_at', 'updated_at', 'card_token']
    
    fieldsets = (
        ('Card Info', {
            'fields': ('user', 'card_type', 'last_four', 'card_token')
        }),
        ('Expiry', {
            'fields': ('expiry_month', 'expiry_year')
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    """Admin interface for Withdrawal model"""
    list_display = [
        'driver', 'amount', 'bank_name', 'status',
        'created_at', 'processed_at'
    ]
    list_filter = ['status', 'bank_name', 'created_at']
    search_fields = [
        'driver__user__phone_number', 'account_number',
        'account_name', 'bank_name'
    ]
    readonly_fields = ['created_at', 'processed_at', 'processed_by']
    
    fieldsets = (
        ('Driver Info', {
            'fields': ('driver',)
        }),
        ('Amount', {
            'fields': ('amount',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'account_name')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('Related', {
            'fields': ('transaction',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-set processed_by and processed_at when status changes to completed"""
        if change and 'status' in form.changed_data:
            if obj.status == 'completed' and not obj.processed_by:
                obj.processed_by = request.user
                obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)