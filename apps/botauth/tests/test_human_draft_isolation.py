"""Bidirectional bot isolation: botauth accepts bot drafts only (S1 R6).

The promote/reject boundaries (view querysets and the promotion service) must
deny human drafts (``draft_created_by_bot == ""``) without changing
authorship, draft state, or deletion state. Genuine bot drafts keep the
promotion flow covered by ``apps.botauth.tests.test_promotion``.
"""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.botauth.promotion_service import DraftPromotionService
from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient

User = get_user_model()


def no_search_vector(*args, **kwargs):
    """Skip the search-vector update; isolation is not about the index."""
    return


class HumanDraftIsolationTestBase(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username="isolationdoctor",
            email="isolationdoctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            account_status="active",
            password_change_required=False,
            terms_accepted=True,
        )
        self.student = User.objects.create_user(
            username="isolationstudent",
            email="isolationstudent@example.com",
            password="testpass123",
            profession_type=User.STUDENT,
            account_status="active",
            password_change_required=False,
            terms_accepted=True,
        )
        self.patient = Patient.objects.create(
            name="Isolation Patient",
            birthday=date(1990, 1, 1),
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        with patch("apps.dailynotes.signals.update_search_vector", no_search_vector):
            self.human_draft = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description="Student draft awaiting approval",
                content="Student draft content",
                created_by=self.student,
                updated_by=self.student,
                is_draft=True,
                draft_created_by_bot="",
            )

    def _reload(self):
        return DailyNote.all_objects.get(pk=self.human_draft.pk)


class HumanDraftServiceIsolationTests(HumanDraftIsolationTestBase):
    """R6: the promotion service refuses human drafts before mutating them."""

    def test_promote_refuses_human_draft(self):
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.promote_draft(
                draft=self.human_draft, approving_user=self.doctor
            )

        self.assertIn("bot", str(context.exception))
        stored = self._reload()
        self.assertTrue(stored.is_draft)
        self.assertEqual(stored.created_by, self.student)
        self.assertIsNone(stored.draft_promoted_at)
        self.assertIsNone(stored.draft_promoted_by)

    def test_reject_refuses_human_draft(self):
        with self.assertRaises(ValueError) as context:
            DraftPromotionService.reject_draft(
                draft=self.human_draft, rejecting_user=self.doctor, reason="nope"
            )

        self.assertIn("bot", str(context.exception))
        stored = self._reload()
        self.assertTrue(stored.is_draft)
        self.assertEqual(stored.created_by, self.student)
        self.assertFalse(stored.is_deleted)


class HumanDraftViewIsolationTests(HumanDraftIsolationTestBase):
    """R6: the promote/reject querysets exclude human drafts (404, no change)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor)

    def test_promote_view_hides_human_draft(self):
        url = reverse("botauth:draft_promote", kwargs={"pk": self.human_draft.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        stored = self._reload()
        self.assertTrue(stored.is_draft)
        self.assertEqual(stored.created_by, self.student)
        self.assertIsNone(stored.draft_promoted_by)

    def test_reject_view_hides_human_draft(self):
        url = reverse("botauth:draft_reject", kwargs={"pk": self.human_draft.pk})

        response = self.client.post(url, {"reason": "nope"})

        self.assertEqual(response.status_code, 404)
        stored = self._reload()
        self.assertTrue(stored.is_draft)
        self.assertFalse(stored.is_deleted)
