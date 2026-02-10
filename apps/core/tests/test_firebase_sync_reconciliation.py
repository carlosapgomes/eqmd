from datetime import datetime, date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID

from django.conf import settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.management.commands.sync_firebase_data import Command
from apps.patients.models import Patient, PatientAdmission, PatientRecordNumber, Ward

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

    def _create_ward(self, ward_id, name, abbreviation):
        return Ward.objects.create(
            id=UUID(ward_id),
            name=name,
            abbreviation=abbreviation,
            created_by=self.user,
            updated_by=self.user,
        )

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
        patient_data["bed"] = "B12"

        result = command.process_firebase_patient("firebase-key-3", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertEqual(admission.initial_bed, "B12")
        patient.refresh_from_db()
        self.assertEqual(patient.status, Patient.Status.INPATIENT)
        self.assertEqual(patient.bed, "B12")
        self.assertEqual(command.admissions_created_count, 1)

    def test_new_import_inpatient_assigns_mapped_ward(self):
        mapped_ward = self._create_ward(
            "8a15753e-0c62-4191-9ca4-dd6f2e8d6326",
            "1A",
            "1A",
        )
        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-import-ward")
        patient_data["ward"] = "-KkXn7i8rYfm-nQlPriE"
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)
        patient_data["bed"] = "A03"

        result = command.process_firebase_patient("firebase-new-ward", patient_data)

        self.assertEqual(result, "imported")
        patient = Patient.objects.get(current_record_number="pt-import-ward")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertEqual(admission.ward_id, mapped_ward.id)
        self.assertEqual(admission.initial_bed, "A03")
        patient.refresh_from_db()
        self.assertEqual(patient.ward_id, mapped_ward.id)
        self.assertEqual(patient.bed, "A03")
        self.assertEqual(command.ward_mapped_count, 1)

    def test_reconcile_inpatient_updates_active_admission_bed_when_changed(self):
        patient = Patient.objects.create(
            name="Bed Update Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            bed="A1",
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-bed-update",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-bed-update",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timezone.timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="A1",
            ward=None,
            admission_diagnosis="Admissão de teste",
            created_by=self.user,
            updated_by=self.user,
        )
        patient.current_admission_id = admission.id
        patient.bed = "A1"
        patient.updated_by = self.user
        patient.save(update_fields=["current_admission_id", "bed", "updated_by", "updated_at"])

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-bed-update")
        patient_data["bed"] = "B4"

        result = command.process_firebase_patient("firebase-key-bed-update", patient_data)

        self.assertEqual(result, "reconciled")
        admission.refresh_from_db()
        self.assertEqual(admission.initial_bed, "B4")
        patient.refresh_from_db()
        self.assertEqual(patient.bed, "B4")

    def test_reconcile_inpatient_intermediario_maps_to_intermediario_b(self):
        inter_b = self._create_ward(
            "fe9fd934-ab73-405b-a73c-87aafb4bc889",
            "Intermediário B",
            "Inter. B",
        )
        patient = Patient.objects.create(
            name="Ward Mapping Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-inter",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-inter",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-inter")
        patient_data["ward"] = "Intermediário"
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)

        result = command.process_firebase_patient("firebase-key-inter", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertEqual(admission.ward_id, inter_b.id)
        patient.refresh_from_db()
        self.assertEqual(patient.ward_id, inter_b.id)
        self.assertEqual(command.ward_mapped_count, 1)

    def test_reconcile_inpatient_intermediario_without_accent_maps(self):
        inter_b = self._create_ward(
            "fe9fd934-ab73-405b-a73c-87aafb4bc889",
            "Intermediário B",
            "Inter. B",
        )
        patient = Patient.objects.create(
            name="Ward Mapping Accent Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-inter-no-accent",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-inter-no-accent",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-inter-no-accent")
        patient_data["ward"] = "  intermediario  "
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)

        result = command.process_firebase_patient("firebase-key-inter-no-accent", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertEqual(admission.ward_id, inter_b.id)
        patient.refresh_from_db()
        self.assertEqual(patient.ward_id, inter_b.id)
        self.assertEqual(command.ward_mapped_count, 1)

    def test_reconcile_inpatient_ward_path_value_maps_by_firebase_key(self):
        ward_1b = self._create_ward(
            "b4d5d745-6557-4981-a947-e96d3987b5b6",
            "1B",
            "1B",
        )
        patient = Patient.objects.create(
            name="Ward Mapping Path Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-path",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-path",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-path")
        patient_data["ward"] = "/wards/-KkXn7iAddX_H-rRVoeW"
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)

        result = command.process_firebase_patient("firebase-key-path", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertEqual(admission.ward_id, ward_1b.id)
        patient.refresh_from_db()
        self.assertEqual(patient.ward_id, ward_1b.id)
        self.assertEqual(command.ward_mapped_count, 1)

    def test_reconcile_inpatient_retired_wards_map_to_none(self):
        command = self._build_command()

        for index, ward_name in enumerate(["Hosp. Dia", "Anexo"], start=1):
            patient = Patient.objects.create(
                name=f"Retired Ward Patient {index}",
                birthday=date(1990, 1, 1),
                gender=Patient.GenderChoices.MALE,
                status=Patient.Status.OUTPATIENT,
                created_by=self.user,
                updated_by=self.user,
            )
            firebase_key = f"firebase-key-retired-{index}"
            pt_rec_n = f"pt-retired-{index}"
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=firebase_key,
                is_current=False,
                created_by=self.user,
                updated_by=self.user,
            )
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=pt_rec_n,
                is_current=True,
                created_by=self.user,
                updated_by=self.user,
            )

            patient_data = self._build_patient_data("inpatient", pt_rec_n=pt_rec_n)
            patient_data["ward"] = ward_name
            patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)

            result = command.process_firebase_patient(firebase_key, patient_data)
            self.assertEqual(result, "reconciled")

            admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
            self.assertIsNotNone(admission)
            self.assertIsNone(admission.ward)

        self.assertEqual(command.ward_mapped_to_none_count, 2)
        self.assertEqual(command.ward_unresolved_count, 0)

    def test_reconcile_inpatient_unresolved_ward_does_not_fail(self):
        patient = Patient.objects.create(
            name="Unknown Ward Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-unknown",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-unknown",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-unknown")
        patient_data["ward"] = "Unknown Legacy Ward"
        patient_data["lastAdmissionDate"] = int(datetime(2024, 1, 11).timestamp() * 1000)

        result = command.process_firebase_patient("firebase-key-unknown", patient_data)

        self.assertEqual(result, "reconciled")
        admission = PatientAdmission.objects.filter(patient=patient, is_active=True).first()
        self.assertIsNotNone(admission)
        self.assertIsNone(admission.ward)
        self.assertEqual(command.ward_unresolved_count, 1)

    def test_reconcile_inpatient_updates_active_admission_ward_when_changed(self):
        ward_1a = self._create_ward(
            "8a15753e-0c62-4191-9ca4-dd6f2e8d6326",
            "1A",
            "1A",
        )
        ward_1b = self._create_ward(
            "b4d5d745-6557-4981-a947-e96d3987b5b6",
            "1B",
            "1B",
        )
        patient = Patient.objects.create(
            name="Ward Update Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            ward=ward_1a,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="firebase-key-ward-update",
            is_current=False,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="pt-ward-update",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timezone.timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="A1",
            ward=ward_1a,
            admission_diagnosis="Admissão de teste",
            created_by=self.user,
            updated_by=self.user,
        )
        patient.current_admission_id = admission.id
        patient.ward = ward_1a
        patient.updated_by = self.user
        patient.save(update_fields=["current_admission_id", "ward", "updated_by", "updated_at"])

        command = self._build_command()
        patient_data = self._build_patient_data("inpatient", pt_rec_n="pt-ward-update")
        patient_data["ward"] = "-KkXn7iAddX_H-rRVoeW"

        result = command.process_firebase_patient("firebase-key-ward-update", patient_data)

        self.assertEqual(result, "reconciled")
        admission.refresh_from_db()
        self.assertEqual(admission.ward_id, ward_1b.id)
        patient.refresh_from_db()
        self.assertEqual(patient.ward_id, ward_1b.id)
        self.assertEqual(command.ward_updated_count, 1)

    def test_resolve_file_path_falls_back_to_base_dir_when_cwd_differs(self):
        command = self._build_command()
        expected = Path(settings.BASE_DIR) / "fixtures/firebase-ward-map.json"

        with TemporaryDirectory() as temp_dir:
            with patch(
                "apps.core.management.commands.sync_firebase_data.Path.cwd",
                return_value=Path(temp_dir),
            ):
                resolved = command._resolve_file_path("fixtures/firebase-ward-map.json")

        self.assertEqual(resolved, expected)
        self.assertTrue(resolved.exists())

    def test_load_ward_mapping_works_when_cwd_differs_from_project_root(self):
        command = self._build_command()

        with TemporaryDirectory() as temp_dir:
            with patch(
                "apps.core.management.commands.sync_firebase_data.Path.cwd",
                return_value=Path(temp_dir),
            ):
                command.load_ward_mapping()

        self.assertTrue(command.ward_mapping_loaded)
        self.assertIn(
            "-KkXn7i8rYfm-nQlPriE",
            command.firebase_ward_to_eqmd_ward_id,
        )
