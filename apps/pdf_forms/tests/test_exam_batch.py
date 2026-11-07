"""S1: batch exam-request capture (lote de exames / chequinho).

Covers R1-R8: batch page render, atomic creation with shared batch_id,
invalid-row rollback, 12-item server limit, supervision parity,
form_select section/card, timeline redirect, legacy flow preserved.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.tests.helpers import create_navigation_user
from apps.pdf_forms.models import PDFFormSubmission

from ..tests.factories import (
    PatientFactory,
    PDFFormTemplateFactory,
)

User = get_user_model()

EXAM_FORM_FIELDS = {
    "doctor": {
        "type": "text",
        "label": "Profissional Solicitante",
        "required": False,
    },
    "examCode": {
        "type": "text",
        "label": "Código",
        "required": False,
    },
    "currentDate": {
        "type": "date",
        "label": "Data",
        "required": False,
    },
    "patientName": {
        "type": "text",
        "label": "Nome",
        "required": False,
    },
    "examRequested": {
        "type": "text",
        "label": "Exame Solicitado",
        "required": False,
    },
    "requestReason": {
        "type": "text",
        "label": "Motivo da Solicitação",
        "required": False,
    },
    "patientAddress": {
        "type": "text",
        "label": "Endereço do Paciente",
        "required": False,
    },
    "doctorRegistrationNumber": {
        "type": "text",
        "label": "Registro Profissional",
        "required": False,
    },
}


def make_exam_template(user, name="Solicitação de Exames SUS"):
    return PDFFormTemplateFactory(
        name=name,
        form_fields=dict(EXAM_FORM_FIELDS),
        created_by=user,
    )


class ExamBatchCaptureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="exam-batch-doctor",
            email="exam-batch-doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.student = create_navigation_user(
            username="exam-batch-student",
            email="exam-batch-student@example.com",
            password="testpass123",
            profession_type=User.STUDENT,
        )
        cls.patient = PatientFactory(
            created_by=cls.doctor, updated_by=cls.doctor
        )
        cls.template = make_exam_template(cls.doctor)

    def _batch_url(self):
        return reverse("pdf_forms:exam_batch", kwargs={"patient_id": self.patient.pk})

    def _valid_post(self, exams, **shared_overrides):
        shared = {
            "requestReason": "Dor torácica",
            "currentDate": "2026-11-01",
            "doctor": "Dra. Teste",
            "doctorRegistrationNumber": "12345",
        }
        shared.update(shared_overrides)
        data = dict(shared)
        data.update(
            {
                "exams-TOTAL_FORMS": str(len(exams)),
                "exams-INITIAL_FORMS": "0",
                "exams-MIN_NUM_FORMS": "1",
                "exams-MAX_NUM_FORMS": "12",
            }
        )
        for i, exam in enumerate(exams):
            data[f"exams-{i}-examRequested"] = exam.get("examRequested", "")
            data[f"exams-{i}-examCode"] = exam.get("examCode", "")
        return data

    def test_batch_page_renders_shared_fields_and_formset(self):
        """R1: GET renders shared fields with auto-fills + add-exam button."""
        self.client.force_login(self.doctor)
        response = self.client.get(self._batch_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "requestReason")
        self.assertContains(response, "Adicionar exame")
        self.assertContains(response, 'name="save_final"')

    def test_batch_page_hides_finalize_action_from_students(self):
        """R5 parity: students see only the draft action on the batch page."""
        self.client.force_login(self.student)
        response = self.client.get(self._batch_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="save_draft"')
        self.assertNotContains(response, 'name="save_final"')

    def test_valid_batch_creates_n_submissions_with_shared_batch_id(self):
        """R2: valid POST creates N rows sharing one batch_id in form_data."""
        self.client.force_login(self.doctor)
        data = self._valid_post(
            [
                {"examRequested": "Hemograma", "examCode": "0202031225"},
                {"examRequested": "Glicemia"},
                {"examRequested": "Raio-X de tórax"},
            ],
            save_final="1",
        )
        response = self.client.post(self._batch_url(), data)
        self.assertEqual(response.status_code, 302)
        submissions = PDFFormSubmission.all_objects.filter(
            patient=self.patient, form_template=self.template
        )
        self.assertEqual(submissions.count(), 3)
        batch_ids = {s.form_data.get("batch_id") for s in submissions}
        self.assertEqual(len(batch_ids), 1)
        batch_id = batch_ids.pop()
        self.assertTrue(batch_id)
        for s in submissions:
            self.assertEqual(s.form_data.get("requestReason"), "Dor torácica")
            self.assertTrue(s.form_data.get("examRequested"))
            self.assertFalse(s.is_draft)

    def test_invalid_exam_row_creates_zero_submissions(self):
        """R3: any invalid exam row rolls back the whole batch."""
        self.client.force_login(self.doctor)
        data = self._valid_post(
            [
                {"examRequested": "Hemograma"},
                {"examRequested": "", "examCode": "0202031225"},
            ],
            save_final="1",
        )
        response = self.client.post(self._batch_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            PDFFormSubmission.all_objects.filter(
                patient=self.patient, form_template=self.template
            ).count(),
            0,
        )

    def test_batch_over_12_items_rejected(self):
        """R4: server rejects batches with more than 12 exams."""
        self.client.force_login(self.doctor)
        exams = [{"examRequested": f"Exame {i}"} for i in range(13)]
        data = self._valid_post(exams, save_final="1")
        response = self.client.post(self._batch_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            PDFFormSubmission.all_objects.filter(
                patient=self.patient, form_template=self.template
            ).count(),
            0,
        )

    def test_student_batch_creates_drafts_and_final_denied(self):
        """R5: student creates drafts; save_final by non-doctor is denied."""
        self.client.force_login(self.student)
        data = self._valid_post(
            [{"examRequested": "Hemograma"}, {"examRequested": "Glicemia"}],
            save_draft="1",
        )
        response = self.client.post(self._batch_url(), data)
        self.assertEqual(response.status_code, 302)
        submissions = PDFFormSubmission.all_objects.filter(
            patient=self.patient, form_template=self.template
        )
        self.assertEqual(submissions.count(), 2)
        for s in submissions:
            self.assertTrue(s.is_draft)

        denied = self._valid_post([{"examRequested": "Hemograma"}], save_final="1")
        response = self.client.post(self._batch_url(), denied)
        self.assertEqual(response.status_code, 403)

    def test_form_select_has_batch_section_and_card(self):
        """R6: form_select shows the batch section + chequinho card."""
        self.client.force_login(self.doctor)
        url = reverse("pdf_forms:form_select", kwargs={"patient_id": self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitação de Exames Múltiplos SUS")
        self.assertContains(response, "Solicitação de Exames SUS (chequinho)")

    def test_success_redirects_to_patient_timeline(self):
        """R7: post-create redirect goes to the patient timeline."""
        self.client.force_login(self.doctor)
        data = self._valid_post([{"examRequested": "Hemograma"}], save_final="1")
        response = self.client.post(self._batch_url(), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            ),
        )

    def test_legacy_single_flow_unchanged(self):
        """R8: submissions without batch_id behave exactly as before."""
        self.client.force_login(self.doctor)
        fill_url = reverse(
            "pdf_forms:form_fill",
            kwargs={"template_id": self.template.pk, "patient_id": self.patient.pk},
        )
        response = self.client.get(fill_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("batch_id", str(response.content.decode()))
