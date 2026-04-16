from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.historyandphysicals.models import HistoryAndPhysical
from apps.historyandphysicals.views import HistoryAndPhysicalListView
from apps.patients.models import Patient


User = get_user_model()


class HistoryAndPhysicalSearchAccentInsensitiveTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="hp-search-user",
            email="hp-search-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.patient = Patient.objects.create(
            name="João Teixeira",
            birthday="1986-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.record = HistoryAndPhysical.objects.create(
            patient=self.patient,
            description="Anamnese",
            content="Paciente em bom estado geral.",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )

    @patch("apps.core.permissions.cache.get_user_accessible_patients")
    def test_get_queryset_matches_patient_name_without_diacritics(self, mock_accessible):
        mock_accessible.return_value = [self.patient.id]
        request = self.factory.get("/", {"search": "joao"})
        request.user = self.user

        view = HistoryAndPhysicalListView()
        view.request = request

        queryset = view.get_queryset()

        self.assertIn(self.record, queryset)
