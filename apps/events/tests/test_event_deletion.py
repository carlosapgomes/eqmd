"""S3 R6: the generic event deletion helper (design D7).

Deletion rights follow current state and are enforced by the callers'
predicates; the helper only picks the method the record's history requires:
never-finalized drafts lose the row, anything ever finalized keeps the
soft-delete path. The helper stays event-type agnostic (no media handling
here; media cleanup lands with the media slice).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

from ..models import Event
from ..services.event_deletion import delete_event_record

User = get_user_model()


class EventDeletionHelperTests(TestCase):
    """The hard/soft decision is driven by state plus finalization history."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="deletion-doctor",
            email="deletion-doctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.student = User.objects.create_user(
            username="deletion-student",
            email="deletion-student@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.STUDENT,
        )
        cls.patient = Patient.objects.create(
            name="Deletion Helper Patient",
            birthday=date(1990, 1, 1),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_event(
        self,
        *,
        author=None,
        event_type=Event.DAILY_NOTE_EVENT,
        is_draft=False,
        promoted_at=None,
        promoted_by=None,
    ):
        author = author or self.doctor
        return Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Evento de teste da exclusão",
            event_type=event_type,
            is_draft=is_draft,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            created_by=author,
            updated_by=author,
        )

    def test_never_finalized_draft_is_hard_deleted(self):
        draft = self._create_event(is_draft=True)

        hard_deleted = delete_event_record(draft, deleted_by=self.student)

        self.assertTrue(hard_deleted)
        self.assertFalse(Event.all_objects.filter(pk=draft.pk).exists())

    def test_definitive_event_is_soft_deleted(self):
        event = self._create_event()

        hard_deleted = delete_event_record(event, deleted_by=self.doctor)

        self.assertFalse(hard_deleted)
        stored = Event.all_objects.get(pk=event.pk)
        self.assertTrue(stored.is_deleted)
        self.assertEqual(stored.deleted_by, self.doctor)

    def test_reverted_final_is_soft_deleted(self):
        reverted = self._create_event(
            is_draft=True,
            promoted_at=timezone.now() - timedelta(days=1),
            promoted_by=self.doctor,
        )

        hard_deleted = delete_event_record(reverted, deleted_by=self.doctor)

        self.assertFalse(hard_deleted)
        self.assertTrue(Event.all_objects.get(pk=reverted.pk).is_deleted)

    def test_finalizer_without_timestamp_counts_as_ever_finalized(self):
        reverted = self._create_event(is_draft=True, promoted_by=self.doctor)

        hard_deleted = delete_event_record(reverted, deleted_by=self.doctor)

        self.assertFalse(hard_deleted)
        self.assertTrue(Event.all_objects.get(pk=reverted.pk).is_deleted)

    def test_helper_works_for_child_models(self):
        draft = SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content="Conteúdo suficiente para a nota de teste.",
            is_draft=True,
            created_by=self.student,
            updated_by=self.student,
        )

        hard_deleted = delete_event_record(draft, deleted_by=self.doctor)

        self.assertTrue(hard_deleted)
        self.assertFalse(SimpleNote.all_objects.filter(pk=draft.pk).exists())
