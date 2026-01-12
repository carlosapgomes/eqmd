# Phase 08 – Bot API Layer

## Goal

Create REST API endpoints for bot operations: reading patient data, creating drafts, and generating summaries.

## Prerequisites

- Phase 07 completed (DRF Authentication Backend)
- All existing tests passing

## Tasks

### Task 8.1: Create API Serializers

Create `apps/botauth/serializers.py`:

```python
"""
Serializers for bot API endpoints.
"""

from rest_framework import serializers
from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote
from apps.events.models import Event


class PatientReadSerializer(serializers.ModelSerializer):
    """Serializer for reading patient data (bot-safe)."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'record_number', 'birth_date', 'gender',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = fields


class DailyNoteDraftSerializer(serializers.ModelSerializer):
    """Serializer for creating daily note drafts."""
    
    class Meta:
        model = DailyNote
        fields = ['patient', 'content', 'event_datetime', 'description']
    
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
```

### Task 8.2: Create Bot API Views

Create `apps/botauth/bot_api_views.py`:

```python
"""
API views for bot operations.
"""

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from .authentication import DelegatedJWTAuthentication
from .permissions import HasScope, IsDelegatedRequest
from .serializers import PatientReadSerializer, DailyNoteDraftSerializer

from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote


class BotPatientListView(ListAPIView):
    """
    List patients for bot (requires patient:read scope).
    
    GET /auth/api/bot/patients/
    """
    
    authentication_classes = [DelegatedJWTAuthentication]
    permission_classes = [IsDelegatedRequest, HasScope]
    required_scopes = ['patient:read']
    serializer_class = PatientReadSerializer
    
    def get_queryset(self):
        # Return active patients only
        return Patient.objects.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.OUTPATIENT]
        ).order_by('-updated_at')[:100]


class BotPatientDetailView(RetrieveAPIView):
    """
    Get patient details (requires patient:read scope).
    
    GET /auth/api/bot/patients/<uuid:pk>/
    """
    
    authentication_classes = [DelegatedJWTAuthentication]
    permission_classes = [IsDelegatedRequest, HasScope]
    required_scopes = ['patient:read']
    serializer_class = PatientReadSerializer
    queryset = Patient.objects.all()


class BotDailyNoteDraftCreateView(CreateAPIView):
    """
    Create a daily note draft (requires dailynote:draft scope).
    
    POST /auth/api/bot/dailynotes/draft/
    """
    
    authentication_classes = [DelegatedJWTAuthentication]
    permission_classes = [IsDelegatedRequest, HasScope]
    required_scopes = ['dailynote:draft']
    serializer_class = DailyNoteDraftSerializer
    
    def perform_create(self, serializer):
        # Set draft fields
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            is_draft=True,
            draft_created_by_bot=self.request.actor,
            draft_delegated_by=self.request.user,
            draft_expires_at=timezone.now() + timedelta(hours=36),
            description=f"Rascunho criado via bot sob delegação de {self.request.user.get_full_name()}"
        )
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        
        # Enhance response
        response.data['message'] = (
            'Draft created successfully. '
            'It will expire in 36 hours if not reviewed.'
        )
        response.data['is_draft'] = True
        
        return response


class BotPatientSummaryView(APIView):
    """
    Generate patient summary (requires summary:generate scope).
    
    GET /auth/api/bot/patients/<uuid:pk>/summary/
    """
    
    authentication_classes = [DelegatedJWTAuthentication]
    permission_classes = [IsDelegatedRequest, HasScope]
    required_scopes = ['patient:read', 'summary:generate']
    
    def get(self, request, pk):
        try:
            patient = Patient.objects.get(pk=pk)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate summary from recent notes
        recent_notes = DailyNote.objects.filter(
            patient=patient,
            is_draft=False
        ).order_by('-event_datetime')[:10]
        
        summary = {
            'patient': PatientReadSerializer(patient).data,
            'recent_notes_count': recent_notes.count(),
            'latest_note_date': recent_notes.first().event_datetime if recent_notes.exists() else None,
            'notes_preview': [
                {
                    'date': note.event_datetime,
                    'excerpt': note.content[:200] + '...' if len(note.content) > 200 else note.content
                }
                for note in recent_notes[:5]
            ]
        }
        
        return Response(summary)
```

### Task 8.3: Add URL Routes

Update `apps/botauth/urls.py`:

```python
from django.urls import path
from . import views
from .api_views import DelegatedTokenView
from .bot_api_views import (
    BotPatientListView, BotPatientDetailView,
    BotDailyNoteDraftCreateView, BotPatientSummaryView
)

app_name = 'botauth'

urlpatterns = [
    # Human-facing views
    path('matrix/bind/', views.MatrixBindingCreateView.as_view(), name='binding_create'),
    path('matrix/status/', views.MatrixBindingStatusView.as_view(), name='binding_status'),
    path('matrix/verify/<str:token>/', views.MatrixBindingVerifyView.as_view(), name='binding_verify'),
    path('matrix/revoke/<uuid:pk>/', views.MatrixBindingDeleteView.as_view(), name='binding_delete'),
    
    # Delegation endpoint
    path('api/delegated-token/', DelegatedTokenView.as_view(), name='delegated_token'),
    
    # Bot API endpoints
    path('api/bot/patients/', BotPatientListView.as_view(), name='bot_patient_list'),
    path('api/bot/patients/<uuid:pk>/', BotPatientDetailView.as_view(), name='bot_patient_detail'),
    path('api/bot/patients/<uuid:pk>/summary/', BotPatientSummaryView.as_view(), name='bot_patient_summary'),
    path('api/bot/dailynotes/draft/', BotDailyNoteDraftCreateView.as_view(), name='bot_dailynote_draft'),
]
```

## Acceptance Criteria

- [ ] Bot can list patients with `patient:read` scope
- [ ] Bot can view patient details with `patient:read` scope  
- [ ] Bot can create daily note drafts with `dailynote:draft` scope
- [ ] Bot can generate summaries with `summary:generate` scope
- [ ] All drafts are marked with `is_draft=True`
- [ ] All drafts have expiration time set
- [ ] Human users via session auth can still access these endpoints
- [ ] Missing scopes return 403 Forbidden
- [ ] All tests pass

## Notes

- This phase requires the Event model changes from Phase 09
- Bot endpoints are separate from human endpoints for clarity
- All bot-created content is clearly marked as drafts
