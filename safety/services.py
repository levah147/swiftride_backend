
"""
FILE LOCATION: safety/services.py
"""
import logging

logger = logging.getLogger(__name__)


def trigger_emergency_alert(sos):
    """Trigger emergency alert and notify contacts"""
    # Notify emergency contacts
    contacts = sos.user.emergency_contacts.all()
    
    for contact in contacts:
        send_emergency_sms(contact.phone_number, sos)
    
    # Notify admin/support team
    notify_admin_team(sos)
    
    logger.info(f"Emergency alert triggered for user {sos.user.id}")


def send_emergency_sms(phone_number, sos):
    """Send emergency SMS to contact"""
    message = f"EMERGENCY: {sos.user.phone_number} has triggered an SOS alert. Location: {sos.address}"
    # Implement SMS sending logic
    pass


def notify_admin_team(sos):
    """Notify admin team of emergency"""
    # Send alert to admin dashboard/team
    pass

 
def send_trip_share_notification(trip_share):
    """Send trip share notifications"""
    for contact in trip_share.shared_with:
        send_trip_share_sms(contact, trip_share)


def send_trip_share_sms(phone_number, trip_share):
    """Send trip share link via SMS"""
    message = f"{trip_share.user.phone_number} is sharing their trip with you. Track here: {trip_share.share_link}"
    # Implement SMS sending
    pass


