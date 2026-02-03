from datetime import datetime, date
from io import StringIO

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.management.commands.sync_firebase_data import Command
from apps.patients.models import Patient, PatientAdmission, PatientRecordNumber

User = get_user_model()


class FirebaseSyncReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            password_change_required=False,
            terms_accepted=True,
        )

    def _build_patient_data(self, status, pt_rec_n="pt-123"):
        return {
            "name": "Test Patient",
            "ptRecN": pt_rec_n,
            "birthDt": int(datetime(1990, 1, 1).timestamp() * 1000),
            "status": status,
            "registrationDt": int(datetime(2024, 1, 1).timestamp() * 1000),
        }

    def _build_command(self):
        command = Command()
        command.dry_run = False
        command.import_user = self.user
        command.stdout = StringIO()
        command.reconciled_patients_count = 0
        command.admissions_closed_count = 0
        command.admissions_created_count = 0
        return command

    def test_reconcile_outpatient_closes_active_admission(self):
        patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-1",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-123",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timezone.timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="B1",
            ward=None,
            admission_diagnosis="Admissão de teste",
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("outpatient")

        result = command.process_firebase_patient("firebase-key-1", patient_data)

        self.assertEqual(result, "reconciled")
        admission.refresh_from_db()
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.discharge_type, PatientAdmission.DischargeType.MEDICAL)
        patient.refresh_from_db()
        self.assertEqual(patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(command.admissions_closed_count, 1)

    def test_reconcile_deceased_sets_status_and_discharge_type(self):
        patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-2",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-456",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timezone.timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="B2",
            ward=None,
            admission_diagnosis="Admissão de teste",
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("deceased", pt_rec_n="pt-456")

        result = command.process_firebase_patient("firebase-key-2", patient_data)

        self.assertEqual(result, "reconciled")
        admission.refresh_from_db()
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.discharge_type, PatientAdmission.DischargeType.DEATH)
        patient.refresh_from_db()
        self.assertEqual(patient.status, Patient.Status.DECEASED)

    def test_reconcile_inpatient_creates_active_admission(self):
        patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-3",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-789",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-789")
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 10).timestamp() * 1000)

        result = command.process_firebase_patient("firebase-key-3", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        patient.refresh_from_db()
        self.assertEqual(patient.status, Patient.Status.INPATIENT)
        self.assertEqual(command.admissions_created_count, 1)
