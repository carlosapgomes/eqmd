"""S2 R6: expired-draft cleanup leaves null-expiry drafts untouched (D9).

Human drafts never auto-expire (``draft_expires_at`` stays null), so the bot
cleanup command must only remove drafts that carry an expiry in the past.
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event
from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

User = get_user_model()


class CleanupExpiredDraftsTests(TestCase):
    """R6: null-expiry human drafts survive ``cleanup_expired_drafts``."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="cleanupdoctor",
            email="cleanupdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = Patient.objects.create(
            name="Cleanup Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_draft(self, *, description, draft_expires_at=None):
        return SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description=description,
            content=description,
            is_draft=True,
            draft_expires_at=draft_expires_at,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    def _run_cleanup(self):
        call_command("cleanup_expired_drafts", stdout=StringIO())

    def test_null_expiry_draft_survives_cleanup(self):
        draft = self._create_draft(description="Rascunho sem expiração")

        self._run_cleanup()

        self.assertTrue(SimpleNote.objects.with_drafts().filter(pk=draft.pk).exists())

    def test_expired_draft_is_cleaned_up(self):
        expired = self._create_draft(
            description="Rascunho expirado",
            draft_expires_at=timezone.now() - timedelta(hours=1),
        )

        self._run_cleanup()

        self.assertFalse(Event.objects.with_drafts().filter(pk=expired.pk).exists())
        self.assertTrue(Event.all_objects.get(pk=expired.pk).is_deleted)
