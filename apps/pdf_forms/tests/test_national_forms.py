from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import MedicalProcedure
from apps.pdf_forms.models import PDFFormSubmission, PDFFormTemplate
from apps.pdf_forms.tests.factories import UserFactory, PatientFactory, PDFFormTemplateFactory
from apps.patients.models import Patient


class APACFormTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user, updated_by=self.user)
        self.client.force_login(self.user)

        PDFFormTemplateFactory(
            form_type='APAC',
            hospital_specific=False,
            created_by=self.user
        )

        self.proc_main = MedicalProcedure.objects.create(
            code="PROC001",
            description="Procedimento Principal"
        )
        self.proc_secondary = MedicalProcedure.objects.create(
            code="PROC002",
            description="Procedimento Secundario"
        )

    def _base_post_data(self):
        return {
            "patient_name": self.patient.name,
            "patient_gender": self.patient.get_gender_display(),
            "patient_birth_date": self.patient.birthday.isoformat(),
            "main_diagnosis": "Diagnostico principal",
            "main_icd": "A00.0",
            "secondary_icd": "",
            "other_icd": "",
            "diagnosis_notes": "",
        }

    def test_apac_requires_main_procedure(self):
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("main_procedure_display", form.errors)

    def test_apac_form_includes_procedure_search_script(self):
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/api/procedures/search/")
        self.assertContains(response, "procedureInputs")

    def test_apac_rejects_duplicate_procedures(self):
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "secondary_procedure_1": str(self.proc_main.id),
            "secondary_procedure_1_display": f"{self.proc_main.code} - {self.proc_main.description}",
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("main_procedure_display", form.errors)
        self.assertIn("secondary_procedure_1_display", form.errors)

    def test_apac_persists_procedure_keys(self):
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "secondary_procedure_1": str(self.proc_secondary.id),
            "secondary_procedure_1_display": f"{self.proc_secondary.code} - {self.proc_secondary.description}",
        })

        with self.settings(HOSPITAL_CONFIG={"name": "Test Hospital", "cnes": "CNES123"}):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.objects.latest("created_at")
        form_data = submission.form_data

        self.assertEqual(form_data["main_procedure_id"], str(self.proc_main.id))
        self.assertEqual(form_data["main_procedure_code"], self.proc_main.code)
        self.assertEqual(form_data["main_procedure_description"], self.proc_main.description)
        self.assertEqual(form_data["secondary_procedure_1_id"], str(self.proc_secondary.id))
        self.assertEqual(form_data["secondary_procedure_1_code"], self.proc_secondary.code)
        self.assertEqual(form_data["secondary_procedure_1_description"], self.proc_secondary.description)

        self.assertEqual(form_data["secondary_procedure_2_id"], "")
        self.assertEqual(form_data["secondary_procedure_2_code"], "")
        self.assertEqual(form_data["secondary_procedure_2_description"], "")
        self.assertEqual(form_data["main_procedure_quantity"], "")
        self.assertEqual(form_data["secondary_procedure_1_qty"], "")
        self.assertEqual(form_data["hospital_name"], "Test Hospital")
        self.assertEqual(form_data["hospital_cnes"], "CNES123")

    def test_apac_sets_gender_checkbox_fields_from_patient(self):
        self.patient.gender = Patient.GenderChoices.MALE
        self.patient.save(update_fields=["gender"])

        template = PDFFormTemplate.objects.get(form_type='APAC')
        template.form_fields = {
            "sections": {},
            "fields": {
                "gender_masc": {
                    "type": "boolean",
                    "label": "Masculino",
                    "x": 0,
                    "y": 0,
                    "width": 0.5,
                    "height": 0.3,
                },
                "gender_fem": {
                    "type": "boolean",
                    "label": "Feminino",
                    "x": 0,
                    "y": 0,
                    "width": 0.5,
                    "height": 0.3,
                },
            },
        }
        template.save(update_fields=["form_fields"])

        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.objects.latest("created_at")
        form_data = submission.form_data

        self.assertTrue(form_data["gender_masc"])
        self.assertFalse(form_data["gender_fem"])
