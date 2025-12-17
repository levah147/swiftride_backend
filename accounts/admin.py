from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from decimal import Decimal

from .models import User, OTPVerification


# ==================== CUSTOM FILTERS ====================

class WalletBalanceFilter(SimpleListFilter):
    """
    Custom filter for users with wallet balance.
    
    FIXED: Replaces the broken method-based filter with a proper filter class.
    This allows Django admin to properly filter users by wallet balance.
    """
    title = 'Wallet Balance'
    parameter_name = 'has_balance'

    def lookups(self, request, model_admin):
        """Define filter options."""
        return (
            ('has_balance', 'Has Balance (> ₦0)'),
            ('no_balance', 'No Balance (₦0)'),
        )

    def queryset(self, request, queryset):
        """Filter queryset based on selected option."""
        from payments.models import Wallet
        
        if self.value() == 'has_balance':
            # Get users with wallets that have balance > 0
            wallet_ids_with_balance = Wallet.objects.filter(
                balance__gt=Decimal('0.00')
            ).values_list('user_id', flat=True)
            return queryset.filter(id__in=wallet_ids_with_balance)
        
        elif self.value() == 'no_balance':
            # Get users with no balance or no wallet
            wallet_ids_with_balance = Wallet.objects.filter(
                balance__gt=Decimal('0.00')
            ).values_list('user_id', flat=True)
            return queryset.exclude(id__in=wallet_ids_with_balance)
        
        return queryset


