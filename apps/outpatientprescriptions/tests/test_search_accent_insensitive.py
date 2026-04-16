from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.outpatientprescriptions.models import OutpatientPrescription
from apps.outpatientprescriptions.views import OutpatientPrescriptionListView
from apps.patients.models import Patient


User = get_user_model()


class OutpatientPrescriptionSearchAccentInsensitiveTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="prescription-search-user",
            email="prescription-search-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.patient = Patient.objects.create(
            name="João Cardoso",
            birthday="1981-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            description="Prescrição ambulatorial",
            instructions="Hidratação oral.",
            status="draft",
            prescription_date=date.today(),
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )

    @patch("apps.core.permissions.cache.get_user_accessible_patients")
    def test_get_queryset_matches_patient_name_without_diacritics(self, mock_accessible):
        mock_accessible.return_value = [self.patient.id]
        request = self.factory.get("/", {"search": "joao"})
        request.user = self.user

        view = OutpatientPrescriptionListView()
        view.request = request

        queryset = view.get_queryset()

        self.assertIn(self.prescription, queryset)
