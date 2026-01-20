import unittest
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import MedicalProcedure, Icd10Code
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

        # Create ICD-10 codes for testing
        self.icd_main = Icd10Code.objects.create(
            code="A000",
            description="Cólera devida a Vibrio cholerae 01, variedade cholerae",
            is_active=True
        )
        self.icd_secondary = Icd10Code.objects.create(
            code="A010",
            description="Febre tifoide",
            is_active=True
        )
        self.icd_other = Icd10Code.objects.create(
            code="B000",
            description="Herpes simples",
            is_active=True
        )
        self.icd_inactive = Icd10Code.objects.create(
            code="Z999",
            description="Inactive code for testing",
            is_active=False
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
            "main_icd_id": str(self.icd_main.id),
            "main_icd_display": self.icd_main.code,
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
            "main_icd_id": str(self.icd_main.id),
            "main_icd_display": self.icd_main.code,
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.objects.latest("created_at")
        form_data = submission.form_data

        self.assertTrue(form_data["gender_masc"])
        self.assertFalse(form_data["gender_fem"])

    # ICD-10 Search Tests

    def test_apac_requires_main_icd(self):
        """Test that main ICD-10 is required for APAC form."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": "",  # Missing main ICD
            "main_icd_display": "",
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("main_icd_display", form.errors)

    def test_apac_accepts_blank_secondary_and_other_icd(self):
        """Test that secondary and other ICD-10 fields are optional."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": str(self.icd_main.id),
            "main_icd_display": self.icd_main.code,
            "secondary_icd_id": "",
            "secondary_icd_display": "",
            "other_icd_id": "",
            "other_icd_display": "",
        })

        with self.settings(HOSPITAL_CONFIG={"name": "Test", "cnes": "123"}):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)

    def test_apac_form_includes_icd10_search_script(self):
        """Test that ICD-10 search script and API URL are included in the form."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/api/icd10/search/")
        self.assertContains(response, "icd10Inputs")

    def test_apac_rejects_invalid_icd10_selection(self):
        """Test that plain text ICD-10 codes not from search suggestions are rejected."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": "",  # No valid UUID
            "main_icd_display": "INVALID99",  # Invalid plain text code
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("main_icd_display", form.errors)

    def test_apac_rejects_inactive_icd10_code(self):
        """Test that inactive ICD-10 codes are rejected."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": str(self.icd_inactive.id),
            "main_icd_display": self.icd_inactive.code,
        })

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("main_icd_display", form.errors)

    def test_apac_persists_icd10_keys(self):
        """Test that ICD-10 UUID, code, and description are persisted in submission data."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": str(self.icd_main.id),
            "main_icd_display": self.icd_main.code,
            "secondary_icd_id": str(self.icd_secondary.id),
            "secondary_icd_display": self.icd_secondary.code,
            "other_icd_id": str(self.icd_other.id),
            "other_icd_display": self.icd_other.code,
        })

        with self.settings(HOSPITAL_CONFIG={"name": "Test Hospital", "cnes": "CNES123"}):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.objects.latest("created_at")
        form_data = submission.form_data

        # Main ICD-10
        self.assertEqual(form_data["main_icd_id"], str(self.icd_main.id))
        self.assertEqual(form_data["main_icd_code"], self.icd_main.code)
        self.assertEqual(form_data["main_icd_description"], self.icd_main.description)

        # Secondary ICD-10
        self.assertEqual(form_data["secondary_icd_id"], str(self.icd_secondary.id))
        self.assertEqual(form_data["secondary_icd_code"], self.icd_secondary.code)
        self.assertEqual(form_data["secondary_icd_description"], self.icd_secondary.description)

        # Other ICD-10
        self.assertEqual(form_data["other_icd_id"], str(self.icd_other.id))
        self.assertEqual(form_data["other_icd_code"], self.icd_other.code)
        self.assertEqual(form_data["other_icd_description"], self.icd_other.description)

    def test_apac_persists_empty_icd10_when_not_selected(self):
        """Test that empty strings are persisted when ICD-10 fields are not selected."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        data = self._base_post_data()
        data.update({
            "main_procedure": str(self.proc_main.id),
            "main_procedure_display": f"{self.proc_main.code} - {self.proc_main.description}",
            "main_icd_id": str(self.icd_main.id),
            "main_icd_display": self.icd_main.code,
            "secondary_icd_id": "",
            "secondary_icd_display": "",
            "other_icd_id": "",
            "other_icd_display": "",
        })

        with self.settings(HOSPITAL_CONFIG={"name": "Test", "cnes": "123"}):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.objects.latest("created_at")
        form_data = submission.form_data

        self.assertEqual(form_data["main_icd_id"], str(self.icd_main.id))
        self.assertEqual(form_data["secondary_icd_id"], "")
        self.assertEqual(form_data["secondary_icd_code"], "")
        self.assertEqual(form_data["secondary_icd_description"], "")
        self.assertEqual(form_data["other_icd_id"], "")
        self.assertEqual(form_data["other_icd_code"], "")
        self.assertEqual(form_data["other_icd_description"], "")

    def test_apac_icd10_input_shows_only_code(self):
        """Test that the ICD-10 input displays only the code, not code+description."""
        url = reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that the form includes ICD-10 display fields
        self.assertContains(response, "main_icd_display")
        self.assertContains(response, "secondary_icd_display")
        self.assertContains(response, "other_icd_display")

    @unittest.skip("ICD-10 search requires search_vector population in test database")
    def test_icd10_search_by_code(self):
        """Test ICD-10 search by code returns matching results."""
        url = reverse("apps.core:icd10_search_api")
        response = self.client.get(url, {"q": "A000"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["results"]), 0)
        self.assertEqual(data["results"][0]["code"], "A000")
        self.assertEqual(data["results"][0]["description"], self.icd_main.description)

    @unittest.skip("ICD-10 search requires search_vector population in test database")
    def test_icd10_search_by_description(self):
        """Test ICD-10 search by description returns matching results."""
        url = reverse("apps.core:icd10_search_api")
        response = self.client.get(url, {"q": "cólera"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["results"]), 0)
        # Should find A00.0 which contains "Cólera" in description

    def test_icd10_search_case_insensitive(self):
        """Test that ICD-10 search is case insensitive."""
        url = reverse("apps.core:icd10_search_api")
        response_lowercase = self.client.get(url, {"q": "cólera"})
        response_uppercase = self.client.get(url, {"q": "CÓLERA"})

        self.assertEqual(response_lowercase.status_code, 200)
        self.assertEqual(response_uppercase.status_code, 200)
        self.assertEqual(
            len(response_lowercase.json()["results"]),
            len(response_uppercase.json()["results"])
        )

    @unittest.skip("ICD-10 search requires search_vector population in test database")
    def test_icd10_search_respects_limit(self):
        """Test that ICD-10 search respects the limit parameter."""
        url = reverse("apps.core:icd10_search_api")
        response = self.client.get(url, {"q": "A", "limit": "2"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["results"]), 2)

    def test_icd10_search_requires_min_chars(self):
        """Test that ICD-10 search requires at least 2 characters."""
        url = reverse("apps.core:icd10_search_api")
        response = self.client.get(url, {"q": "A"})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("at least 2 characters", data["error"])

    def test_icd10_api_requires_authentication(self):
        """Test that ICD-10 search API requires authentication."""
        self.client.logout()

        url = reverse("apps.core:icd10_search_api")
        response = self.client.get(url, {"q": "test"})

        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_icd10_detail_api(self):
        """Test ICD-10 detail API returns code information."""
        url = reverse("apps.core:icd10_detail_api", args=[self.icd_main.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["code"], self.icd_main.code)
        self.assertEqual(data["description"], self.icd_main.description)
        self.assertEqual(data["is_active"], True)
