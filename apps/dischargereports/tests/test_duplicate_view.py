"""Tests for the discharge report duplicate flow.

Slice S1 of change ``duplicate-discharge-report``: a new draft report is
created from an existing report's clinical content (design D2–D4), the source
is never mutated, and the timeline card exposes the action only to users
holding ``events.add_event`` (design D5).
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.forms import DischargeReportDuplicateForm
from apps.dischargereports.models import DischargeReport
from apps.dischargereports.services.permissions import can_edit_discharge_report
from apps.patients.models import Patient, PatientAdmission

User = get_user_model()

DUPLICATED_FIELDS = (
    "medical_specialty",
    "admission_date",
    "discharge_date",
    "admission_history",
    "problems_and_diagnosis",
    "exams_list",
    "procedures_list",
    "inpatient_medical_history",
    "discharge_status",
    "discharge_recommendations",
)


class DischargeReportDuplicateViewTests(TestCase):
    """Duplicate route, form prefill and copy semantics."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="dup_doctor",
            email="dup_doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        cls.doctor.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="events", codename="add_event"
            )
        )
        cls.reader = User.objects.create_user(
            username="dup_reader",
            email="dup_reader@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Duplicated Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        # An active admission gives the create form its own admission/discharge
        # date defaults, so the prefill assertions prove the source wins.
        cls.active_admission = PatientAdmission.objects.create(
            patient=cls.patient,
            admission_datetime=timezone.now() - timedelta(days=5),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        expired_finalized_at = timezone.now() - timedelta(hours=48)
        cls.source = DischargeReport.objects.create(
            patient=cls.patient,
            event_datetime=timezone.now() - timedelta(days=40),
            description="Relatório de Alta",
            admission_date=date(2024, 3, 1),
            discharge_date=date(2024, 3, 10),
            medical_specialty="Cardiologia",
            admission_history="História da admissão de origem.",
            problems_and_diagnosis="Diagnósticos de origem.",
            exams_list="Exames de origem.",
            procedures_list="Procedimentos de origem.",
            inpatient_medical_history="Evolução da internação de origem.",
            discharge_status="Alta estável.",
            discharge_recommendations="Retorno ambulatorial em 7 dias.",
            is_draft=False,
            finalized_at=expired_finalized_at,
            finalized_by=cls.doctor,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        # Legacy creation anchor far outside the 24h correction window: the
        # source final is expired but must remain duplicable.
        DischargeReport.objects.filter(pk=cls.source.pk).update(
            created_at=timezone.now() - timedelta(days=40),
        )
        cls.source.refresh_from_db()

        cls.source_snapshot = {
            "admission_date": cls.source.admission_date,
            "discharge_date": cls.source.discharge_date,
            "medical_specialty": cls.source.medical_specialty,
            "admission_history": cls.source.admission_history,
            "problems_and_diagnosis": cls.source.problems_and_diagnosis,
            "exams_list": cls.source.exams_list,
            "procedures_list": cls.source.procedures_list,
            "inpatient_medical_history": cls.source.inpatient_medical_history,
            "discharge_status": cls.source.discharge_status,
            "discharge_recommendations": cls.source.discharge_recommendations,
            "event_datetime": cls.source.event_datetime,
            "is_draft": cls.source.is_draft,
            "finalized_at": cls.source.finalized_at,
            "finalized_by_id": cls.source.finalized_by_id,
            "created_by_id": cls.source.created_by_id,
            "updated_by_id": cls.source.updated_by_id,
        }

    def setUp(self):
        self.client = Client()
        self.client.login(username="dup_doctor", password="testpass123")

    def _duplicate_url(self, pk=None):
        return reverse(
            "apps.dischargereports:dischargereport_duplicate",
            kwargs={"pk": pk or self.source.pk},
        )

    def _timeline_url(self):
        return reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def _form_data(self, **overrides):
        """Return a complete duplicate POST payload built from the source."""
        data = {
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "admission_date": self.source.admission_date.strftime("%Y-%m-%d"),
            "discharge_date": self.source.discharge_date.strftime("%Y-%m-%d"),
            "medical_specialty": self.source.medical_specialty,
            "admission_history": self.source.admission_history,
            "problems_and_diagnosis": self.source.problems_and_diagnosis,
            "exams_list": self.source.exams_list,
            "procedures_list": self.source.procedures_list,
            "inpatient_medical_history": self.source.inpatient_medical_history,
            "discharge_status": self.source.discharge_status,
            "discharge_recommendations": self.source.discharge_recommendations,
        }
        data.update(overrides)
        return data

    def _copies(self):
        return DischargeReport.all_objects.filter(patient=self.patient).exclude(
            pk=self.source.pk
        )

    # R1 — route

    def test_duplicate_route_reverses_to_documented_path(self):
        self.assertEqual(
            self._duplicate_url(),
            f"/dischargereports/{self.source.pk}/duplicate/",
        )

    # R2/D4 — prefill

    def test_duplicate_get_prefills_content_fields_from_source(self):
        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIsInstance(form, DischargeReportDuplicateForm)
        for name in DUPLICATED_FIELDS:
            self.assertEqual(
                form.fields[name].initial,
                getattr(self.source, name),
                f"{name} was not prefilled from the source",
            )

        content = response.content.decode()
        self.assertIn("História da admissão de origem.", content)
        self.assertIn("Retorno ambulatorial em 7 dias.", content)

    def test_duplicate_get_prefill_uses_field_level_initial(self):
        """Design D4: the view must not pass form-level initial."""
        response = self.client.get(self._duplicate_url())

        form = response.context["form"]
        for name in DUPLICATED_FIELDS:
            self.assertNotIn(name, form.initial)

    def test_duplicate_get_keeps_source_dates_over_admission_defaults(self):
        """Source dates differ from the active-admission defaults and win."""
        admission_default = self.active_admission.admission_datetime.date()
        self.assertNotEqual(self.source.admission_date, admission_default)
        self.assertNotEqual(self.source.discharge_date, timezone.localdate())

        response = self.client.get(self._duplicate_url())

        form = response.context["form"]
        self.assertEqual(form.fields["admission_date"].initial, date(2024, 3, 1))
        self.assertEqual(form.fields["discharge_date"].initial, date(2024, 3, 10))

    def test_duplicate_get_defaults_event_datetime_to_now(self):
        response = self.client.get(self._duplicate_url())

        initial = response.context["form"].fields["event_datetime"].initial
        self.assertIsInstance(initial, str)
        now_local = timezone.now().astimezone(timezone.get_default_timezone())
        # The field renders to the minute, so allow the neighbouring minutes.
        allowed = {
            (now_local - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M"),
            now_local.strftime("%Y-%m-%dT%H:%M"),
            (now_local + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M"),
        }
        self.assertIn(initial, allowed)
        source_initial = (
            self.source.event_datetime
            .astimezone(timezone.get_default_timezone())
            .strftime("%Y-%m-%dT%H:%M")
        )
        self.assertNotEqual(initial, source_initial)

    # R4 — template

    def test_duplicate_get_renders_duplicate_template(self):
        response = self.client.get(self._duplicate_url())

        self.assertTemplateUsed(
            response, "dischargereports/dischargereport_duplicate.html"
        )
        self.assertContains(response, "Duplicar Relatório de Alta")
        self.assertContains(response, "Duplicated Patient")
        self.assertContains(response, 'name="save_draft"')
        self.assertContains(response, 'name="save_final"')
        self.assertEqual(self._copies().count(), 0)

    # R3/D2 — draft copy

    def test_duplicate_post_creates_independent_draft(self):
        response = self.client.post(self._duplicate_url(), self._form_data())

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self._timeline_url(), fetch_redirect_response=False)

        copy = self._copies().get()
        self.assertEqual(copy.patient, self.patient)
        self.assertTrue(copy.is_draft)
        self.assertEqual(copy.created_by, self.doctor)
        self.assertEqual(copy.updated_by, self.doctor)
        self.assertIsNone(copy.finalized_at)
        self.assertIsNone(copy.finalized_by)
        self.assertEqual(copy.admission_date, date(2024, 3, 1))
        self.assertEqual(copy.discharge_date, date(2024, 3, 10))
        self.assertEqual(copy.medical_specialty, "Cardiologia")
        self.assertEqual(
            copy.discharge_recommendations, "Retorno ambulatorial em 7 dias."
        )
        self.assertEqual(copy.event_type, self.source.event_type)

        success_messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("duplicad" in message for message in success_messages),
            success_messages,
        )

    def test_duplicate_post_with_save_final_stamps_the_copy_only(self):
        response = self.client.post(
            self._duplicate_url(), self._form_data(save_final="Salvar Definitivo")
        )

        self.assertEqual(response.status_code, 302)
        copy = self._copies().get()
        self.assertFalse(copy.is_draft)
        self.assertIsNotNone(copy.finalized_at)
        self.assertEqual(copy.finalized_by, self.doctor)

        self.source.refresh_from_db()
        self.assertFalse(self.source.is_draft)
        self.assertEqual(self.source.finalized_at, self.source_snapshot["finalized_at"])
        self.assertEqual(self.source.finalized_by_id, self.doctor.pk)

    # R6 — expired final stays duplicable

    def test_duplicate_of_expired_final_is_allowed_and_born_draft(self):
        self.assertFalse(self.source.is_within_finalization_window)
        self.assertFalse(can_edit_discharge_report(self.doctor, self.source))

        response = self.client.get(self._duplicate_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self._duplicate_url(), self._form_data())

        self.assertEqual(response.status_code, 302)
        copy = self._copies().get()
        self.assertTrue(copy.is_draft)
        self.assertIsNone(copy.finalized_at)
        self.assertIsNone(copy.finalized_by)

        self.source.refresh_from_db()
        self.assertFalse(self.source.is_draft)
        self.assertEqual(self.source.finalized_at, self.source_snapshot["finalized_at"])
        self.assertEqual(self.source.finalized_by, self.doctor)

    def test_duplicate_leaves_the_source_unchanged(self):
        self.client.get(self._duplicate_url())
        self.client.post(self._duplicate_url(), self._form_data())

        self.source.refresh_from_db()
        for name, expected in self.source_snapshot.items():
            self.assertEqual(getattr(self.source, name), expected, name)

    # R6 — access control

    def test_duplicate_get_denied_without_patient_access(self):
        with patch(
            "apps.dischargereports.views.can_access_patient", return_value=False
        ):
            response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_post_denied_without_patient_access(self):
        with patch(
            "apps.dischargereports.views.can_access_patient", return_value=False
        ):
            response = self.client.post(self._duplicate_url(), self._form_data())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._copies().count(), 0)

    def test_duplicate_unknown_report_returns_404(self):
        response = self.client.get(
            self._duplicate_url(pk="00000000-0000-0000-0000-000000000000")
        )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_get_requires_login(self):
        self.client.logout()

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    # R5/D5 — timeline card gating

    def test_timeline_card_shows_duplicate_action_with_add_event(self):
        response = self.client.get(self._timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._duplicate_url())
        self.assertContains(response, "bi-files")
        self.assertContains(response, "btn-outline-info")
        self.assertContains(response, 'aria-label="Duplicar relatório de alta"')

    def test_timeline_card_hides_duplicate_action_without_add_event(self):
        self.client.logout()
        self.client.login(username="dup_reader", password="testpass123")

        response = self.client.get(self._timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver relatório completo")
        self.assertNotContains(response, self._duplicate_url())
        self.assertNotContains(response, 'aria-label="Duplicar relatório de alta"')
