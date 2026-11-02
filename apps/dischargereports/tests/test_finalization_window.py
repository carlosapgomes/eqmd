"""Finalization window anchoring for discharge reports (S3 R1/R4/R5/R7).

Finalizing a draft opens a 24h correction window anchored at ``finalized_at``
for the report's creator and finalizer (design D6). Legacy finals without an
anchor fall back to ``created_at`` so their verdicts stay identical to the
creation-anchored rule.
"""

import importlib
from datetime import date, timedelta

from django.apps import apps as django_apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from apps.dischargereports.admin import DischargeReportAdmin
from apps.dischargereports.models import DischargeReport
from apps.patients.models import Patient

User = get_user_model()

MIGRATION_MODULE = (
    "apps.dischargereports.migrations.0003_dischargereport_finalization_anchor"
)


def load_finalization_migration():
    """Import the slice's data migration to exercise its backfill step."""
    return importlib.import_module(MIGRATION_MODULE)


def run_migration_step(step):
    """Run a migration data step against the live schema."""
    with connection.schema_editor() as schema_editor:
        step(django_apps, schema_editor)


class FinalizationAnchorMigrationTests(TestCase):
    """R1: legacy finals get the creation anchor; drafts stay null."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="anchorcreator",
            email="anchorcreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.patient = Patient.objects.create(
            name="Anchor Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _create_report(self, *, is_draft, created_at=None):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Draft" if is_draft else "Final",
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
            is_draft=is_draft,
            created_by=self.creator,
            updated_by=self.creator,
        )
        if created_at is not None:
            DischargeReport.all_objects.filter(pk=report.pk).update(
                created_at=created_at
            )
            report.refresh_from_db()
        return report

    def test_backfill_anchors_legacy_finals_at_creation(self):
        """R1: finals get finalized_at=created_at and finalized_by=created_by."""
        now = timezone.now()
        old_final = self._create_report(
            is_draft=False, created_at=now - timedelta(days=30)
        )
        fresh_final = self._create_report(is_draft=False)
        draft = self._create_report(is_draft=True, created_at=now - timedelta(days=30))
        self.assertIsNone(old_final.finalized_at)

        run_migration_step(load_finalization_migration().backfill_finalization_anchor)

        for report in (old_final, fresh_final):
            report.refresh_from_db()
            self.assertEqual(report.finalized_at, report.created_at)
            self.assertEqual(report.finalized_by_id, report.created_by_id)
        draft.refresh_from_db()
        self.assertIsNone(draft.finalized_at)
        self.assertIsNone(draft.finalized_by_id)

    def test_reverse_step_clears_the_backfilled_anchor(self):
        """R1: the data step is reversible (fields hold derived data)."""
        now = timezone.now()
        old_final = self._create_report(
            is_draft=False, created_at=now - timedelta(days=30)
        )
        migration = load_finalization_migration()

        run_migration_step(migration.backfill_finalization_anchor)
        run_migration_step(migration.clear_finalization_anchor)

        old_final.refresh_from_db()
        self.assertIsNone(old_final.finalized_at)
        self.assertIsNone(old_final.finalized_by_id)


class FinalizationWindowModelTests(TestCase):
    """R4/R5: the final branch is anchored at finalization with a fallback."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="windowcreator",
            email="windowcreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.finalizer = User.objects.create_user(
            username="windowfinalizer",
            email="windowfinalizer@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.other_doctor = User.objects.create_user(
            username="windowotherdoctor",
            email="windowotherdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.patient = Patient.objects.create(
            name="Window Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _create_final(self, *, created_at=None, finalized_at=None):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Final",
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
            is_draft=False,
            created_by=self.creator,
            updated_by=self.creator,
            finalized_at=finalized_at,
            finalized_by=self.finalizer if finalized_at else None,
        )
        if created_at is not None:
            DischargeReport.all_objects.filter(pk=report.pk).update(
                created_at=created_at
            )
            report.refresh_from_db()
        return report

    def test_anchor_inside_window_allows_creator_and_finalizer_only(self):
        """R2: the union opens for creator OR finalizer, not every doctor."""
        now = timezone.now()
        report = self._create_final(
            created_at=now - timedelta(days=30), finalized_at=now
        )

        self.assertTrue(report.can_be_edited_by_user(self.creator))
        self.assertTrue(report.can_be_edited_by_user(self.finalizer))
        self.assertFalse(report.can_be_edited_by_user(self.other_doctor))

    def test_anchor_past_the_window_denies_creator_and_finalizer(self):
        """R4: more than 24h after finalized_at nobody is allowed."""
        now = timezone.now()
        report = self._create_final(
            created_at=now - timedelta(days=30),
            finalized_at=now - timedelta(hours=25),
        )

        self.assertFalse(report.can_be_edited_by_user(self.creator))
        self.assertFalse(report.can_be_edited_by_user(self.finalizer))

    def test_change_event_holder_is_window_bound(self):
        """R4: events.change_event does not escape the finalization window."""
        holder = User.objects.create_user(
            username="windowchanger",
            email="windowchanger@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        holder.user_permissions.add(Permission.objects.get(codename="change_event"))
        now = timezone.now()
        fresh = self._create_final(
            created_at=now - timedelta(days=30), finalized_at=now
        )
        expired = self._create_final(
            created_at=now - timedelta(days=30),
            finalized_at=now - timedelta(hours=25),
        )

        self.assertTrue(fresh.can_be_edited_by_user(holder))
        self.assertFalse(expired.can_be_edited_by_user(holder))

    def test_null_anchor_falls_back_to_created_at(self):
        """R5: a final without finalized_at keeps the creation-anchored rule."""
        now = timezone.now()
        fresh_legacy = self._create_final(created_at=now - timedelta(hours=23))
        old_legacy = self._create_final(created_at=now - timedelta(hours=25))

        self.assertIsNone(fresh_legacy.finalized_at)
        self.assertTrue(fresh_legacy.can_be_edited_by_user(self.creator))
        self.assertFalse(fresh_legacy.can_be_edited_by_user(self.finalizer))
        self.assertFalse(old_legacy.can_be_edited_by_user(self.creator))


class FinalizationAdminDisplayTests(TestCase):
    """R7: admin exposes the finalization fields read-only."""

    def test_finalization_fields_are_read_only(self):
        admin = DischargeReportAdmin(DischargeReport, AdminSite())

        self.assertIn("finalized_at", admin.readonly_fields)
        self.assertIn("finalized_by", admin.readonly_fields)

    def test_finalization_fields_are_in_the_metadata_fieldset(self):
        admin = DischargeReportAdmin(DischargeReport, AdminSite())
        metadata = dict(admin.fieldsets)["Metadados"]["fields"]

        self.assertIn("finalized_at", metadata)
        self.assertIn("finalized_by", metadata)
