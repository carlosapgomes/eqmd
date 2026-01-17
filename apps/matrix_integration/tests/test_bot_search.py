from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.patients.models import Patient, PatientAdmission, PatientRecordNumber, Ward

from apps.matrix_integration.bot.search import SearchQuery, parse_search_query, rank_patient_candidates


class BotSearchParsingTests(TestCase):
    def test_parse_search_query_with_prefixes(self):
        query = parse_search_query("Joao Silva reg:12345 leito:10 enf:UTI")

        self.assertEqual(query.name_terms, ["Joao", "Silva"])
        self.assertEqual(query.record_number, "12345")
        self.assertEqual(query.bed, "10")
        self.assertEqual(query.ward, "UTI")

    def test_parse_search_query_ignores_long_prefix_values(self):
        long_value = "x" * 51
        query = parse_search_query(f"reg:{long_value} Maria")

        self.assertIsNone(query.record_number)
        self.assertEqual(query.name_terms, ["Maria"])


class BotSearchRankingTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ward = Ward.objects.create(
            name="Unidade de Terapia Intensiva",
            abbreviation="UTI",
            created_by=self.user,
            updated_by=self.user,
        )

    def _create_inpatient(self, name, record_number, admission_days_ago=1, bed="101"):
        patient = Patient.objects.create(
            name=name,
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            bed=bed,
            ward=self.ward,
            current_record_number=record_number,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number=record_number,
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timedelta(days=admission_days_ago),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed=bed,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        return admission

    def test_rank_patient_candidates_prefers_exact_record_number(self):
        admission_exact = self._create_inpatient("Joao Silva", "12345", admission_days_ago=5)
        admission_partial = self._create_inpatient("Joao Silva", "123", admission_days_ago=1)

        query = SearchQuery(name_terms=[], record_number="12345", bed=None, ward=None)
        ranked = rank_patient_candidates([admission_partial, admission_exact], query)

        self.assertEqual(ranked[0].patient.current_record_number, "12345")
