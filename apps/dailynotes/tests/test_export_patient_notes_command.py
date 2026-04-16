from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.dailynotes.management.commands.export_patient_notes import Command
from apps.patients.models import Patient


User = get_user_model()


class ExportPatientNotesCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="export-user",
            email="export-user@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.patient = Patient.objects.create(
            name="João de Souza",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_get_patient_by_name_is_accent_insensitive(self):
        command = Command()
        options = {
            "patient_id": None,
            "record_number": None,
            "patient_name": "joao",
        }

        patient = command._get_patient(options)

        self.assertEqual(patient.pk, self.patient.pk)
