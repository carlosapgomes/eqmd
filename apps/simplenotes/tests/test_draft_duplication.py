"""S3 R8: SimpleNote duplicate sources and student duplicate results.

Duplicate sources stay definitive-only (human drafts 404 as sources, design
D14) and a duplicate created by a student persists as a draft through the
model backstop.
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

from ..models import SimpleNote

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class SimpleNoteDraftDuplicationTests(TestCase):
    """R8: drafts cannot seed duplicates; student copies are drafts."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("dup-student", User.STUDENT)
        cls.doctor = create_profession_user("dup-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Draft Duplication Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_note(self, *, author=None, is_draft=False):
        author = author or self.doctor
        return SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=1),
            content="Conteúdo suficiente para a nota de origem.",
            is_draft=is_draft,
            created_by=author,
            updated_by=author,
        )

    def _payload(self):
        return {
            "event_datetime": timezone.localtime(
                timezone.now() - timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            "content": "Conteúdo suficiente para a nota duplicada.",
        }

    def test_human_draft_cannot_be_duplicated(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("simplenotes:simplenote_duplicate", kwargs={"pk": draft.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_student_duplicate_result_persists_as_draft(self):
        source = self._create_note(author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("simplenotes:simplenote_duplicate", kwargs={"pk": source.pk}),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        copy = SimpleNote.all_objects.get(
            content="Conteúdo suficiente para a nota duplicada."
        )
        self.assertTrue(copy.is_draft)
        self.assertEqual(copy.created_by, self.student)
        self.assertIsNone(copy.draft_promoted_at)

    def test_physician_duplicate_result_stays_definitive(self):
        source = self._create_note(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse("simplenotes:simplenote_duplicate", kwargs={"pk": source.pk}),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        copy = SimpleNote.objects.get(
            content="Conteúdo suficiente para a nota duplicada."
        )
        self.assertFalse(copy.is_draft)
