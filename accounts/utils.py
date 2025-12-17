"""
Utility functions for sending SMS and Email notifications.
Supports multiple SMS providers: Africa's Talking, Twilio, Termii
Includes retry mechanism with exponential backoff for reliability.
"""
import logging
import time
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service abstraction layer."""
    
    @staticmethod
    def send_otp(phone_number, otp_code):
        """
        Send OTP via SMS to the given phone number with retry mechanism.
        Returns: (success: bool, message: str)
        """
        otp_settings = getattr(settings, 'OTP_SETTINGS', {})
        expiration_min = otp_settings.get('EXPIRATION_MINUTES', 10)
        
        message = f"Your SwiftRide verification code is: {otp_code}. Valid for {expiration_min} minutes. Do not share this code."
        
        # Choose provider based on settings
        provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        # Get retry settings
        max_retries = otp_settings.get('SMS_MAX_RETRIES', 3)
        use_backoff = otp_settings.get('SMS_RETRY_EXPONENTIAL_BACKOFF', True)
        base_delay = otp_settings.get('SMS_RETRY_DELAY_SECONDS', 5)
        
        # Try sending with retries
        for attempt in range(max_retries):
            try:
                if provider == 'africastalking':
                    success, msg = SMSService._send_via_africastalking(phone_number, message)
                elif provider == 'twilio':
                    success, msg = SMSService._send_via_twilio(phone_number, message)
                elif provider == 'termii':
                    success, msg = SMSService._send_via_termii(phone_number, message)
                else:
                    # Development: Print to console
                    success, msg = SMSService._send_via_console(phone_number, otp_code)
                
                if success:
                    logger.info(f"SMS sent successfully on attempt {attempt + 1}")
                    return True, msg
                
                # If failed and not last attempt, wait before retry
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) if use_backoff else base_delay
                    logger.warning(f"SMS attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"SMS attempt {attempt + 1} error: {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) if use_backoff else base_delay
                    time.sleep(delay)
        
        # All retries failed
        logger.error(f"SMS failed after {max_retries} attempts")
        return False, f"Failed to send SMS after {max_retries} attempts"
    
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
    """Email service for user notifications."""
    
    @staticmethod
    def send_welcome_email(user):
        """
        Send welcome email to new user.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            if not user.email:
                logger.warning(f"User {user.phone_number} has no email address")
                return False
            
            subject = 'Welcome to SwiftRide!'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            # HTML content
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #4CAF50;">Welcome to SwiftRide, {user.get_full_name()}!</h2>
                    <p>We're excited to have you on board.</p>
                    <p>With SwiftRide, you can:</p>
                    <ul>
                        <li>Book rides quickly and securely</li>
                        <li>Track your driver in real-time</li>
                        <li>Pay easily with your wallet</li>
                        <li>Earn loyalty rewards</li>
                    </ul>
                    <p>Your phone number: <strong>{user.phone_number}</strong></p>
                    <p>Get started by topping up your wallet and booking your first ride!</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">SwiftRide - Your reliable ride partner</p>
                </body>
            </html>
            """
            
            # Plain text version
            text_message = f"""
            Welcome to SwiftRide, {user.get_full_name()}!
            
            We're excited to have you on board.
            
            With SwiftRide, you can:
            - Book rides quickly and securely
            - Track your driver in real-time
            - Pay easily with your wallet
            - Earn loyalty rewards
            
            Your phone number: {user.phone_number}
            
            Get started by topping up your wallet and booking your first ride!
            
            SwiftRide - Your reliable ride partner
            """
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Welcome email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, reset_token):
        """
        Send password reset email.
        
        Args:
            user: User instance
            reset_token: Password reset token
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            if not user.email:
                return False
            
            subject = 'Reset Your SwiftRide Password'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            # In production, replace with actual reset URL
            reset_url = f"https://swiftride.com/reset-password?token={reset_token}"
            
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Password Reset Request</h2>
                    <p>Hello {user.get_full_name()},</p>
                    <p>We received a request to reset your password for your SwiftRide account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="margin: 30px 0;">
                        <a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link:</p>
                    <p style="color: #666;">{reset_url}</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">If you didn't request this, please ignore this email.</p>
                </body>
            </html>
            """
            
            text_message = f"""
            Password Reset Request
            
            Hello {user.get_full_name()},
            
            We received a request to reset your password for your SwiftRide account.
            
            Click this link to reset your password:
            {reset_url}
            
            If you didn't request this, please ignore this email.
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Password reset email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False
    
    @staticmethod
    def send_ride_confirmation(user, ride):
        """
        Send ride confirmation email.
        
        Args:
            user: User instance
            ride: Ride instance
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            if not user.email:
                return False
            
            subject = f'Ride Confirmation - SwiftRide #{ride.id}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #4CAF50;">Ride Confirmed!</h2>
                    <p>Hello {user.get_full_name()},</p>
                    <p>Your ride has been confirmed.</p>
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <p><strong>Ride #:</strong> {ride.id}</p>
                        <p><strong>Pickup:</strong> {ride.pickup_address or 'Location provided'}</p>
                        <p><strong>Dropoff:</strong> {ride.dropoff_address or 'Location provided'}</p>
                        <p><strong>Driver:</strong> {ride.driver.user.get_full_name() if ride.driver else 'Assigning...'}</p>
                        <p><strong>Estimated Fare:</strong> ₦{ride.estimated_fare}</p>
                    </div>
                    <p>Track your ride in the SwiftRide app!</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">SwiftRide - Your reliable ride partner</p>
                </body>
            </html>
            """
            
            text_message = f"""
            Ride Confirmed!
            
            Hello {user.get_full_name()},
            
            Your ride has been confirmed.
            
            Ride #: {ride.id}
            Pickup: {ride.pickup_address or 'Location provided'}
            Dropoff: {ride.dropoff_address or 'Location provided'}
            Driver: {ride.driver.user.get_full_name() if ride.driver else 'Assigning...'}
            Estimated Fare: ₦{ride.estimated_fare}
            
            Track your ride in the SwiftRide app!
            
            SwiftRide - Your reliable ride partner
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Ride confirmation email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send ride confirmation email: {str(e)}")
            return False