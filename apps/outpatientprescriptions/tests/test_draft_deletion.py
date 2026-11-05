"""S6 R1: prescription draft deletion follows state and history (design D7).

Never-finalized drafts hard-delete the row; definitive prescriptions keep the
soft-delete path; unrelated students cannot delete and the row survives.
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

from ..models import OutpatientPrescription, PrescriptionItem

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PrescriptionDraftDeletionTests(TestCase):
    """R1: hard delete for never-finalized drafts, soft delete for finals."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("rx-delete-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "rx-delete-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("rx-delete-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Prescription Delete Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_prescription(
        self, *, author=None, is_draft=False, promoted_at=None, promoted_by=None
    ):
        author = author or self.doctor
        prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            prescription_date=timezone.localdate(),
            instructions="Uso oral.",
            status="draft",
            is_draft=is_draft,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            description="Receita",
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
        )
        PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name="Paracetamol",
            presentation="500mg comprimidos",
            usage_instructions="Tomar 1 comprimido de 8 em 8 horas.",
            quantity="21 comprimidos",
            order=1,
        )
        return prescription

    def _delete_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_delete",
            kwargs={"pk": prescription.pk},
        )

    def test_student_author_hard_deletes_own_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)
        prescription_pk = draft.pk
        self.client.force_login(self.student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            OutpatientPrescription.all_objects.filter(pk=prescription_pk).exists()
        )

    def test_physician_clears_a_student_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)
        prescription_pk = draft.pk
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            OutpatientPrescription.all_objects.filter(pk=prescription_pk).exists()
        )

    def test_unrelated_student_cannot_delete_and_the_row_survives(self):
        draft = self._create_prescription(author=self.student, is_draft=True)
        self.client.force_login(self.other_student)

        response = self.client.post(self._delete_url(draft))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            OutpatientPrescription.all_objects.filter(pk=draft.pk).exists()
        )

    def test_definitive_prescription_keeps_the_soft_delete_path(self):
        final = self._create_prescription(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(self._delete_url(final))

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertTrue(final.is_deleted)
        self.assertEqual(final.deleted_by, self.doctor)
