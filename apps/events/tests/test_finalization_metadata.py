"""Finalizer/anchor helpers and the ever-finalized derivation (S1 R5).

``Event.finalizer()`` and ``Event.finalization_anchor()`` resolve both
finalization field pairs (``draft_promoted_*`` for supervised approvals,
``finalized_*`` for discharge reports) following design D6. ``was_ever_finalized()``
derives from the RETAINED metadata only, so a reverted final keeps the signal
without depending on history (design D5/D7).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()


class FinalizationMetadataTestBase(TestCase):
    def setUp(self):
        self.creator = self._create_user("metadatacreator", User.MEDICAL_DOCTOR)
        self.finalizer = self._create_user("metadatafinalizer", User.RESIDENT)
        self.patient = Patient.objects.create(
            name="Metadata Patient",
            birthday=date(1990, 1, 1),
            created_by=self.creator,
            updated_by=self.creator,
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

    def _create_event(self, *, is_draft=False, **extra):
        return Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Metadata event",
            event_type=Event.SIMPLE_NOTE_EVENT,
            created_by=self.creator,
            updated_by=self.creator,
            is_draft=is_draft,
            **extra,
        )

    def _create_report(self, *, is_draft=False, **extra):
        return DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Metadata report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Cardiologia",
            admission_history="history",
            problems_and_diagnosis="diagnosis",
            exams_list="exams",
            procedures_list="procedures",
            inpatient_medical_history="inpatient history",
            discharge_status="status",
            discharge_recommendations="recommendations",
            created_by=self.creator,
            updated_by=self.creator,
            is_draft=is_draft,
            **extra,
        )


class FinalizerResolutionTests(FinalizationMetadataTestBase):
    """R5: the helpers resolve both field pairs."""

    def test_never_finalized_draft_has_no_finalizer_or_anchor(self):
        draft = self._create_event(is_draft=True)

        self.assertIsNone(draft.finalizer())
        self.assertIsNone(draft.finalization_anchor())
        self.assertFalse(draft.was_ever_finalized())

    def test_promoted_pair_is_resolved(self):
        promoted_at = timezone.now() - timedelta(hours=2)
        event = self._create_event(
            draft_promoted_at=promoted_at,
            draft_promoted_by=self.finalizer,
        )

        self.assertEqual(event.finalizer(), self.finalizer)
        self.assertEqual(event.finalization_anchor(), promoted_at)
        self.assertTrue(event.was_ever_finalized())

    def test_discharge_finalized_pair_is_resolved(self):
        finalized_at = timezone.now() - timedelta(hours=2)
        report = self._create_report(
            finalized_at=finalized_at,
            finalized_by=self.finalizer,
        )

        self.assertEqual(report.finalizer(), self.finalizer)
        self.assertEqual(report.finalization_anchor(), finalized_at)
        self.assertTrue(report.was_ever_finalized())

    def test_timestamp_without_finalizer_still_sets_the_anchor(self):
        promoted_at = timezone.now() - timedelta(hours=2)
        event = self._create_event(draft_promoted_at=promoted_at)

        self.assertIsNone(event.finalizer())
        self.assertEqual(event.finalization_anchor(), promoted_at)
        self.assertTrue(event.was_ever_finalized())

    def test_finalizer_without_timestamp_leaves_the_anchor_empty(self):
        event = self._create_event(draft_promoted_by=self.finalizer)

        self.assertEqual(event.finalizer(), self.finalizer)
        self.assertIsNone(event.finalization_anchor())
        self.assertTrue(event.was_ever_finalized())

    def test_discharge_revert_keeps_the_ever_finalized_signal(self):
        """D5 retention: a reverted report still proves it was finalized."""
        report = self._create_report(
            is_draft=True,
            finalized_at=timezone.now() - timedelta(days=3),
            finalized_by=self.finalizer,
        )

        self.assertTrue(report.is_draft)
        self.assertTrue(report.was_ever_finalized())
        self.assertEqual(report.finalizer(), self.finalizer)

    def test_supervised_revert_keeps_the_ever_finalized_signal(self):
        event = self._create_event(
            is_draft=True,
            draft_promoted_at=timezone.now() - timedelta(days=3),
            draft_promoted_by=self.finalizer,
        )

        self.assertTrue(event.is_draft)
        self.assertTrue(event.was_ever_finalized())
