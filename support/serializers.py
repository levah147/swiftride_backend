"""
FILE LOCATION: support/serializers.py

Serializers for support app.
"""
from rest_framework import serializers
from .models import (
    SupportCategory,
    SupportTicket,
    TicketMessage,
    TicketAttachment,
    FAQ
)
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info"""
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name']


class SupportCategorySerializer(serializers.ModelSerializer):
    """Serializer for support categories"""
    
    ticket_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportCategory
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'icon',
            'is_active',
            'ticket_count'
        ]
    
    def get_ticket_count(self, obj):
        """Get number of open tickets in category"""
        return obj.tickets.filter(status__in=['open', 'in_progress']).count()


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ticket attachments"""
    
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketAttachment
        fields = [
            'id',
            'file_url',
            'file_name',
            'file_size',
            'file_size_formatted',
            'file_type',
            'uploaded_at'
        ]
        read_only_fields = fields
    
    def get_file_url(self, obj):
        """Get full URL for file"""
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class TicketMessageSerializer(serializers.ModelSerializer):
    """Serializer for ticket messages"""
    
    sender = UserBasicSerializer(read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = TicketMessage
        fields = [
            'id',
            'sender',
            'message',
            'is_staff_reply',
            'is_internal',
            'attachments',
            'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_staff_reply', 'created_at']


class TicketMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ticket messages"""
    
    class Meta:
        model = TicketMessage
        fields = ['ticket', 'message', 'is_internal']
    
    def validate_ticket(self, value):
        """Ensure user can reply to ticket"""
        user = self.context['request'].user
        if not user.is_staff and value.user != user:
            raise serializers.ValidationError("You can only reply to your own tickets")
        return value
    
    def create(self, validated_data):
        """Create message with sender"""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for support tickets"""
    
    user = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'ticket_id',
            'user',
            'category',
            'category_name',
            'subject',
            'description',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'assigned_to',
            'ride',
            'rating',
            'feedback',
            'attachments',
            'message_count',
            'created_at',
            'updated_at',
            'resolved_at',
            'closed_at'
        ]
        read_only_fields = [
            'id',
            'ticket_id',
            'user',
            'assigned_to',
            'created_at',
            'updated_at',
            'resolved_at',
            'closed_at'
        ]
    
    def get_message_count(self, obj):
        """Get number of messages"""
        return obj.messages.count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating support tickets"""
    
    class Meta:
        model = SupportTicket
        fields = [
            'category',
            'subject',
            'description',
            'ride',
            'priority'
        ]
    
    def validate_subject(self, value):
        """Validate subject is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Subject cannot be empty")
        return value.strip()
    
    def validate_description(self, value):
        """Validate description is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty")
        return value.strip()
    
    def create(self, validated_data):
        """Create ticket with user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ticket lists"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    unread_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'ticket_id',
            'category_name',
            'subject',
            'status',
            'status_display',
            'priority',
            'unread_messages',
            'created_at',
            'updated_at'
        ]
    
    def get_unread_messages(self, obj):
        """Get count of unread messages"""
        # Simplified - you might want to track this differently
        return 0


class TicketUpdateSerializer(serializers.Serializer):
    """Serializer for updating ticket status/assignment"""
    
    status = serializers.ChoiceField(
        choices=SupportTicket.STATUS_CHOICES,
        required=False
    )
    priority = serializers.ChoiceField(
        choices=SupportTicket.PRIORITY_CHOICES,
        required=False
    )
    assigned_to = serializers.IntegerField(required=False, allow_null=True)


class TicketRatingSerializer(serializers.Serializer):
    """Serializer for rating tickets"""
    
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True)


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQs"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    helpfulness_ratio = serializers.SerializerMethodField()
    
    class Meta:
        model = FAQ
        fields = [
            'id',
            'category',
            'category_name',
            'question',
            'answer',
            'view_count',
            'helpful_count',
            'not_helpful_count',
            'helpfulness_ratio',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'view_count',
            'helpful_count',
            'not_helpful_count',
            'created_at',
            'updated_at'
        ]
    
    def get_helpfulness_ratio(self, obj):
        """Calculate helpfulness ratio"""
        total = obj.helpful_count + obj.not_helpful_count
        if total == 0:
            return None
        return round((obj.helpful_count / total) * 100, 1)


class SupportStatsSerializer(serializers.Serializer):
    """Serializer for support statistics"""
    
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    in_progress_tickets = serializers.IntegerField()
    resolved_tickets = serializers.IntegerField()
    closed_tickets = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    average_resolution_time = serializers.FloatField()
    user_rating_average = serializers.FloatField()