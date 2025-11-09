"""
FILE LOCATION: chat/serializers.py

Serializers for chat app.
"""
from rest_framework import serializers
from .models import Conversation, Message, MessageAttachment, TypingIndicator
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for chat"""
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'profile_picture']


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments"""
    
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id',
            'attachment_type',
            'file_url',
            'thumbnail_url',
            'file_name',
            'file_size',
            'file_size_formatted',
            'file_type',
            'width',
            'height',
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
    
    def get_thumbnail_url(self, obj):
        """Get full URL for thumbnail"""
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    
    sender = UserBasicSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'message_type',
            'message_type_display',
            'content',
            'metadata',
            'attachments',
            'is_read',
            'read_at',
            'is_delivered',
            'delivered_at',
            'is_edited',
            'edited_at',
            'is_deleted',
            'reply_to',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'sender',
            'is_read',
            'read_at',
            'is_delivered',
            'delivered_at',
            'is_edited',
            'edited_at',
            'is_deleted',
            'created_at',
            'updated_at'
        ]


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = [
            'conversation',
            'message_type',
            'content',
            'metadata',
            'reply_to'
        ]
    
    def validate_conversation(self, value):
        """Ensure user is participant in conversation"""
        user = self.context['request'].user
        if user != value.rider and user != value.driver:
            raise serializers.ValidationError("You are not a participant in this conversation")
        return value
    
    def validate_content(self, value):
        """Ensure content is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()
    
    def create(self, validated_data):
        """Create message with sender"""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message lists"""
    
    sender_name = serializers.SerializerMethodField()
    has_attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id',
            'sender_name',
            'message_type',
            'content',
            'has_attachments',
            'is_read',
            'is_deleted',
            'created_at'
        ]
    
    def get_sender_name(self, obj):
        """Get sender's display name"""
        if obj.sender.first_name:
            return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return obj.sender.phone_number
    
    def get_has_attachments(self, obj):
        """Check if message has attachments"""
        return obj.attachments.exists()


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""
    
    rider = UserBasicSerializer(read_only=True)
    driver = UserBasicSerializer(read_only=True)
    last_message = MessageListSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'conversation_id',
            'rider',
            'driver',
            'ride',
            'status',
            'last_message',
            'last_message_at',
            'unread_count',
            'other_participant',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.get_unread_count(user)
        return 0
    
    def get_other_participant(self, obj):
        """Get the other participant's info"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            other_user = obj.get_other_participant(user)
            return UserBasicSerializer(other_user).data
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists"""
    
    other_participant = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'conversation_id',
            'other_participant',
            'last_message_preview',
            'last_message_at',
            'unread_count',
            'status'
        ]
    
    def get_other_participant(self, obj):
        """Get other participant's basic info"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            other_user = obj.get_other_participant(user)
            return {
                'id': other_user.id,
                'name': f"{other_user.first_name} {other_user.last_name}".strip() or other_user.phone_number,
                'phone_number': other_user.phone_number,
                'profile_picture': other_user.profile_picture.url if other_user.profile_picture else None
            }
        return None
    
    def get_last_message_preview(self, obj):
        """Get preview of last message"""
        if obj.last_message:
            content = obj.last_message.content
            if obj.last_message.is_deleted:
                return "Message deleted"
            if len(content) > 50:
                return content[:50] + "..."
            return content
        return None
    
    def get_unread_count(self, obj):
        """Get unread count"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.get_unread_count(user)
        return 0


class MarkMessagesReadSerializer(serializers.Serializer):
    """Serializer for marking messages as read"""
    
    message_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    
    mark_all = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Ensure either message_ids or mark_all is provided"""
        if not data.get('message_ids') and not data.get('mark_all'):
            raise serializers.ValidationError(
                "Either 'message_ids' or 'mark_all' must be provided"
            )
        return data


class TypingIndicatorSerializer(serializers.Serializer):
    """Serializer for typing indicators"""
    
    conversation_id = serializers.CharField()
    is_typing = serializers.BooleanField()


class SendMessageSerializer(serializers.Serializer):
    """Serializer for WebSocket message sending"""
    
    conversation_id = serializers.CharField()
    content = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=['text', 'image', 'location'],
        default='text'
    )
    metadata = serializers.JSONField(required=False)
    reply_to_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_content(self, value):
        """Validate content is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty")
        return value.strip()


class UploadAttachmentSerializer(serializers.Serializer):
    """Serializer for uploading message attachments"""
    
    file = serializers.FileField()
    message_id = serializers.IntegerField(required=False)
    
    def validate_file(self, value):
        """Validate file size and type"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Check file type
        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("File type not supported")
        
        return value


class ConversationStatsSerializer(serializers.Serializer):
    """Serializer for conversation statistics"""
    
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    archived_conversations = serializers.IntegerField()
    total_messages_sent = serializers.IntegerField()
    total_messages_received = serializers.IntegerField()
    unread_messages = serializers.IntegerField()