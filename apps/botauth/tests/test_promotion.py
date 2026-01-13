"""
Tests for the draft promotion service and views (Phase 10).
"""

import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from unittest.mock import patch

from apps.botauth.promotion_service import DraftPromotionService
from apps.botauth.models import MatrixUserBinding
from apps.botauth.services import MatrixBindingService
from apps.botauth.bot_service import BotClientService
from apps.events.models import Event
from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient

User = get_user_model()


# Mock the search vector functionality to avoid SQLite incompatibility
def mock_search_vector_update(*args, **kwargs):
    pass


class DraftPromotionServiceTest(TestCase):
    """Tests for the DraftPromotionService."""
    
    def setUp(self):
        # Create doctor
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create another doctor for approval tests
        self.other_doctor = User.objects.create_user(
            username='other_doctor',
            email='other@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create non-doctor user
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@hospital.com',
            password='testpass',
            profession_type=2,  # Nurse
            is_active=True,
            account_status='active'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
        
        # Create draft daily note with mocked search vector
        with patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update):
            self.draft = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description='Test draft via bot',
                content='Test content',
                created_by=self.doctor,
                updated_by=self.doctor,
                is_draft=True,
                draft_created_by_bot=self.bot.client_id,
                draft_delegated_by=self.doctor,
                draft_expires_at=timezone.now() + timedelta(hours=24)
            )
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_promote_draft_success(self, mock_update):
        """Test successful draft promotion."""
        original_created_by = self.draft.created_by
        original_description = self.draft.description
        
        promoted = DraftPromotionService.promote_draft(
            draft=self.draft,
            approving_user=self.doctor
        )
        
        # Check that draft is no longer a draft
        self.assertFalse(promoted.is_draft)
        
        # Check that authorship transferred
        self.assertEqual(promoted.created_by, self.doctor)
        self.assertEqual(promoted.updated_by, self.doctor)
        
        # Check that promotion metadata is set
        self.assertIsNotNone(promoted.draft_promoted_at)
        self.assertEqual(promoted.draft_promoted_by, self.doctor)
        
        # Check that description was cleaned if it had bot references
        # (if it contained 'via bot' or 'rascunho')
        
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_promote_draft_with_modifications(self, mock_update):
        """Test draft promotion with content modifications."""
        modifications = {
            'content': 'Updated content during promotion',
            'description': 'Updated description'
        }
        
        promoted = DraftPromotionService.promote_draft(
            draft=self.draft,
            approving_user=self.doctor,
            modifications=modifications
        )
        
        self.assertEqual(promoted.content, modifications['content'])
        self.assertEqual(promoted.description, modifications['description'])
        self.assertFalse(promoted.is_draft)
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_promote_non_draft_fails(self, mock_update):
        """Test that promoting a non-draft event fails."""
        # Create a definitive event
        definitive_event = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Definitive event',
            content='Definitive content',
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=False
        )
        
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.promote_draft(
                draft=definitive_event,
                approving_user=self.doctor
            )
        
        self.assertIn('not a draft', str(context.exception))
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_promote_expired_draft_fails(self, mock_update):
        """Test that promoting an expired draft fails."""
        # Create an expired draft
        expired_draft = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Expired draft',
            content='Expired content',
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=True,
            draft_created_by_bot=self.bot.client_id,
            draft_delegated_by=self.doctor,
            draft_expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )
        
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.promote_draft(
                draft=expired_draft,
                approving_user=self.doctor
            )
        
        self.assertIn('expired', str(context.exception))
    
    def test_promote_draft_by_non_doctor_fails(self):
        """Test that only doctors can promote drafts."""
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.promote_draft(
                draft=self.draft,
                approving_user=self.nurse
            )
        
        self.assertIn('Only doctors', str(context.exception))
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_promote_draft_by_inactive_user_fails(self, mock_update):
        """Test that inactive users cannot promote drafts."""
        inactive_doctor = User.objects.create_user(
            username='inactive_doctor',
            email='inactive@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=False,
            account_status='active'
        )
        
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.promote_draft(
                draft=self.draft,
                approving_user=inactive_doctor
            )
        
        self.assertIn('not active', str(context.exception))
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_reject_draft_success(self, mock_update):
        """Test successful draft rejection."""
        draft_id = self.draft.id
        
        DraftPromotionService.reject_draft(
            draft=self.draft,
            rejecting_user=self.doctor,
            reason='Test rejection'
        )
        
        # Draft should be deleted
        self.assertFalse(
            DailyNote.objects.filter(id=draft_id).exists()
        )
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_reject_non_draft_fails(self, mock_update):
        """Test that rejecting a non-draft event fails."""
        definitive_event = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Definitive event',
            content='Definitive content',
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=False
        )
        
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.reject_draft(
                draft=definitive_event,
                rejecting_user=self.doctor
            )
        
        self.assertIn('not a draft', str(context.exception))


