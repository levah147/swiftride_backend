"""
Utility functions for sending SMS notifications.
Supports multiple SMS providers: Africa's Talking, Twilio, Termii
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service abstraction layer."""
    
    @staticmethod
    def send_otp(phone_number, otp_code):
        """
        Send OTP via SMS to the given phone number.
        Returns: (success: bool, message: str)
        """
        message = f"Your SwiftRide verification code is: {otp_code}. Valid for 10 minutes. Do not share this code."
        
        # Choose provider based on settings
        provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        if provider == 'africastalking':
            return SMSService._send_via_africastalking(phone_number, message)
        elif provider == 'twilio':
            return SMSService._send_via_twilio(phone_number, message)
        elif provider == 'termii':
            return SMSService._send_via_termii(phone_number, message)
        else:
            # Development: Print to console
            return SMSService._send_via_console(phone_number, otp_code)
    
    @staticmethod
    def _send_via_console(phone_number, otp_code):
        """Print OTP to console for development."""
        print("\n" + "="*60)
        print(f"📱 OTP SMS (CONSOLE)")
        print(f"To: {phone_number}")
        print(f"Code: {otp_code}")
        print("="*60 + "\n")
        return True, "OTP printed to console"
    
    @staticmethod
    def _send_via_africastalking(phone_number, message):
        """Send SMS via Africa's Talking (Recommended for Nigeria)."""
        try:
            import africastalking
            
            # Initialize SDK
            username = settings.AFRICASTALKING_USERNAME
            api_key = settings.AFRICASTALKING_API_KEY
            africastalking.initialize(username, api_key)
            
            # Get SMS service
            sms = africastalking.SMS
            
            # Send message
            response = sms.send(message, [phone_number])
            
            logger.info(f"SMS sent to {phone_number}: {response}")
            return True, "SMS sent successfully"
            
        except Exception as e:
            logger.error(f"Africa's Talking SMS error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def _send_via_twilio(phone_number, message):
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client
            
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token = settings.TWILIO_AUTH_TOKEN
            from_number = settings.TWILIO_PHONE_NUMBER
            
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            
            logger.info(f"Twilio SMS sent to {phone_number}: {message.sid}")
            return True, "SMS sent successfully"
            
        except Exception as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def _send_via_termii(phone_number, message):
        """Send SMS via Termii (Popular in Nigeria)."""
        try:
            import requests
            
            api_key = settings.TERMII_API_KEY
            sender_id = settings.TERMII_SENDER_ID
            
            url = "https://api.ng.termii.com/api/sms/send"
            
            payload = {
                "to": phone_number,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": api_key,
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Termii SMS sent to {phone_number}")
            return True, "SMS sent successfully"
            
        except Exception as e:
            logger.error(f"Termii SMS error: {str(e)}")
            return False, f"Failed to send SMS: {str(e)}"


class EmailService:
    """Email service for notifications (future use)."""
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user."""
        # TODO: Implement email sending
        pass
    
    @staticmethod
    def send_ride_confirmation(user, ride):
        """Send ride confirmation email."""
        # TODO: Implement email sending
        pass