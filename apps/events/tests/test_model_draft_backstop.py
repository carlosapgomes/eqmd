"""Model backstop: student-authored events never persist as definitive (S1 R4).

``Event.save()`` forces ``is_draft=True`` when ``created_by`` is a student and
the acting user (``updated_by``) is a student, on create and on update,
including restricted ``update_fields`` saves where the force adds ``is_draft``
to the persisted field set. A doctor/resident acting on the same record (the
finalize path) is unaffected, and bot drafts keep their own lifecycle.
"""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.dailynotes.models import DailyNote
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()


def no_search_vector(*args, **kwargs):
    """Skip the postgreSQL search-vector update for the DailyNote subclass."""
    return


class StudentAuthorDraftBackstopTests(TestCase):
    """R4: the force covers create, update web saves and update_fields."""

    def setUp(self):
        self.student = self._create_user("backstopstudent", User.STUDENT)
        self.other_student = self._create_user("backstopotherstudent", User.STUDENT)
        self.doctor = self._create_user("backstopdoctor", User.MEDICAL_DOCTOR)
        self.patient = Patient.objects.create(
            name="Backstop Patient",
            birthday=date(1990, 1, 1),
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    def _create_user(self, username, profession_type):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=profession_type,
        )

    def _create_event(self, *, created_by, updated_by, is_draft, **extra):
        return Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Backstop event",
            event_type=Event.SIMPLE_NOTE_EVENT,
            created_by=created_by,
            updated_by=updated_by,
            is_draft=is_draft,
            **extra,
        )

    def _stored_event(self, event):
        return Event.all_objects.get(pk=event.pk)

    def test_student_creation_is_forced_to_draft(self):
        event = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=False,
        )

        self.assertTrue(event.is_draft)
        self.assertTrue(self._stored_event(event).is_draft)

    def test_student_cannot_flip_own_draft_on_full_save(self):
        draft = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=True,
        )
        draft.is_draft = False
        draft.description = "Student tries to finalize"

        draft.save()

        self.assertTrue(self._stored_event(draft).is_draft)

    def test_student_cannot_flip_own_draft_with_update_fields(self):
        draft = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=True,
        )
        draft.is_draft = False

        draft.save(update_fields=["is_draft"])

        self.assertTrue(self._stored_event(draft).is_draft)

    def test_restricted_save_without_is_draft_still_persists_the_force(self):
        draft = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=True,
        )
        draft.is_draft = False
        draft.description = "Restricted save must not bypass the force"

        draft.save(update_fields=["description"])

        stored = self._stored_event(draft)
        self.assertTrue(stored.is_draft)
        self.assertEqual(stored.description, draft.description)

    def test_subclass_save_keeps_the_force(self):
        with patch("apps.dailynotes.signals.update_search_vector", no_search_vector):
            note = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description="Student daily note",
                content="Student daily note content",
                created_by=self.student,
                updated_by=self.student,
                is_draft=False,
            )

            self.assertTrue(self._stored_event(note).is_draft)

    def test_subclass_restricted_save_still_persists_the_force(self):
        """MTI children accept the added field in ``update_fields``."""
        with patch("apps.dailynotes.signals.update_search_vector", no_search_vector):
            note = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description="Student daily note",
                content="Student daily note content",
                created_by=self.student,
                updated_by=self.student,
                is_draft=True,
            )
            note.is_draft = False
            note.content = "Edited by the student"

            note.save(update_fields=["content"])

        stored = DailyNote.all_objects.get(pk=note.pk)
        self.assertTrue(stored.is_draft)
        self.assertEqual(stored.content, "Edited by the student")

    def test_doctor_finalize_path_is_not_forced(self):
        """A doctor/resident acting on a student record may finalize it."""
        draft = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=True,
        )
        draft.updated_by = self.doctor
        draft.is_draft = False

        draft.save()

        self.assertFalse(self._stored_event(draft).is_draft)
        self.assertEqual(self._stored_event(draft).created_by, self.student)

    def test_student_update_of_doctor_authored_event_is_not_forced(self):
        """The force follows authorship, not the acting student."""
        event = self._create_event(
            created_by=self.doctor,
            updated_by=self.doctor,
            is_draft=False,
        )
        event.updated_by = self.student
        event.description = "Student edits a definitive record"

        event.save()

        self.assertFalse(self._stored_event(event).is_draft)

    def test_bot_draft_is_unaffected(self):
        with patch("apps.dailynotes.signals.update_search_vector", no_search_vector):
            bot_draft = DailyNote.objects.create(
                patient=self.patient,
                event_datetime=timezone.now(),
                description="Draft via bot",
                content="Draft via bot content",
                created_by=self.doctor,
                updated_by=self.doctor,
                is_draft=True,
                draft_created_by_bot="bot-client-id",
                draft_delegated_by=self.doctor,
            )

        self.assertTrue(self._stored_event(bot_draft).is_draft)

    def test_other_student_acting_user_still_forces(self):
        """The acting-user side of the conjunction is enough on updates."""
        draft = self._create_event(
            created_by=self.student,
            updated_by=self.student,
            is_draft=True,
        )
        draft.updated_by = self.other_student
        draft.is_draft = False

        draft.save()

        self.assertTrue(self._stored_event(draft).is_draft)
