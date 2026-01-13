"""
Serializers for bot API endpoints.
"""

from rest_framework import serializers
from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote
from apps.events.models import Event


class PatientReadSerializer(serializers.ModelSerializer):
    """Serializer for reading patient data (bot-safe)."""
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'birthday', 'gender', 'created_at'
        ]
        read_only_fields = fields


class DailyNoteDraftSerializer(serializers.ModelSerializer):
    """Serializer for creating daily note drafts."""
    
    class Meta:
        model = DailyNote
        fields = ['id', 'patient', 'content', 'event_datetime', 'description', 'is_draft', 'draft_expires_at']
        read_only_fields = ['id', 'is_draft', 'draft_expires_at']
    
    def create(self, validated_data):
        # Force draft status
        validated_data['is_draft'] = True
        validated_data['draft_expires_at'] = self._get_expiration()
        return super().create(validated_data)
    
    def _get_expiration(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() + timedelta(hours=36)


class DraftResponseSerializer(serializers.Serializer):
    """Response serializer for draft creation."""
    
    id = serializers.UUIDField()
    is_draft = serializers.BooleanField()
    draft_expires_at = serializers.DateTimeField()
    message = serializers.CharField()