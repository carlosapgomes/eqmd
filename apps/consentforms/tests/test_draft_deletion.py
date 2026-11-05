"""S6 R3: consent draft deletion follows state and history (design D7).

Never-finalized drafts hard-delete the row; definitive consent forms keep the
soft-delete path; unrelated students cannot delete and the row survives.
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.patients.models import Patient

from ..models import ConsentForm, ConsentTemplate

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class ConsentFormDraftDeletionTests(TestCase):
    """R3: hard delete for never-finalized drafts, soft delete for finals."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("cf-delete-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "cf-delete-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("cf-delete-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Consent Delete Patient",
            birthday="1990-01-01",
            current_record_number="RN654",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template de Exclusão",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} "
                "{{ document_date }} {{ procedure_description }}"
            ),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_consent(self, *, author=None, is_draft=False, promoted_by=None):
        author = author or self.doctor
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 2),
            procedure_description="Procedimento de teste",
            rendered_markdown="Conteúdo do termo.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Termo de Consentimento - Template de Exclusão",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            draft_promoted_by=promoted_by,
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
        )

    def _delete_url(self, consent):
        return reverse("consentforms:consentform_delete", kwargs={"pk": consent.pk})

    def test_student_author_hard_deletes_own_draft(self):
        draft = self._create_consent(author=self.student, is_draft=True)
        consent_pk = draft.pk
        self.client.force_login(self.student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConsentForm.all_objects.filter(pk=consent_pk).exists())

    def test_physician_clears_a_student_draft(self):
        draft = self._create_consent(author=self.student, is_draft=True)
        consent_pk = draft.pk
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConsentForm.all_objects.filter(pk=consent_pk).exists())

    def test_unrelated_student_cannot_delete_and_the_row_survives(self):
        draft = self._create_consent(author=self.student, is_draft=True)
        self.client.force_login(self.other_student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ConsentForm.all_objects.filter(pk=draft.pk).exists())

    def test_definitive_consent_keeps_the_soft_delete_path(self):
        final = self._create_consent(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(final))

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertTrue(final.is_deleted)
        self.assertEqual(final.deleted_by, self.doctor)
