"""S2 R3/R4/R5: discharge finalize gate, timeline card actions and form roles.

Server-side finalize authorization is the boundary (design D5); the form
buttons are role-aware UX on top of it. The timeline card follows the object
predicate for delete and hides the PDF export of drafts (design D9/D10).
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.patients.models import Patient

User = get_user_model()


def _report_payload(patient, **overrides):
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


class DischargeGateFixtures(TestCase):
    """Shared users, patient and report builders."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="gatedoctor",
            email="gatedoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.student = User.objects.create_user(
            username="gatestudent",
            email="gatestudent@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.STUDENT,
        )
        cls.nurse = User.objects.create_user(
            username="gatenurse",
            email="gatenurse@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        cls.patient = Patient.objects.create(
            name="Gate Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_report(self, *, is_draft, author):
        return DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
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
            created_by=author,
            updated_by=author,
        )

    def _create_url(self):
        return reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

    def _duplicate_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_duplicate",
            kwargs={"pk": report.pk},
        )

    def _update_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": report.pk},
        )

    def _pdf_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_pdf", kwargs={"pk": report.pk}
        )

    def _reports(self):
        return DischargeReport.all_objects.filter(patient=self.patient)


class DischargeFinalizeServerGateTests(DischargeGateFixtures):
    """R3: non-doctors/residents cannot finalize through any discharge path."""

    def test_student_create_with_save_final_is_denied(self):
        self.client.force_login(self.student)

        response = self.client.post(
            self._create_url(), _report_payload(self.patient, save_final="x")
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self._reports().exists())

    def test_student_create_with_save_draft_stays_draft(self):
        self.client.force_login(self.student)

        response = self.client.post(
            self._create_url(), _report_payload(self.patient, save_draft="x")
        )

        self.assertEqual(response.status_code, 302)
        report = self._reports().get()
        self.assertTrue(report.is_draft)
        self.assertIsNone(report.finalized_at)
        self.assertIsNone(report.finalized_by)

    def test_nurse_create_with_save_final_is_denied(self):
        self.client.force_login(self.nurse)

        response = self.client.post(
            self._create_url(), _report_payload(self.patient, save_final="x")
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self._reports().exists())

    def test_doctor_create_with_save_final_records_metadata(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._create_url(), _report_payload(self.patient, save_final="x")
        )

        self.assertEqual(response.status_code, 302)
        report = self._reports().get()
        self.assertFalse(report.is_draft)
        self.assertIsNotNone(report.finalized_at)
        self.assertEqual(report.finalized_by, self.doctor)

    def test_student_update_with_save_final_is_denied(self):
        report = self._create_report(is_draft=True, author=self.student)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(report), _report_payload(self.patient, save_final="x")
        )

        self.assertEqual(response.status_code, 403)
        report.refresh_from_db()
        self.assertTrue(report.is_draft)
        self.assertIsNone(report.finalized_at)
        self.assertIsNone(report.finalized_by)

    def test_student_update_with_save_draft_keeps_the_draft(self):
        report = self._create_report(is_draft=True, author=self.student)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(report),
            _report_payload(self.patient, save_draft="x"),
        )

        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertTrue(report.is_draft)
        self.assertIsNone(report.finalized_at)
        self.assertIsNone(report.finalized_by)

    def test_non_physician_revert_finalize_is_denied(self):
        """R3: reverting a final back to draft is a physician act too."""
        final = self._create_report(is_draft=False, author=self.nurse)
        self.client.force_login(self.nurse)

        response = self.client.post(
            self._update_url(final), _report_payload(self.patient, save_draft="x")
        )

        self.assertEqual(response.status_code, 403)
        final.refresh_from_db()
        self.assertFalse(final.is_draft)

    def test_student_duplicate_with_save_final_is_denied(self):
        source = self._create_report(is_draft=False, author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            self._duplicate_url(source), _report_payload(self.patient, save_final="x")
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._reports().count(), 1)

    def test_student_duplicate_with_save_draft_creates_a_draft(self):
        source = self._create_report(is_draft=False, author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            self._duplicate_url(source), _report_payload(self.patient, save_draft="x")
        )

        self.assertEqual(response.status_code, 302)
        copy = self._reports().exclude(pk=source.pk).get()
        self.assertTrue(copy.is_draft)
        self.assertIsNone(copy.finalized_at)
        self.assertIsNone(copy.finalized_by)


