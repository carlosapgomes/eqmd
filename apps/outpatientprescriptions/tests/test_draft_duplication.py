"""S6 R10: prescription duplication sources stay definitive-only (design D14).

Drafts 404 as sources through the draft-excluding manager, and a
student-authored duplicate result persists as a draft through the model
backstop.
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


class PrescriptionDraftDuplicationTests(TestCase):
    """R10: draft sources 404, duplicate results follow the author's rules."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("rx-dup-student", User.STUDENT)
        cls.doctor = create_profession_user("rx-dup-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Prescription Duplicate Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_prescription(self, *, author=None, is_draft=False):
        author = author or self.doctor
        prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            prescription_date=timezone.localdate(),
            instructions="Uso oral.",
            status="draft",
            is_draft=is_draft,
            description="Receita",
            created_by=author,
            updated_by=author,
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

    def _duplicate_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_duplicate",
            kwargs={"pk": prescription.pk},
        )

    def test_draft_source_is_a_404_for_the_author_and_physicians(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            response = self.client.post(self._duplicate_url(draft))
            self.assertEqual(response.status_code, 404)

    def test_student_duplicate_result_persists_as_draft(self):
        source = self._create_prescription(author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(self._duplicate_url(source))

        self.assertEqual(response.status_code, 302)
        copy = OutpatientPrescription.all_objects.get(
            created_by=self.student, is_draft=True
        )
        self.assertNotEqual(copy.pk, source.pk)
        self.assertEqual(copy.items.count(), 1)

    def test_physician_duplicate_result_stays_definitive(self):
        source = self._create_prescription(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(self._duplicate_url(source))

        self.assertEqual(response.status_code, 302)
        copy = (
            OutpatientPrescription.all_objects.filter(created_by=self.doctor)
            .exclude(pk=source.pk)
            .get()
        )
        self.assertFalse(copy.is_draft)
