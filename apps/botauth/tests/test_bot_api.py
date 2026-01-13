"""
Tests for bot API functionality.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote
from apps.botauth.models import BotClientProfile, MatrixUserBinding, DelegationAuditLog
from apps.botauth.tokens import DelegatedTokenGenerator
from apps.botauth.bot_service import BotClientService

User = get_user_model()


class BotAPITestCase(APITestCase):
    """Base test case for bot API tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doctor'
        )
        
        # Create test bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            description='Test bot for API testing',
            allowed_scopes=['patient:read', 'dailynote:draft', 'summary:generate'],
            created_by=self.user
        )
        
        # Create matrix binding
        self.matrix_binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:test.com'
        )
        self.matrix_binding.verify()
        
        # Create test patients
        self.patient1 = Patient.objects.create(
            name='Patient One',
            birthday='1990-01-01',
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient2 = Patient.objects.create(
            name='Patient Two',
            birthday='1985-05-15',
            gender='F',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Skip creating daily notes in setup to avoid search vector issues in SQLite tests
        # Tests will create their own notes as needed


class BotPatientListViewTests(BotAPITestCase):
    """Tests for bot patient list view."""
    
    def setUp(self):
        super().setUp()
        # Generate delegated token
        self.token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_list_patients_with_valid_scope(self):
        """Test that bot can list patients with valid scope."""
        url = reverse('botauth:bot_patient_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        patient_names = [patient['name'] for patient in response.data]
        self.assertIn('Patient One', patient_names)
        self.assertIn('Patient Two', patient_names)
    
    def test_list_patients_without_scope_fails(self):
        """Test that request without scope fails."""
        # Generate token without patient:read scope
        token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['dailynote:draft']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('botauth:bot_patient_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_patients_without_token_fails(self):
        """Test that request without authentication fails."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('botauth:bot_patient_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BotPatientDetailViewTests(BotAPITestCase):
    """Tests for bot patient detail view."""
    
    def setUp(self):
        super().setUp()
        self.token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_get_patient_detail_success(self):
        """Test that bot can get patient details."""
        url = reverse('botauth:bot_patient_detail', kwargs={'pk': self.patient1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Patient One')
        self.assertEqual(response.data['gender'], 'M')
    
    def test_get_nonexistent_patient_returns_404(self):
        """Test that requesting non-existent patient returns 404."""
        import uuid
        fake_id = uuid.uuid4()
        url = reverse('botauth:bot_patient_detail', kwargs={'pk': fake_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BotDailyNoteDraftCreateViewTests(BotAPITestCase):
    """Tests for bot daily note draft creation."""
    
    def setUp(self):
        super().setUp()
        self.token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['dailynote:draft']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_create_draft_with_valid_scope(self):
        """Test that bot can create daily note draft."""
        url = reverse('botauth:bot_dailynote_draft')
        data = {
            'patient': str(self.patient1.pk),
            'content': 'Test draft content from bot',
            'event_datetime': timezone.now().isoformat(),
            'description': 'Bot test draft'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_draft'], True)
        self.assertIn('message', response.data)
        self.assertIn('draft_expires_at', response.data)
        
        # Verify the draft was created correctly
        draft = DailyNote.objects.get(pk=response.data['id'])
        self.assertTrue(draft.is_draft)
        self.assertEqual(draft.draft_created_by_bot, self.bot.client_id)
        self.assertEqual(draft.draft_delegated_by, self.user)
        self.assertEqual(draft.created_by, self.user)
    
    def test_create_draft_sets_expiration(self):
        """Test that created draft has proper expiration time."""
        url = reverse('botauth:bot_dailynote_draft')
        data = {
            'patient': str(self.patient1.pk),
            'content': 'Test draft content',
            'event_datetime': timezone.now().isoformat(),
            'description': 'Test draft'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Check expiration is set and is approximately 36 hours from now
        draft = DailyNote.objects.get(pk=response.data['id'])
        self.assertIsNotNone(draft.draft_expires_at)
        
        expires_soon = timezone.now() + timedelta(hours=35)
        expires_late = timezone.now() + timedelta(hours=37)
        self.assertTrue(expires_soon <= draft.draft_expires_at <= expires_late)
    
    def test_create_draft_without_scope_fails(self):
        """Test that creating draft without proper scope fails."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read']  # Wrong scope
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('botauth:bot_dailynote_draft')
        data = {
            'patient': str(self.patient1.pk),
            'content': 'Test draft content',
            'event_datetime': timezone.now().isoformat(),
            'description': 'Test draft'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BotPatientSummaryViewTests(BotAPITestCase):
    """Tests for bot patient summary view."""
    
    def setUp(self):
        super().setUp()
        self.token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read', 'summary:generate']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_generate_summary_success(self):
        """Test that bot can generate patient summary."""
        # Create a non-draft note for testing
        note = DailyNote.objects.create(
            patient=self.patient1,
            content='Test note for summary',
            event_datetime=timezone.now() - timedelta(days=1),
            description='Test note',
            created_by=self.user,
            updated_by=self.user,
            is_draft=False
        )
        
        url = reverse('botauth:bot_patient_summary', kwargs={'pk': self.patient1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('patient', response.data)
        self.assertIn('recent_notes_count', response.data)
        self.assertIn('latest_note_date', response.data)
        self.assertIn('notes_preview', response.data)
        
        # Check that patient data is included
        self.assertEqual(response.data['patient']['name'], 'Patient One')
        
        # Check that notes are included
        self.assertEqual(response.data['recent_notes_count'], 1)
        self.assertTrue(len(response.data['notes_preview']) > 0)
    
    def test_generate_summary_nonexistent_patient_returns_404(self):
        """Test that summary for non-existent patient returns 404."""
        import uuid
        fake_id = uuid.uuid4()
        url = reverse('botauth:bot_patient_summary', kwargs={'pk': fake_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_generate_summary_without_required_scope_fails(self):
        """Test that summary generation without summary:generate scope fails."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read']  # Missing summary:generate
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('botauth:bot_patient_summary', kwargs={'pk': self.patient1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_summary_excludes_draft_notes(self):
        """Test that summary excludes draft notes."""
        # First create a non-draft note
        DailyNote.objects.create(
            patient=self.patient1,
            content='Non-draft note',
            event_datetime=timezone.now() - timedelta(days=1),
            description='Non-draft note',
            created_by=self.user,
            updated_by=self.user,
            is_draft=False
        )
        
        # Create a draft note
        DailyNote.objects.create(
            patient=self.patient1,
            content='Draft note that should not appear in summary',
            event_datetime=timezone.now(),
            description='Draft note',
            created_by=self.user,
            updated_by=self.user,
            is_draft=True,
            draft_expires_at=timezone.now() + timedelta(hours=36)
        )
        
        url = reverse('botauth:bot_patient_summary', kwargs={'pk': self.patient1.pk})
        response = self.client.get(url)
        
        # Should only count non-draft notes
        self.assertEqual(response.data['recent_notes_count'], 1)  # Only the non-draft note


class BotAPIIntegrationTests(BotAPITestCase):
    """Integration tests for bot API workflow."""
    
    def test_complete_bot_workflow(self):
        """Test complete workflow: list patients, view details, create draft, generate summary."""
        # Step 1: Generate token with multiple scopes
        token = DelegatedTokenGenerator.generate_token(
            user=self.user,
            bot_profile=self.bot,
            scopes=['patient:read', 'dailynote:draft', 'summary:generate']
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Step 2: List patients
        list_url = reverse('botauth:bot_patient_list')
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 2)
        
        # Step 3: Get patient details
        patient_id = list_response.data[0]['id']
        detail_url = reverse('botauth:bot_patient_detail', kwargs={'pk': patient_id})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        
        # Step 4: Create a draft
        draft_url = reverse('botauth:bot_dailynote_draft')
        draft_data = {
            'patient': patient_id,
            'content': 'Integration test draft from bot',
            'event_datetime': timezone.now().isoformat(),
            'description': 'Integration test draft'
        }
        draft_response = self.client.post(draft_url, draft_data, format='json')
        self.assertEqual(draft_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(draft_response.data['is_draft'])
        
        # Step 5: Generate summary (should exclude the just-created draft)
        summary_url = reverse('botauth:bot_patient_summary', kwargs={'pk': patient_id})
        summary_response = self.client.get(summary_url)
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        
        # Verify audit log was created for delegation
        audit_log = DelegationAuditLog.objects.filter(
            bot_client_id=self.bot.client_id,
            user=self.user,
            status=DelegationAuditLog.Status.ISSUED
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.granted_scopes, ['patient:read', 'dailynote:draft', 'summary:generate'])