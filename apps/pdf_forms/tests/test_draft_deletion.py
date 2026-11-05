"""S6 R5: PDF submission draft deletion (design D7).

The delete view adopts the draft-inclusive lookup plus the generic deletion
helper: never-finalized drafts hard-delete the row, definitive submissions
keep the soft-delete path, bot drafts stay 404 and unrelated students cannot
delete.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import PDFFormSubmission
from .factories import PDFFormTemplateFactory

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PDFSubmissionDraftDeletionTests(TestCase):
    """R5: hard delete for never-finalized drafts, soft delete for finals."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("pdf-delete-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "pdf-delete-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("pdf-delete-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="PDF Delete Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = PDFFormTemplateFactory(
            name="Formulário de Exclusão",
            created_by=cls.doctor,
            form_fields={},
        )

    def setUp(self):
        cache.clear()

    def _create_submission(
        self, *, author=None, is_draft=False, draft_created_by_bot="", promoted_by=None
    ):
        author = author or self.doctor
        return PDFFormSubmission.objects.create(
            form_template=self.template,
            patient=self.patient,
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Formulário PDF de teste",
            form_data={"notes": "Nota"},
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            draft_promoted_by=promoted_by,
        )

    def _delete_url(self, submission):
        return reverse("pdf_forms:submission_delete", kwargs={"pk": submission.pk})

    def test_student_author_hard_deletes_own_draft(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        submission_pk = draft.pk
        self.client.force_login(self.student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            PDFFormSubmission.all_objects.filter(pk=submission_pk).exists()
        )

    def test_physician_clears_a_student_draft(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        submission_pk = draft.pk
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            PDFFormSubmission.all_objects.filter(pk=submission_pk).exists()
        )

    def test_bot_draft_delete_lookup_stays_404(self):
        bot_draft = self._create_submission(
            author=self.doctor, is_draft=True, draft_created_by_bot="bot-client-1"
        )
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(bot_draft))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            PDFFormSubmission.all_objects.filter(pk=bot_draft.pk).exists()
        )

    def test_unrelated_student_cannot_delete_and_the_row_survives(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.other_student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(PDFFormSubmission.all_objects.filter(pk=draft.pk).exists())

    def test_definitive_submission_keeps_the_soft_delete_path(self):
        final = self._create_submission(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(final))

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertTrue(final.is_deleted)
        self.assertEqual(final.deleted_by, self.doctor)
