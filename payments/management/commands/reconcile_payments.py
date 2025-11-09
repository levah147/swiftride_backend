
"""
FILE LOCATION: payments/management/commands/reconcile_payments.py
Management command to reconcile payment transactions.
"""
from django.core.management.base import BaseCommand
from payments.models import Wallet, Transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Reconcile wallet balances with transaction history'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting payment reconciliation...')
        
        wallets = Wallet.objects.all()
        issues = []
        
        for wallet in wallets:
            # Calculate expected balance from transactions
            transactions = Transaction.objects.filter(
                user=wallet.user,
                status='completed'
            )
            
            calculated_balance = Decimal('0.00')
            for txn in transactions:
                if txn.transaction_type in ['deposit', 'ride_earning', 'bonus', 'refund']:
                    calculated_balance += txn.amount
                elif txn.transaction_type in ['withdrawal', 'ride_payment', 'commission']:
                    calculated_balance -= txn.amount
            
            if calculated_balance != wallet.balance:
                issues.append({
                    'user': wallet.user.phone_number,
                    'wallet_balance': wallet.balance,
                    'calculated_balance': calculated_balance,
                    'difference': wallet.balance - calculated_balance
                })
        
        if issues:
            self.stdout.write(self.style.WARNING(f'Found {len(issues)} discrepancies:'))
            for issue in issues:
                self.stdout.write(f"  - {issue['user']}: "
                                f"Wallet: ₦{issue['wallet_balance']}, "
                                f"Calculated: ₦{issue['calculated_balance']}, "
                                f"Diff: ₦{issue['difference']}")
        else:
            self.stdout.write(self.style.SUCCESS('All wallets reconciled successfully!'))



