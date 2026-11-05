"""S7 R1/R2/R3: discharge draft deletion, bot guard and revert retention.

Deletion rights follow the current state and the deletion method follows the
history (design D7): never-finalized drafts are hard-deleted by their creator
or by any doctor/resident with patient access (no time limit), while finals and
reverted (ever-finalized) drafts keep the soft path with the rights of their
current state (design D6). The four normal view querysets keep bot drafts
unreachable (design D3), and reverting a final retains ``finalized_at/by`` as
the last-finalization record (design D5).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.patients.models import Patient

from ..models import DischargeReport

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


def report_payload(patient, **overrides):
    """Valid discharge update/create payload for the given patient."""
    data = {
        "patient": patient.pk,
        "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        "description": "Relatório de alta",
        "admission_date": "2024-01-01",
        "discharge_date": "2024-01-05",
        "medical_specialty": "Cardiologia",
        "admission_history": "história",
        "problems_and_diagnosis": "diagnóstico",
        "exams_list": "exames",
        "procedures_list": "procedimentos",
        "inpatient_medical_history": "internação",
        "discharge_status": "estável",
        "discharge_recommendations": "retorno ambulatorial",
    }
    data.update(overrides)
    return data


class DischargeDraftFixtures(TestCase):
    """Shared users, patient, report builder and URL helpers."""

    @classmethod
    def setUpTestData(cls):
        cls.student = create_profession_user("s7-student", User.STUDENT)
        cls.other_student = create_profession_user("s7-other-student", User.STUDENT)
        cls.doctor = create_profession_user("s7-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Discharge Deletion Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_report(
        self,
        *,
        author=None,
        is_draft=True,
        finalized_at=None,
        finalized_by=None,
        draft_created_by_bot="",
        created_at=None,
    ):
        author = author or self.doctor
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Relatório base",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Cardiologia",
            admission_history="história",
            problems_and_diagnosis="diagnóstico",
            exams_list="exames",
            procedures_list="procedimentos",
            inpatient_medical_history="internação",
            discharge_status="estável",
            discharge_recommendations="retorno ambulatorial",
            is_draft=is_draft,
            finalized_at=finalized_at,
            finalized_by=finalized_by,
            draft_created_by_bot=draft_created_by_bot,
            created_by=author,
            # A student acting user would force draft state (design D1), so the
            # acting user of a definitive fixture is the finalizing physician.
            updated_by=finalized_by or author,
        )
        if created_at is not None:
            DischargeReport.all_objects.filter(pk=report.pk).update(
                created_at=created_at
            )
            report.refresh_from_db()
        return report

    def _url(self, name, report):
        return reverse(f"apps.dischargereports:{name}", kwargs={"pk": report.pk})

    def _delete(self, user, report):
        self.client.force_login(user)
        return self.client.post(self._url("dischargereport_delete", report))

    def _stored(self, report):
        return DischargeReport.all_objects.get(pk=report.pk)


class DischargeReportDraftDeletionTests(DischargeDraftFixtures):
    """R1: hard delete for never-finalized drafts, soft delete otherwise."""

    def test_student_hard_deletes_own_never_finalized_draft(self):
        draft = self._create_report(author=self.student)

        response = self._delete(self.student, draft)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DischargeReport.all_objects.filter(pk=draft.pk).exists())
        # The multi-table parent row goes too, so no orphan timeline entry stays.
        self.assertFalse(Event.all_objects.filter(pk=draft.pk).exists())

    def test_physician_clears_another_authors_never_finalized_draft(self):
        draft = self._create_report(author=self.student)

        response = self._delete(self.doctor, draft)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DischargeReport.all_objects.filter(pk=draft.pk).exists())

    def test_unrelated_student_cannot_delete_someone_elses_draft(self):
        draft = self._create_report(author=self.student)

        response = self._delete(self.other_student, draft)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(DischargeReport.all_objects.filter(pk=draft.pk).exists())

    def test_final_keeps_the_soft_delete_path(self):
        final = self._create_report(
            author=self.student,
            is_draft=False,
            finalized_at=timezone.now() - timedelta(hours=1),
            finalized_by=self.doctor,
        )

        response = self._delete(self.doctor, final)

        self.assertEqual(response.status_code, 302)
        stored = self._stored(final)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.deleted_at)
        self.assertEqual(stored.deleted_by, self.doctor)

    def test_reverted_final_keeps_the_soft_delete_path(self):
        reverted = self._create_report(
            author=self.student,
            is_draft=True,
            finalized_at=timezone.now() - timedelta(days=1),
            finalized_by=self.doctor,
        )

        response = self._delete(self.student, reverted)

        self.assertEqual(response.status_code, 302)
        stored = self._stored(reverted)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.finalized_at)
        self.assertEqual(stored.finalized_by, self.doctor)


class DischargeReportRevertRetentionTests(DischargeDraftFixtures):
    """R3: revert retains the finalization pair and delete stays record-safe."""

    def test_revert_retains_finalization_metadata(self):
        draft = self._create_report(author=self.student)
        self.client.force_login(self.doctor)

        self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_final="x"),
        )
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        finalized_at = draft.finalized_at
        self.assertIsNotNone(finalized_at)
        self.assertEqual(draft.finalized_by, self.doctor)

        response = self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_draft="x"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertEqual(draft.finalized_at, finalized_at)
        self.assertEqual(draft.finalized_by, self.doctor)
        self.assertTrue(draft.was_ever_finalized())

    def test_reverted_report_stays_editable_as_a_draft(self):
        draft = self._create_report(author=self.student)
        self.client.force_login(self.doctor)
        self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_final="x"),
        )
        self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_draft="x"),
        )

        # The creator regains draft-state edit rights after the revert.
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(self._url("dischargereport_update", draft)).status_code,
            200,
        )
        response = self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_draft="x"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNotNone(draft.finalized_at)

    def test_finalize_revert_delete_soft_deletes_with_history_retained(self):
        draft = self._create_report(author=self.student)
        self.client.force_login(self.doctor)
        self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_final="x"),
        )
        self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_draft="x"),
        )

        response = self._delete(self.student, draft)

        self.assertEqual(response.status_code, 302)
        stored = self._stored(draft)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.deleted_at)
        self.assertEqual(stored.deleted_by, self.student)
        self.assertTrue(stored.was_ever_finalized())

    def test_refinalize_after_revert_reanchors_the_window(self):
        first_anchor = timezone.now() - timedelta(days=2)
        draft = self._create_report(
            author=self.student,
            finalized_at=first_anchor,
            finalized_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._url("dischargereport_update", draft),
            report_payload(self.patient, save_final="x"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertGreater(draft.finalized_at, first_anchor)
        self.assertEqual(draft.finalized_by, self.doctor)


class DischargeReportBotDraftGuardTests(DischargeDraftFixtures):
    """R2: bot drafts stay unreachable through all four discharge views."""

    def test_bot_drafts_stay_unreachable_through_the_four_views(self):
        bot_draft = self._create_report(
            author=self.doctor,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )

        self.client.force_login(self.doctor)

        for name in (
            "dischargereport_detail",
            "dischargereport_update",
            "dischargereport_delete",
            "dischargereport_duplicate",
        ):
            with self.subTest(view=name):
                response = self.client.get(self._url(name, bot_draft))
                self.assertEqual(response.status_code, 404)

    def test_bot_draft_survives_a_crafted_delete(self):
        bot_draft = self._create_report(
            author=self.doctor,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )

        response = self._delete(self.doctor, bot_draft)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(DischargeReport.all_objects.filter(pk=bot_draft.pk).exists())
