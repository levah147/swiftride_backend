
"""
FILE LOCATION: safety/serializers.py

API data formatting for safety features
"""

from rest_framework import serializers
from .models import (
    EmergencySOS, TripShare, EmergencyContact,
    SafetyCheck, SafeZone, IncidentReport, SafetySettings
)


class EmergencySOSSerializer(serializers.ModelSerializer):
    """Format SOS data"""
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    user_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EmergencySOS
        fields = [
            'id', 'user', 'user_phone', 'user_name', 'ride',
            'latitude', 'longitude', 'address',
            'status', 'status_display', 'priority',
            'notes', 'contacts_notified',
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'resolved_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.phone_number


class TripShareSerializer(serializers.ModelSerializer):
    """Format trip share data"""
    
    class Meta:
        model = TripShare
        fields = [
            'id', 'ride', 'shared_with', 'share_link',
            'is_active', 'views_count',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'share_link', 'share_token', 'created_at']


class TripShareCreateSerializer(serializers.Serializer):
    """Create trip share"""
    ride_id = serializers.IntegerField()
    contacts = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=5
    )
    access_code = serializers.CharField(max_length=6, required=False, allow_blank=True)


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Format emergency contact"""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'name', 'phone_number', 'email', 'relationship',
            'is_primary', 'notify_sos', 'notify_trip_share',
            'notify_trip_start', 'notify_trip_end',
            'is_verified', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at']
    
    def validate_phone_number(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError(
                "Phone number must include country code (+234...)"
            )
        return value


class SafeZoneSerializer(serializers.ModelSerializer):
    """Format safe zone"""
    
    class Meta:
        model = SafeZone
        fields = [
            'id', 'name', 'zone_type', 'latitude', 'longitude',
            'radius', 'address', 'notify_on_arrival',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class IncidentReportSerializer(serializers.ModelSerializer):
    """Format incident report"""
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    incident_type_display = serializers.CharField(
        source='get_incident_type_display',
        read_only=True
    )
    
    class Meta:
        model = IncidentReport
        fields = [
            'id', 'user', 'user_phone', 'ride',
            'incident_type', 'incident_type_display',
            'description', 'severity', 'evidence_images',
            'latitude', 'longitude', 'status',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at']


class SafetySettingsSerializer(serializers.ModelSerializer):
    """Format safety settings"""
    
    class Meta:
        model = SafetySettings
        fields = [
            'id', 'auto_share_trips', 'auto_safe_zone_notify',
            'enable_safety_checks', 'safety_check_interval',
            'quick_sos', 'silent_sos',
            'notify_contacts_on_ride_start', 'notify_contacts_on_ride_end',
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']

