"""Draft-aware generic event predicates (S1 R1/R2).

``can_edit_event``/``can_delete_event`` gain two branches: a human draft
(``draft_created_by_bot == ""``) follows the collaborative draft rule
(creator, or any doctor/resident with patient access, no time limit) and a
definitive event follows the D6 owner/anchor table (owner = finalizer when
recorded, else creator; anchor = finalization timestamp when recorded, else
``created_at``; owner-only inside the 24h window). Bot drafts keep the
pre-existing creator-only 24h rule so nothing widens for the bot flow.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.permissions.utils import can_delete_event, can_edit_event
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()


class EventPredicateTestBase(TestCase):
    """Shared users/patient plus event builders for the predicate matrices."""

    def setUp(self):
        self.student = self._create_user("predicatestudent", User.STUDENT)
        self.other_student = self._create_user("predicateotherstudent", User.STUDENT)
        self.doctor = self._create_user("predicatedoctor", User.MEDICAL_DOCTOR)
        self.other_doctor = self._create_user("predicateotherdoctor", User.MEDICAL_DOCTOR)
        self.resident = self._create_user("predicateresident", User.RESIDENT)
        self.nurse = self._create_user("predicatenurse", User.NURSE)
        self.superuser = User.objects.create_superuser(
            username="predicatesuperuser",
            email="predicatesuperuser@example.com",
            password="testpass123",
        )
        self.patient = Patient.objects.create(
            name="Predicate Patient",
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

    def _create_event(
        self,
        *,
        created_by=None,
        updated_by=None,
        is_draft=False,
        bot_client_id="",
        age_hours=0,
        event_type=Event.DAILY_NOTE_EVENT,
        **extra,
    ):
        author = created_by or self.doctor
        event = Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Predicate event",
            event_type=event_type,
            created_by=author,
            updated_by=updated_by or author,
            is_draft=is_draft,
            draft_created_by_bot=bot_client_id,
            **extra,
        )
        if age_hours:
            Event.all_objects.filter(pk=event.pk).update(
                created_at=timezone.now() - timedelta(hours=age_hours)
            )
            event.refresh_from_db()
        return event


class HumanDraftEditDeleteTests(EventPredicateTestBase):
    """R1: collaborative draft rule with no time limit, no superuser bypass."""

    def test_creator_edits_and_deletes_own_old_draft(self):
        draft = self._create_event(created_by=self.student, is_draft=True, age_hours=24 * 30)

        self.assertTrue(can_edit_event(self.student, draft))
        self.assertTrue(can_delete_event(self.student, draft))

    def test_doctor_with_patient_access_edits_and_deletes_other_author_draft(self):
        draft = self._create_event(created_by=self.student, is_draft=True, age_hours=24 * 30)

        self.assertTrue(can_edit_event(self.doctor, draft))
        self.assertTrue(can_delete_event(self.doctor, draft))

    def test_resident_with_patient_access_edits_other_author_draft(self):
        draft = self._create_event(created_by=self.student, is_draft=True)

        self.assertTrue(can_edit_event(self.resident, draft))
        self.assertTrue(can_delete_event(self.resident, draft))

    def test_unrelated_student_is_denied_on_draft(self):
        draft = self._create_event(created_by=self.student, is_draft=True)

        self.assertFalse(can_edit_event(self.other_student, draft))
        self.assertFalse(can_delete_event(self.other_student, draft))

    def test_nurse_non_creator_is_denied_on_draft(self):
        draft = self._create_event(created_by=self.student, is_draft=True)

        self.assertFalse(can_edit_event(self.nurse, draft))
        self.assertFalse(can_delete_event(self.nurse, draft))

    def test_superuser_gets_no_draft_override(self):
        draft = self._create_event(created_by=self.student, is_draft=True)

        self.assertFalse(can_edit_event(self.superuser, draft))
        self.assertFalse(can_delete_event(self.superuser, draft))

    def test_tag_audit_event_stays_immutable_for_creator_and_doctor(self):
        audit_event = self._create_event(
            created_by=self.student,
            is_draft=True,
            event_type=Event.TAG_ADDED_EVENT,
        )

        for user in (self.student, self.doctor):
            with self.subTest(user=user.username):
                self.assertFalse(can_edit_event(user, audit_event))
                self.assertFalse(can_delete_event(user, audit_event))

    def test_bot_draft_keeps_creator_only_rule(self):
        """The human draft branch must not widen bot drafts."""
        bot_draft = self._create_event(
            created_by=self.doctor,
            is_draft=True,
            bot_client_id="bot-client-id",
            age_hours=1,
        )
        old_bot_draft = self._create_event(
            created_by=self.doctor,
            is_draft=True,
            bot_client_id="bot-client-id",
            age_hours=25,
        )

        self.assertTrue(can_edit_event(self.doctor, bot_draft))
        self.assertFalse(can_edit_event(self.doctor, old_bot_draft))
        self.assertFalse(can_edit_event(self.other_doctor, bot_draft))


class DefinitiveOwnerWindowTests(EventPredicateTestBase):
    """R2: the D6 four-case owner/anchor table for definitive events."""

    def _finalize_case(self, *, age_hours, promoted_by=None, promoted=True):
        """Definitive event created ``age_hours`` ago with optional promotion."""
        extra = {}
        if promoted:
            extra["draft_promoted_at"] = timezone.now()
        if promoted_by is not None:
            extra["draft_promoted_by"] = promoted_by
        return self._create_event(
            created_by=self.doctor,
            age_hours=age_hours,
            **extra,
        )

    def test_finalizer_and_timestamp_give_finalizer_the_window(self):
        event = self._finalize_case(age_hours=24 * 30, promoted_by=self.resident)

        self.assertTrue(can_edit_event(self.resident, event))
        self.assertTrue(can_delete_event(self.resident, event))
        self.assertFalse(can_edit_event(self.doctor, event))
        self.assertFalse(can_delete_event(self.doctor, event))
        self.assertFalse(can_edit_event(self.other_doctor, event))

    def test_finalizer_without_timestamp_anchors_at_creation(self):
        fresh = self._finalize_case(age_hours=1, promoted_by=self.resident, promoted=False)
        old = self._finalize_case(age_hours=25, promoted_by=self.resident, promoted=False)

        self.assertTrue(can_edit_event(self.resident, fresh))
        self.assertTrue(can_delete_event(self.resident, fresh))
        self.assertFalse(can_edit_event(self.doctor, fresh))
        self.assertFalse(can_edit_event(self.resident, old))
        self.assertFalse(can_delete_event(self.resident, old))

    def test_timestamp_without_finalizer_keeps_creator_ownership(self):
        event = self._finalize_case(age_hours=24 * 30, promoted_by=None)

        self.assertTrue(can_edit_event(self.doctor, event))
        self.assertTrue(can_delete_event(self.doctor, event))
        self.assertFalse(can_edit_event(self.resident, event))
        self.assertFalse(can_delete_event(self.resident, event))

    def test_creator_without_metadata_keeps_creation_window(self):
        fresh = self._finalize_case(age_hours=1, promoted=False)
        old = self._finalize_case(age_hours=25, promoted=False)

        self.assertTrue(can_edit_event(self.doctor, fresh))
        self.assertTrue(can_delete_event(self.doctor, fresh))
        self.assertFalse(can_edit_event(self.doctor, old))
        self.assertFalse(can_delete_event(self.doctor, old))
        self.assertFalse(can_edit_event(self.resident, fresh))

    def test_expired_anchor_locks_the_event(self):
        extra = {
            "draft_promoted_at": timezone.now() - timedelta(hours=25),
            "draft_promoted_by": self.resident,
        }
        event = self._create_event(
            created_by=self.doctor,
            age_hours=24 * 30,
            **extra,
        )

        self.assertFalse(can_edit_event(self.resident, event))
        self.assertFalse(can_delete_event(self.resident, event))

    def test_superuser_gets_no_definitive_override(self):
        event = self._finalize_case(age_hours=1, promoted=False)

        self.assertFalse(can_edit_event(self.superuser, event))
        self.assertFalse(can_delete_event(self.superuser, event))
