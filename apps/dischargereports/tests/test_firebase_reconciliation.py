from datetime import date
from io import StringIO

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.dischargereports.management.commands.import_firebase_discharge_reports import Command
from apps.dischargereports.models import DischargeReport
from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()


class FirebaseDischargeReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            password_change_required=False,
            terms_accepted=True,
        )

        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number="firebase-patient-key",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        self.active_admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timezone.timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed="A1",
            ward=None,
            admission_diagnosis="Admissão de teste",
            created_by=self.user,
            updated_by=self.user,
        )

        self.report_data = {
            "content": {
                "admissionDate": "2024-01-01",
                "dischargeDate": "2024-01-05",
                "specialty": "Cardiologia",
                "admissionHistory": "Paciente admitido...",
                "problemsAndDiagnostics": "Angina instável",
                "examsList": "ECG",
                "proceduresList": "Cateterismo",
                "inpatientMedicalHistory": "Evolução",
                "patientDischargeStatus": "Alta",
                "dischargeRecommendations": "Seguimento",
            },
            "datetime": 1704067200000,
            "patient": "firebase-patient-key",
            "username": "Dr. Test",
        }

    def test_import_closes_active_admission_and_updates_status(self):
        command = Command()
        command.dry_run = False
        command.import_user = self.user
        command.stdout = StringIO()
        command.admissions_closed_count = 0
        command.patients_reconciled_count = 0

        result = command.process_firebase_discharge_report(
            "report-key-1",
            self.report_data,
        )

        self.assertEqual(result, "imported")
        self.assertEqual(DischargeReport.objects.count(), 1)

        self.active_admission.refresh_from_db()
        self.assertFalse(self.active_admission.is_active)
        self.assertEqual(
            self.active_admission.discharge_type,
            PatientAdmission.DischargeType.MEDICAL,
        )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)

        self.assertEqual(command.admissions_closed_count, 1)
        self.assertEqual(command.patients_reconciled_count, 1)
