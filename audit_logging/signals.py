"""
FILE LOCATION: audit_logging/signals.py

Signal handlers for automatic audit logging.
Logs critical model changes automatically.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()


# Track which models should be audited
AUDITED_MODELS = [
    'rides.Ride',
    'payments.Transaction',
    'payments.Withdrawal',
    'drivers.Driver',
    'accounts.User',
]


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log model save operations"""
    model_name = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    if model_name in AUDITED_MODELS:
        action_type = 'create' if created else 'update'
        
        # Get user from instance if available
        user = None
        if hasattr(instance, 'user'):
            user = instance.user
        elif hasattr(instance, 'created_by'):
            user = instance.created_by
        
        description = f"{action_type.capitalize()}d {sender._meta.verbose_name}"
        if hasattr(instance, 'id'):
            description += f" #{instance.id}"
        
        try:
            AuditLog.log_action(
                user=user,
                action_type=action_type,
                content_object=instance,
                description=description,
                severity='medium'
            )
        except Exception:
            # Don't break the save operation if logging fails
            pass


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log model delete operations"""
    model_name = f"{sender._meta.app_label}.{sender._meta.model_name}"
    
    if model_name in AUDITED_MODELS:
        # Get user from instance if available
        user = None
        if hasattr(instance, 'user'):
            user = instance.user
        elif hasattr(instance, 'deleted_by'):
            user = instance.deleted_by
        
        description = f"Deleted {sender._meta.verbose_name}"
        if hasattr(instance, 'id'):
            description += f" #{instance.id}"
        
        try:
            AuditLog.log_action(
                user=user,
                action_type='delete',
                content_object=instance,
                description=description,
                severity='high'
            )
        except Exception:
            # Don't break the delete operation if logging fails
            pass

