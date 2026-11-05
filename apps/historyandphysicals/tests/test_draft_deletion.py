"""S4 R1: HistoryAndPhysical draft deletion (rights per state, method per history).

Never-finalized drafts are hard-deleted by their creator or by any
doctor/resident with patient access (including cleanup of rotated-out
students, no time limit); anything ever finalized keeps the soft-delete path
with draft-state rights (design D7).
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import HistoryAndPhysical

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class HistoryAndPhysicalDraftDeletionTests(TestCase):
    """R1: hard delete for never-finalized drafts, soft delete otherwise."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("hp-delete-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "hp-delete-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("hp-delete-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Draft Deletion Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_note(
        self, *, author=None, is_draft=False, promoted_at=None, promoted_by=None
    ):
        author = author or self.doctor
        return HistoryAndPhysical.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content="Conteúdo suficiente para a anamnese e exame físico de teste.",
            is_draft=is_draft,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            created_by=author,
            # A student acting user would force draft state (design D1), so a
            # fixture that must stay definitive records the physician as the
            # acting user.
            updated_by=promoted_by or author,
        )

    def _delete(self, user, note):
        self.client.force_login(user)
        return self.client.post(
            reverse(
                "historyandphysicals:historyandphysical_delete",
                kwargs={"pk": note.pk},
            )
        )

    def test_student_hard_deletes_own_never_finalized_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        response = self._delete(self.student, draft)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(HistoryAndPhysical.all_objects.filter(pk=draft.pk).exists())

    def test_physician_clears_another_authors_stale_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        response = self._delete(self.doctor, draft)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(HistoryAndPhysical.all_objects.filter(pk=draft.pk).exists())

    def test_unrelated_student_cannot_delete_someone_elses_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        response = self._delete(self.other_student, draft)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(HistoryAndPhysical.all_objects.filter(pk=draft.pk).exists())

    def test_definitive_note_keeps_the_soft_delete_path(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._delete(self.doctor, note)

        self.assertEqual(response.status_code, 302)
        stored = HistoryAndPhysical.all_objects.get(pk=note.pk)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.deleted_at)

    def test_reverted_final_keeps_the_soft_delete_path(self):
        reverted = self._create_note(
            author=self.student,
            is_draft=True,
            promoted_at=timezone.now() - timedelta(days=1),
            promoted_by=self.doctor,
        )

        response = self._delete(self.student, reverted)

        self.assertEqual(response.status_code, 302)
        stored = HistoryAndPhysical.all_objects.get(pk=reverted.pk)
        self.assertTrue(stored.is_deleted)