class DraftPromotionViewsTest(TestCase):
    """Tests for the draft promotion views."""
    
    def setUp(self):
        # Create doctor
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
        
        # Create draft daily note with mocked search vector
        with patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update):
            self.draft = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description='Test draft via bot',
                content='Test content',
                created_by=self.doctor,
                updated_by=self.doctor,
                is_draft=True,
                draft_created_by_bot=self.bot.client_id,
                draft_delegated_by=self.doctor,
                draft_expires_at=timezone.now() + timedelta(hours=24)
            )
        
        # Login
        self.client.login(username='doctor', password='testpass')
    
    def test_my_drafts_view(self):
        """Test the my drafts view."""
        url = reverse('botauth:my_drafts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'botauth/my_drafts.html')
        self.assertContains(response, 'Test draft via bot')
    
    def test_draft_detail_view(self):
        """Test the draft detail view."""
        url = reverse('botauth:draft_detail', kwargs={'pk': self.draft.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'botauth/draft_detail.html')
        self.assertContains(response, 'Test draft via bot')
        self.assertContains(response, 'Revisar Rascunho')
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_draft_promote_view_post(self, mock_update):
        """Test the draft promote view via POST."""
        url = reverse('botauth:draft_promote', kwargs={'pk': self.draft.pk})
        response = self.client.post(url)
        
        # Should redirect after successful promotion
        self.assertEqual(response.status_code, 302)
        
        # Check that draft was promoted
        self.draft.refresh_from_db()
        self.assertFalse(self.draft.is_draft)
        self.assertEqual(self.draft.created_by, self.doctor)
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_draft_reject_view_post(self, mock_update):
        """Test the draft reject view via POST."""
        draft_id = self.draft.id
        url = reverse('botauth:draft_reject', kwargs={'pk': self.draft.pk})
        response = self.client.post(url, {'reason': 'Test rejection'})
        
        # Should redirect after successful rejection
        self.assertEqual(response.status_code, 302)
        
        # Check that draft was deleted
        self.assertFalse(
            DailyNote.objects.filter(id=draft_id).exists()
        )
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_unauthorized_user_cannot_access_others_drafts(self, mock_update):
        """Test that users cannot access drafts delegated to others."""
        # Create another user
        other_user = User.objects.create_user(
            username='other_doctor',
            email='other@hospital.com',
            password='testpass',
            profession_type=0,
            is_active=True,
            account_status='active'
        )
        
        # Create draft delegated to other user
        other_draft = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Other user draft',
            content='Other content',
            created_by=other_user,
            updated_by=other_user,
            is_draft=True,
            draft_created_by_bot=self.bot.client_id,
            draft_delegated_by=other_user,
            draft_expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Try to access other user's draft
        url = reverse('botauth:draft_detail', kwargs={'pk': other_draft.pk})
        response = self.client.get(url)
        
        # Should return 404 since queryset filters by current user
        self.assertEqual(response.status_code, 404)


class DraftPromotionIntegrationTest(TestCase):
    """Integration tests for the complete draft promotion flow."""
    
    def setUp(self):
        # Create doctor with Matrix binding
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0,
            is_active=True,
            account_status='active'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
        
        self.client.login(username='doctor', password='testpass')
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_complete_draft_lifecycle(self, mock_update):
        """Test the complete lifecycle from draft creation to promotion."""
        # Step 1: Create a draft (simulating bot creation)
        draft = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Evolução via bot - Test Patient',
            content='Paciente evoluiu bem',
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=True,
            draft_created_by_bot=self.bot.client_id,
            draft_delegated_by=self.doctor,
            draft_expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Step 2: View draft in list
        list_url = reverse('botauth:my_drafts')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Evolução via bot')
        
        # Step 3: View draft details
        detail_url = reverse('botauth:draft_detail', kwargs={'pk': draft.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paciente evoluiu bem')
        
        # Step 4: Promote draft
        promote_url = reverse('botauth:draft_promote', kwargs={'pk': draft.pk})
        response = self.client.post(promote_url)
        self.assertEqual(response.status_code, 302)
        
        # Step 5: Verify promotion
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.created_by, self.doctor)
        self.assertIsNotNone(draft.draft_promoted_at)
        
        # Step 6: Verify draft is no longer in the list
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Evolução via bot')
    
    @patch('apps.dailynotes.signals.update_search_vector', side_effect=mock_search_vector_update)
    def test_draft_rejection_flow(self, mock_update):
        """Test the draft rejection flow."""
        # Create draft
        draft = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description='Draft to reject',
            content='Content to reject',
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=True,
            draft_created_by_bot=self.bot.client_id,
            draft_delegated_by=self.doctor,
            draft_expires_at=timezone.now() + timedelta(hours=24)
        )
        
        draft_id = draft.id
        
        # Reject draft
        reject_url = reverse('botauth:draft_reject', kwargs={'pk': draft.pk})
        response = self.client.post(reject_url, {'reason': 'Incorrect information'})
        self.assertEqual(response.status_code, 302)
        
        # Verify deletion
        self.assertFalse(
            DailyNote.objects.filter(id=draft_id).exists()
        )