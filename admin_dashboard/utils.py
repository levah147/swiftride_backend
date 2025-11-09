"""
FILE LOCATION: admin_dashboard/utils.py
"""

def log_admin_action(admin, action_type, target_type, target_id, reason=''):
    """Helper to log admin actions"""
    from .models import AdminAction
    
    AdminAction.objects.create(
        admin=admin,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        reason=reason
    )





