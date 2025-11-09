from django.utils import timezone
from django.contrib import admin
from .models import Wallet, Transaction, PaymentCard, Withdrawal


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'formatted_balance', 'is_active', 'is_locked', 'updated_at']
    list_filter = ['is_active', 'is_locked', 'created_at']
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Balance', {
            'fields': ('balance', 'formatted_balance')
        }),
        ('Status', {
            'fields': ('is_active', 'is_locked')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'user', 'transaction_type', 'formatted_amount',
        'payment_method', 'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'payment_method', 'status', 'created_at']
    search_fields = [
        'reference', 'user__phone_number', 'user__first_name',
        'user__last_name', 'description'
    ]
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'transaction_type', 'payment_method', 'reference')
        }),
        ('Amount', {
            'fields': ('amount', 'formatted_amount', 'balance_before', 'balance_after')
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


@admin.register(PaymentCard)
class PaymentCardAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_type', 'last_four', 'is_default', 'is_active', 'created_at']
    list_filter = ['card_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__phone_number', 'last_four', 'card_token']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'amount', 'bank_name', 'account_number',
        'status', 'created_at'
    ]
    list_filter = ['status', 'bank_name', 'created_at']
    search_fields = [
        'driver__user__phone_number', 'account_number',
        'account_name', 'bank_name'
    ]
    readonly_fields = ['created_at', 'processed_at']
    
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
            'fields': ('status', 'rejection_reason', 'processed_by')
        }),
        ('Related', {
            'fields': ('transaction',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            if obj.status == 'completed' and not obj.processed_by:
                obj.processed_by = request.user
                obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)