class DischargeFinalizeActionRenderingTests(DischargeGateFixtures):
    """R5: only doctors/residents are offered the finalize button."""

    def _assert_no_finalize_button(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="save_final"')
        self.assertContains(response, 'name="save_draft"')

    def test_student_create_form_offers_no_finalize_button(self):
        self.client.force_login(self.student)

        self._assert_no_finalize_button(self.client.get(self._create_url()))

    def test_nurse_create_form_offers_no_finalize_button(self):
        self.client.force_login(self.nurse)

        self._assert_no_finalize_button(self.client.get(self._create_url()))

    def test_doctor_create_form_offers_finalize_button(self):
        self.client.force_login(self.doctor)

        response = self.client.get(self._create_url())

        self.assertContains(response, 'name="save_final"')

    def test_student_duplicate_form_offers_no_finalize_button(self):
        source = self._create_report(is_draft=False, author=self.doctor)
        self.client.force_login(self.student)

        self._assert_no_finalize_button(self.client.get(self._duplicate_url(source)))

    def test_doctor_duplicate_form_offers_finalize_button(self):
        source = self._create_report(is_draft=False, author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._duplicate_url(source))

        self.assertContains(response, 'name="save_final"')

    def test_student_update_form_offers_no_finalize_button(self):
        report = self._create_report(is_draft=True, author=self.student)
        self.client.force_login(self.student)

        self._assert_no_finalize_button(self.client.get(self._update_url(report)))

    def test_doctor_update_form_offers_finalize_button(self):
        report = self._create_report(is_draft=True, author=self.student)
        self.client.force_login(self.doctor)

        response = self.client.get(self._update_url(report))

        self.assertContains(response, 'name="save_final"')


class DischargeTimelineCardActionTests(DischargeGateFixtures):
    """R4: delete follows the object predicate; drafts hide the PDF action."""

    def _timeline(self, user):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )

    def _delete_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_delete", kwargs={"pk": report.pk}
        )

    def test_draft_card_suppresses_pdf_action(self):
        self._create_report(is_draft=True, author=self.student)

        response = self._timeline(self.doctor)

        self.assertEqual(response.status_code, 200)
        draft = self._reports().get()
        self.assertNotContains(response, self._pdf_url(draft))

    def test_final_card_keeps_pdf_action(self):
        final = self._create_report(is_draft=False, author=self.doctor)

        response = self._timeline(self.doctor)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._pdf_url(final))

    def test_delete_link_ignores_the_django_permission(self):
        draft = self._create_report(is_draft=True, author=self.student)
        self.nurse.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="events", codename="delete_event"
            )
        )

        response = self._timeline(self.nurse)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self._delete_url(draft))

    def test_delete_link_kept_for_the_draft_creator(self):
        draft = self._create_report(is_draft=True, author=self.student)

        response = self._timeline(self.student)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._delete_url(draft))


class DischargeReportPDFDraftGatingTests(DischargeGateFixtures):
    """R2/D10: the discharge PDF denies drafts for every user."""

    def test_pdf_denies_draft(self):
        draft = self._create_report(is_draft=True, author=self.student)
        self.client.force_login(self.doctor)

        response = self.client.get(self._pdf_url(draft))

        self.assertEqual(response.status_code, 404)

    def test_pdf_serves_final(self):
        final = self._create_report(is_draft=False, author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._pdf_url(final))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
