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