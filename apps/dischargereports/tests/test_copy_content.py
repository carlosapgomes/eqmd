from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.patients.models import Patient

User = get_user_model()


class DischargeReportCopyTextTests(TestCase):
    """Unit tests for DischargeReport.get_copy_text() formatting."""

    def _build_report(self, **overrides):
        params = {
            "admission_date": date(2024, 3, 1),
            "discharge_date": date(2024, 3, 10),
            "medical_specialty": "Cardiologia",
            "problems_and_diagnosis": "IAMCSST Killip I.",
            "admission_history": "Dor torácica há 2h.",
            "exams_list": "ECG, troponina.",
            "procedures_list": "Angioplastia primária.",
            "inpatient_medical_history": "Evolução sem intercorrências.",
            "discharge_status": "Estável, assintomático.",
            "discharge_recommendations": "Retorno em 7 dias.",
        }
        params.update(overrides)
        return DischargeReport(**params)

    def test_full_report_formats_header_dates_and_all_sections(self):
        report = self._build_report()

        self.assertEqual(
            report.get_copy_text(),
            "RELATÓRIO DE ALTA — Cardiologia\n"
            "Admissão: 01/03/2024 | Alta: 10/03/2024 (9 dias)\n"
            "\n"
            "PROBLEMAS E DIAGNÓSTICOS:\n"
            "IAMCSST Killip I.\n"
            "\n"
            "HISTÓRIA DA ADMISSÃO:\n"
            "Dor torácica há 2h.\n"
            "\n"
            "LISTA DE EXAMES:\n"
            "ECG, troponina.\n"
            "\n"
            "LISTA DE PROCEDIMENTOS:\n"
            "Angioplastia primária.\n"
            "\n"
            "HISTÓRIA MÉDICA DA INTERNAÇÃO:\n"
            "Evolução sem intercorrências.\n"
            "\n"
            "STATUS DA ALTA:\n"
            "Estável, assintomático.\n"
            "\n"
            "RECOMENDAÇÕES DE ALTA:\n"
            "Retorno em 7 dias.",
        )

    def test_blank_and_whitespace_only_sections_are_skipped(self):
        report = self._build_report(
            admission_history="",
            exams_list="   ",
            procedures_list="",
            inpatient_medical_history="",
            discharge_status="",
        )

        text = report.get_copy_text()

        self.assertIn("PROBLEMAS E DIAGNÓSTICOS:\nIAMCSST Killip I.", text)
        self.assertIn("RECOMENDAÇÕES DE ALTA:\nRetorno em 7 dias.", text)
        self.assertNotIn("HISTÓRIA DA ADMISSÃO", text)
        self.assertNotIn("LISTA DE EXAMES", text)
        self.assertNotIn("LISTA DE PROCEDIMENTOS", text)
        self.assertNotIn("HISTÓRIA MÉDICA DA INTERNAÇÃO", text)
        self.assertNotIn("STATUS DA ALTA", text)

    def test_singular_day_duration(self):
        report = self._build_report(
            admission_date=date(2024, 3, 1),
            discharge_date=date(2024, 3, 2),
        )

        self.assertIn(
            "Admissão: 01/03/2024 | Alta: 02/03/2024 (1 dia)", report.get_copy_text()
        )

    def test_special_characters_newlines_and_surrounding_whitespace(self):
        report = self._build_report(
            problems_and_diagnosis='  Dor "intensa" & febre — evolução:\n\nmelhora progressiva.  ',
            admission_history="",
            exams_list="",
            procedures_list="",
            inpatient_medical_history="",
            discharge_status="",
            discharge_recommendations="",
        )

        self.assertIn(
            'PROBLEMAS E DIAGNÓSTICOS:\nDor "intensa" & febre — evolução:\n\nmelhora progressiva.',
            report.get_copy_text(),
        )

    def test_section_order_matches_pdf_and_detail(self):
        text = self._build_report().get_copy_text()
        labels = [
            "PROBLEMAS E DIAGNÓSTICOS:",
            "HISTÓRIA DA ADMISSÃO:",
            "LISTA DE EXAMES:",
            "LISTA DE PROCEDIMENTOS:",
            "HISTÓRIA MÉDICA DA INTERNAÇÃO:",
            "STATUS DA ALTA:",
            "RECOMENDAÇÕES DE ALTA:",
        ]
        positions = [text.index(label) for label in labels]

        self.assertEqual(positions, sorted(positions))

    def test_missing_specialty_and_dates_do_not_crash(self):
        report = DischargeReport()

        text = report.get_copy_text()

        self.assertTrue(text.startswith("RELATÓRIO DE ALTA\nAdmissão: — | Alta: —"))
        self.assertNotIn("(", text.splitlines()[1])


class DischargeReportCopyButtonViewTests(TestCase):
    """The timeline card and detail page expose the copy button."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="copyuser",
            email="copy@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.patient = Patient.objects.create(
            name="Copy Button Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user,
        )
        self.report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Copy button report",
            admission_date=date(2024, 3, 1),
            discharge_date=date(2024, 3, 10),
            medical_specialty="Cardiologia",
            problems_and_diagnosis='Dor "intensa" & febre',
            admission_history="História da admissão",
            exams_list="ECG",
            procedures_list="Angioplastia",
            inpatient_medical_history="Evolução",
            discharge_status="Estável",
            discharge_recommendations="Retorno em 7 dias",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.login(username="copyuser", password="testpass123")

    def test_detail_contains_copy_button_with_escaped_content(self):
        url = reverse(
            "apps.dischargereports:dischargereport_detail",
            kwargs={"pk": self.report.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "copy-content-btn")
        self.assertContains(response, "Copiar conteúdo do relatório de alta")
        self.assertContains(response, "PROBLEMAS E DIAGNÓSTICOS:")
        self.assertContains(response, "Dor &quot;intensa&quot; &amp; febre")

    def test_timeline_card_contains_copy_button(self):
        url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "copy-content-btn")
        self.assertContains(response, "Copiar conteúdo do relatório de alta")
        self.assertContains(response, "PROBLEMAS E DIAGNÓSTICOS:")
