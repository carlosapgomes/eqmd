"""Duplication POST regression tests for daily notes.

Covers the POST half of ``DailyNoteDuplicateView`` (change
``extend-document-duplication``): a valid submission creates an
independent copy for the same patient while leaving the source evolution
untouched, and users without ``events.add_event`` are refused.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.patients.models import Patient

from ..models import DailyNote

User = get_user_model()


def grant_event_permissions(user, *codenames):
    """Grant the given events app permissions to a user.

    The test database does not seed the profession groups' permissions, so
    view tests must grant the exact Django permissions enforced by
    PermissionRequiredMixin on the duplicate view.
    """
    perms = Permission.objects.filter(
        content_type__app_label="events", codename__in=codenames
    )
    user.user_permissions.add(*perms)


class DailyNoteDuplicationPostTests(TestCase):
    """POST behaviour of the daily note duplication view."""

    def setUp(self):
        self.author = User.objects.create_user(
            username="dailynote-duplicate-author",
            email="dailynote-author@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.duplicator = User.objects.create_user(
            username="dailynote-duplicate-copier",
            email="dailynote-copier@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.user_without_add_event = User.objects.create_user(
            username="dailynote-duplicate-no-add",
            email="dailynote-no-add@example.com",
            password="testpass123",
            profession_type=User.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )
        grant_event_permissions(
            self.author, "view_event", "add_event", "change_event", "delete_event"
        )
        grant_event_permissions(
            self.duplicator, "view_event", "add_event", "change_event", "delete_event"
        )
        grant_event_permissions(
            self.user_without_add_event,
            "view_event",
            "change_event",
            "delete_event",
        )

        self.patient = Patient.objects.create(
            name="Duplication Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            created_by=self.author,
            updated_by=self.author,
        )
        self.source = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=3),
            description=Event.EVENT_TYPE_CHOICES[Event.DAILY_NOTE_EVENT][1],
            content="Evolução de origem usada como base da duplicação.",
            created_by=self.author,
            updated_by=self.author,
        )
        self.url = reverse(
            "dailynotes:dailynote_duplicate", kwargs={"pk": self.source.pk}
        )

    def _payload(self, content, event_datetime):
        """Build a valid duplicate-form POST payload."""
        return {
            "event_datetime": timezone.localtime(event_datetime).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "content": content,
        }

    def _source_snapshot(self):
        """Capture the source document fields that duplication must not alter."""
        return {
            "content": self.source.content,
            "description": self.source.description,
            "event_type": self.source.event_type,
            "event_datetime": self.source.event_datetime,
            "created_by_id": self.source.created_by_id,
            "updated_by_id": self.source.updated_by_id,
        }

    def test_post_creates_independent_copy_for_same_patient(self):
        """Valid POST creates a new evolution for the patient, authored by the poster."""
        self.client.force_login(self.duplicator)
        submitted_event_datetime = timezone.now() - timedelta(minutes=5)
        submitted_content = "Evolução duplicada a partir da origem."

        response = self.client.post(
            self.url, data=self._payload(submitted_content, submitted_event_datetime)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse(
                "patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            ),
        )

        duplicate = DailyNote.objects.filter(patient=self.patient).exclude(
            pk=self.source.pk
        )
        self.assertEqual(duplicate.count(), 1)
        copy = duplicate.get()
        self.assertEqual(copy.content, submitted_content)
        self.assertEqual(copy.event_type, Event.DAILY_NOTE_EVENT)
        self.assertEqual(copy.created_by, self.duplicator)
        self.assertEqual(copy.updated_by, self.duplicator)
        self.assertNotEqual(copy.event_datetime, self.source.event_datetime)
        self.assertAlmostEqual(
            copy.event_datetime.timestamp(),
            submitted_event_datetime.timestamp(),
            delta=120,
        )

    def test_post_leaves_source_document_unchanged(self):
        """Duplicating a daily note does not modify the source evolution."""
        self.client.force_login(self.duplicator)
        before = self._source_snapshot()

        response = self.client.post(
            self.url,
            data=self._payload(
                "Evolução duplicada sem tocar no documento de origem.",
                timezone.now() - timedelta(minutes=5),
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        self.assertEqual(self.source.content, before["content"])
        self.assertEqual(self.source.description, before["description"])
        self.assertEqual(self.source.event_type, before["event_type"])
        self.assertEqual(self.source.event_datetime, before["event_datetime"])
        self.assertEqual(self.source.created_by_id, before["created_by_id"])
        self.assertEqual(self.source.updated_by_id, before["updated_by_id"])

    def test_post_denied_without_add_event_permission(self):
        """Authenticated user without events.add_event cannot duplicate (403)."""
        self.client.force_login(self.user_without_add_event)
        self.assertFalse(self.user_without_add_event.has_perm("events.add_event"))

        response = self.client.post(
            self.url,
            data=self._payload(
                "Tentativa de duplicação sem permissão de criação.",
                timezone.now() - timedelta(minutes=5),
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(DailyNote.objects.filter(patient=self.patient).count(), 1)

    def test_post_denied_for_anonymous_user(self):
        """Anonymous POST is refused because dispatch checks patient access first."""
        response = self.client.post(
            self.url,
            data=self._payload(
                "Tentativa anônima de duplicação de evolução.",
                timezone.now() - timedelta(minutes=5),
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(DailyNote.objects.filter(patient=self.patient).count(), 1)
