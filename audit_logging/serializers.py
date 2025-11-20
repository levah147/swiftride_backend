"""
FILE LOCATION: audit_logging/serializers.py
Serializers for audit logging API.
"""
from rest_framework import serializers
from .models import AuditLog, SecurityEvent
from accounts.serializers import UserProfileSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog"""
    user = UserProfileSerializer(read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action_type', 'severity', 'description',
            'content_type_name', 'object_id', 'ip_address', 'user_agent',
            'request_path', 'request_method', 'metadata', 'timestamp',
            'success', 'error_message'
        ]
        read_only_fields = fields


class SecurityEventSerializer(serializers.ModelSerializer):
    """Serializer for SecurityEvent"""
    user = UserProfileSerializer(read_only=True)
    resolved_by_user = UserProfileSerializer(source='resolved_by', read_only=True)
    
    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'user', 'event_type', 'severity', 'description',
            'ip_address', 'user_agent', 'request_path', 'request_method',
            'metadata', 'timestamp', 'resolved', 'resolved_at',
            'resolved_by_user', 'resolution_notes'
        ]
        read_only_fields = fields