# ==================== USER ADMIN ====================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin configuration for the User model."""

    list_display = [
        'phone_number', 'get_full_name_link', 'email', 'is_driver',
        'is_phone_verified', 'rating', 'total_rides', 
        'wallet_balance_display',  # ✅ Show wallet balance
        'transaction_count_display',  # ✅ Show transaction count
        'created_at'
    ]
    list_filter = [
        'is_driver', 'is_phone_verified', 'is_staff',
        'is_superuser', 'is_active', 'created_at',
        WalletBalanceFilter,  # ✅ FIXED: Use custom filter class instead of method
    ]
    search_fields = ['phone_number', 'first_name', 'last_name', 'email']
    ordering = ['-created_at']
    list_select_related = True  # ✅ Improves query performance
    list_per_page = 25  # ✅ Pagination for better performance
    date_hierarchy = 'created_at'  # ✅ Date drill-down

    fieldsets = (
        ('Personal Information', {
            'fields': ('phone_number', 'first_name', 'last_name', 'email', 'profile_picture')
        }),
        ('Account Status', {
            'fields': ('is_phone_verified', 'is_driver', 'is_active')
        }),
        ('Statistics', {
            'fields': ('rating', 'total_rides')
        }),
        ('Wallet & Transactions', {  # ✅ NEW: Wallet section
            'fields': (
                'wallet_balance_formatted', 
                'transaction_stats',
                'deposit_count'
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    readonly_fields = [
        'created_at', 'updated_at', 'last_login',
        'wallet_balance_formatted',  # ✅ NEW
        'transaction_stats',  # ✅ NEW
        'deposit_count'  # ✅ NEW
    ]

    # ==================== CUSTOM DISPLAY METHODS ====================
    
    def get_full_name_link(self, obj):
        """Display full name as a clickable link to the edit page."""
        url = f"/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.get_full_name())
    get_full_name_link.short_description = 'Full Name'
    get_full_name_link.admin_order_field = 'first_name'

    def wallet_balance_display(self, obj):
        """
        Display wallet balance with color coding in list view.
        
        FIXED: Pre-format balance before passing to format_html()
        format_html() does not support :f format specifiers
        """
        balance = obj.wallet_balance
        
        # Color code based on balance
        if balance >= Decimal('10000.00'):
            color = 'green'  # High balance
            icon = '💰'
        elif balance >= Decimal('1000.00'):
            color = 'blue'  # Medium balance
            icon = '💵'
        elif balance > Decimal('0.00'):
            color = 'orange'  # Low balance
            icon = '💸'
        else:
            color = 'gray'  # Zero balance
            icon = '📭'
        
        # ✅ FIXED: Pre-format the balance string BEFORE format_html()
        formatted_balance = f'{balance:,.2f}'
        
        return format_html(
            '<span style="color:{}; font-weight:600;">{} ₦{}</span>',
            color, icon, formatted_balance
        )
    wallet_balance_display.short_description = 'Wallet Balance'
    wallet_balance_display.admin_order_field = 'wallet__balance'  # Allow sorting

    def transaction_count_display(self, obj):
        """Display transaction count with badge in list view."""
        count = obj.total_transactions
        
        # Color code based on activity
        if count >= 50:
            color = '#2ecc71'  # Very active
        elif count >= 20:
            color = '#3498db'  # Active
        elif count >= 5:
            color = '#f39c12'  # Moderate
        else:
            color = '#95a5a6'  # Low activity
        
        return format_html(
            '<span style="display:inline-block; background-color:{}; color:white; '
            'padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">'
            '{} txns</span>',
            color, count
        )
    transaction_count_display.short_description = 'Transactions'

    def wallet_balance_formatted(self, obj):
        """Display formatted wallet balance in detail view."""
        balance = obj.wallet_balance
        formatted = obj.formatted_wallet_balance
        
        # Add visual indicator
        if balance >= Decimal('10000.00'):
            status = '🟢 High Balance'
        elif balance >= Decimal('1000.00'):
            status = '🔵 Medium Balance'
        elif balance > Decimal('0.00'):
            status = '🟠 Low Balance'
        else:
            status = '⚪ Zero Balance'
        
        return format_html(
            '<div style="font-size:16px; font-weight:600; margin-bottom:5px;">{}</div>'
            '<div style="color:#7f8c8d; font-size:12px;">{}</div>',
            formatted, status
        )
    wallet_balance_formatted.short_description = '💰 Wallet Balance'

    def transaction_stats(self, obj):
        """Display transaction statistics in detail view."""
        total = obj.total_transactions
        deposits = obj.total_deposits
        
        return format_html(
            '<div style="background:#f8f9fa; padding:10px; border-radius:5px;">'
            '<div style="margin-bottom:5px;">'
            '<strong>Total Transactions:</strong> <span style="color:#3498db;">{}</span>'
            '</div>'
            '<div>'
            '<strong>Completed Deposits:</strong> <span style="color:#2ecc71;">{}</span>'
            '</div>'
            '</div>',
            total, deposits
        )
    transaction_stats.short_description = '📊 Transaction Stats'

    def deposit_count(self, obj):
        """Display deposit count in detail view."""
        count = obj.total_deposits
        
        return format_html(
            '<div style="background:#d5f4e6; color:#27ae60; padding:8px 12px; '
            'border-radius:5px; display:inline-block; font-weight:600;">'
            '✅ {} Completed Deposits'
            '</div>',
            count
        )
    deposit_count.short_description = '💳 Deposits'

    # ==================== CUSTOM ACTIONS ====================
    
    actions = ['view_wallet_summary', 'export_as_csv', 'mark_as_verified']

    def view_wallet_summary(self, request, queryset):
        """Admin action: Display wallet summary for selected users."""
        total_balance = sum(user.wallet_balance for user in queryset)
        total_transactions = sum(user.total_transactions for user in queryset)
        
        # Pre-format the balance for display
        formatted_total = f'{total_balance:,.2f}'
        
        self.message_user(
            request,
            f'📊 Summary: {queryset.count()} users | '
            f'Total Balance: ₦{formatted_total} | '
            f'Total Transactions: {total_transactions}'
        )
    view_wallet_summary.short_description = '📊 View wallet summary for selected users'
    
    def export_as_csv(self, request, queryset):
        """Admin action: Export selected users to CSV."""
        import csv
        from django.http import HttpResponse
        
        # Create response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
        
        writer = csv.writer(response)
        # Write header
        writer.writerow([
            'Phone Number', 'First Name', 'Last Name', 'Email',
            'Is Driver', 'Is Verified', 'Rating', 'Total Rides',
            'Wallet Balance', 'Total Transactions', 'Created At'
        ])
        
        # Write data
        for user in queryset:
            writer.writerow([
                user.phone_number,
                user.first_name,
                user.last_name,
                user.email,
                'Yes' if user.is_driver else 'No',
                'Yes' if user.is_phone_verified else 'No',
                user.rating,
                user.total_rides,
                user.wallet_balance,
                user.total_transactions,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_as_csv.short_description = '📥 Export selected users to CSV'
    
    def mark_as_verified(self, request, queryset):
        """Admin action: Mark selected users as phone verified."""
        updated = queryset.update(is_phone_verified=True)
        self.message_user(request, f'{updated} user(s) marked as verified.')
    mark_as_verified.short_description = '✅ Mark as phone verified'


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """Admin interface for managing OTP Verification records."""

    list_display = [
        'phone_number', 'otp_code', 'is_verified',
        'attempts', 'status_badge', 'created_at', 'expires_at'
    ]
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['phone_number', 'otp_code']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    list_per_page = 30  # ✅ Improves admin pagination performance

    def status_badge(self, obj):
        """Display a visually styled badge for OTP status."""
        if obj.is_verified:
            color, text = ('green', 'Verified')
        elif hasattr(obj, 'is_expired') and obj.is_expired():
            color, text = ('red', 'Expired')
        elif obj.attempts >= 5:
            color, text = ('orange', 'Max Attempts')
        else:
            color, text = ('blue', 'Pending')

        return format_html(
            '<span style="display:inline-block; background-color:{}; color:white; '
            'padding:3px 8px; border-radius:4px; font-weight:600;">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'

    actions = ['mark_as_verified', 'delete_expired_otps']

    def mark_as_verified(self, request, queryset):
        """Admin action: Mark selected OTPs as verified."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} OTP(s) marked as verified.')
    mark_as_verified.short_description = '✅ Mark selected as verified'

    def delete_expired_otps(self, request, queryset):
        """Admin action: Delete expired OTPs."""
        deleted = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted[0]} expired OTP(s) deleted.')
    delete_expired_otps.short_description = '🗑️ Delete expired OTPs'
    