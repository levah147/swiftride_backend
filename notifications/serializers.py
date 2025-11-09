"""
FILE LOCATION: notifications/serializers.py

Serializers for notifications app.
Handles data serialization for API endpoints.
"""
from rest_framework import serializers
from .models import (
    PushToken,
    Notification,
    NotificationPreference,
    SMSLog,
    EmailLog
)
from django.contrib.auth import get_user_model

User = get_user_model()


class PushTokenSerializer(serializers.ModelSerializer):
    """Serializer for push notification tokens"""
    
    class Meta:
        model = PushToken
        fields = [
            'id',
            'token',
            'platform',
            'device_id',
            'device_name',
            'is_active',
            'created_at',
            'last_used'
        ]
        read_only_fields = ['id', 'created_at', 'last_used', 'is_active']
    
    def validate_token(self, value):
        """Ensure token is not empty"""
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid token format")
        return value
    
    def create(self, validated_data):
        """Create or update push token"""
        user = self.context['request'].user
        token = validated_data.get('token')
        
        # Deactivate old token if exists
        PushToken.objects.filter(token=token).update(is_active=False)
        
        # Create new token
        validated_data['user'] = user
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'body',
            'data',
            'is_read',
            'read_at',
            'sent_via_push',
            'sent_via_sms',
            'sent_via_email',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'sent_via_push',
            'sent_via_sms',
            'sent_via_email',
            'created_at',
            'read_at'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification lists"""
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'body',
            'is_read',
            'created_at'
        ]
        read_only_fields = fields


class MarkNotificationReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=False,
        help_text="List of notification IDs to mark as read"
    )
    
    mark_all = serializers.BooleanField(
        default=False,
        help_text="Mark all notifications as read"
    )
    
    def validate(self, data):
        """Ensure either notification_ids or mark_all is provided"""
        if not data.get('notification_ids') and not data.get('mark_all'):
            raise serializers.ValidationError(
                "Either 'notification_ids' or 'mark_all' must be provided"
            )
        return data


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'push_ride_updates',
            'push_payment_updates',
            'push_promotional',
            'push_enabled',
            'sms_ride_updates',
            'sms_payment_updates',
            'sms_enabled',
            'email_ride_updates',
            'email_payment_updates',
            'email_promotional',
            'email_enabled',
            'inapp_enabled',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        """Update notification preferences"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SendPushNotificationSerializer(serializers.Serializer):
    """Serializer for sending push notifications"""
    
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of user IDs to send notification to"
    )
    
    user_type = serializers.ChoiceField(
        choices=['all', 'riders', 'drivers'],
        required=False,
        help_text="Send to all users of a specific type"
    )
    
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    
    data = serializers.JSONField(
        required=False,
        help_text="Additional data payload"
    )
    
    notification_type = serializers.ChoiceField(
        choices=[choice[0] for choice in Notification.NOTIFICATION_TYPES],
        default='general'
    )
    
    def validate(self, data):
        """Ensure either user_ids or user_type is provided"""
        if not data.get('user_ids') and not data.get('user_type'):
            raise serializers.ValidationError(
                "Either 'user_ids' or 'user_type' must be provided"
            )
        return data


class SMSLogSerializer(serializers.ModelSerializer):
    """Serializer for SMS logs"""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = SMSLog
        fields = [
            'id',
            'phone_number',
            'message',
            'status',
            'status_display',
            'provider',
            'cost',
            'error_message',
            'created_at',
            'delivered_at'
        ]
        read_only_fields = fields


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email logs"""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = EmailLog
        fields = [
            'id',
            'recipient_email',
            'subject',
            'status',
            'status_display',
            'error_message',
            'created_at',
            'sent_at',
            'delivered_at'
        ]
        read_only_fields = fields


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    today_count = serializers.IntegerField()
    this_week_count = serializers.IntegerField()
    
    # By type
    ride_notifications = serializers.IntegerField()
    payment_notifications = serializers.IntegerField()
    system_notifications = serializers.IntegerField()


class BulkSendNotificationSerializer(serializers.Serializer):
    """Serializer for bulk sending notifications"""
    
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs"
    )
    
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=[choice[0] for choice in Notification.NOTIFICATION_TYPES]
    )
    
    send_push = serializers.BooleanField(default=True)
    send_sms = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=False)
    
    data = serializers.JSONField(required=False)
    
    def validate_recipients(self, value):
        """Validate recipients list"""
        if len(value) == 0:
            raise serializers.ValidationError("Recipients list cannot be empty")
        if len(value) > 1000:
            raise serializers.ValidationError("Cannot send to more than 1000 users at once")
        return value