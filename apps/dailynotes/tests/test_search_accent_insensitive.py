from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.dailynotes.models import DailyNote
from apps.dailynotes.views import DailyNoteListView
from apps.patients.models import Patient


User = get_user_model()


class DailyNoteSearchAccentInsensitiveTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="dailynote-search-user",
            email="dailynote-search-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.patient = Patient.objects.create(
            name="João Batista",
            birthday="1984-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.note = DailyNote.objects.create(
            patient=self.patient,
            description="Evolução diária",
            content="Paciente sem intercorrências.",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )

    @patch("apps.core.permissions.utils.get_user_accessible_patients")
    def test_get_queryset_matches_patient_name_without_diacritics(self, mock_accessible):
        mock_accessible.return_value = Patient.objects.filter(pk=self.patient.pk)
        request = self.factory.get("/", {"search": "joao"})
        request.user = self.user

        view = DailyNoteListView()
        view.request = request

        queryset = view.get_queryset()

        self.assertIn(self.note, queryset)
