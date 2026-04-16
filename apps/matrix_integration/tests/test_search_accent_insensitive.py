from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.matrix_integration.bot.search import (
    SearchQuery,
    rank_patient_candidates,
    search_inpatients,
)
from apps.patients.models import Patient, PatientAdmission, Ward


User = get_user_model()


class MatrixPatientSearchAccentInsensitiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="matrix-search-user",
            email="matrix-search-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.ward = Ward.objects.create(
            name="Unidade de Terapia Intensiva",
            abbreviation="UTI",
            created_by=self.user,
            updated_by=self.user,
        )

    def _create_admission(self, *, name, bed="101", days_ago=1):
        patient = Patient.objects.create(
            name=name,
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            bed=bed,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        return PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timedelta(days=days_ago),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed=bed,
            ward=self.ward,
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_search_inpatients_matches_name_without_diacritics(self):
        target = self._create_admission(name="João Ferreira")

        query = SearchQuery(name_terms=["joao"], record_number=None, bed=None, ward=None)
        results = search_inpatients(query)

        self.assertIn(target, results)

    def test_rank_patient_candidates_scores_name_without_diacritics(self):
        match = self._create_admission(name="José Pereira", days_ago=2)
        other = self._create_admission(name="Maria Pereira", days_ago=2)

        query = SearchQuery(name_terms=["jose"], record_number=None, bed=None, ward=None)
        ranked = rank_patient_candidates([other, match], query)

        self.assertEqual(ranked[0], match)
