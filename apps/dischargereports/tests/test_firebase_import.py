from datetime import date, datetime
from unittest import skip
from unittest.mock import Mock, patch, MagicMock, mock_open
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from apps.dischargereports.models import DischargeReport

User = get_user_model()


@skip("Firebase import tests disabled per project scope.")
class FirebaseImportTests(TestCase):
    def setUp(self):
        self._init_firebase_patcher = patch(
            'apps.dischargereports.management.commands.import_firebase_discharge_reports.Command.init_firebase'
        )
        self._init_firebase_patcher.start()
        self.addCleanup(self._init_firebase_patcher.stop)

        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            password_change_required=False,
            terms_accepted=True
        )

        # Create patient with record number
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='firebase-patient-key',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        # Sample Firebase data
        self.firebase_data = {
            'report-key-1': {
                'content': {
                    'admissionDate': '2024-01-01',
                    'dischargeDate': '2024-01-05',
                    'specialty': 'Cardiologia',
                    'admissionHistory': 'Paciente admitido com dor torácica...',
                    'problemsAndDiagnostics': 'Angina instável',
                    'examsList': 'ECG, Ecocardiograma',
                    'proceduresList': 'Cateterismo cardíaco',
                    'inpatientMedicalHistory': 'Evolução favorável...',
                    'patientDischargeStatus': 'Alta melhorada',
                    'dischargeRecommendations': 'Seguimento ambulatorial'
                },
                'datetime': 1704067200000,  # 2024-01-01 timestamp
                'patient': 'firebase-patient-key',
                'username': 'Dr. Test'
            }
        }

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_successful_import(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test successful Firebase import"""
        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = self.firebase_data
        mock_db.reference.return_value = mock_ref

        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()

        # Capture command output
        out = StringIO()

        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('1 discharge reports', output)
        self.assertIn('DRY RUN', output)

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_actual_import_creates_objects(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test that actual import creates DischargeReport and PatientAdmission objects"""
        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = self.firebase_data
        mock_db.reference.return_value = mock_ref

        # Run actual import (not dry run)
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            stdout=StringIO()
        )

        # Verify objects were created
        self.assertEqual(DischargeReport.objects.count(), 1)
        self.assertEqual(PatientAdmission.objects.count(), 1)

        report = DischargeReport.objects.first()
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.medical_specialty, 'Cardiologia')
        self.assertFalse(report.is_draft)  # Imported reports are finalized

        admission = PatientAdmission.objects.first()
        self.assertEqual(admission.patient, self.patient)
        self.assertEqual(admission.admission_type, PatientAdmission.AdmissionType.SCHEDULED)
        self.assertFalse(admission.is_active)

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_import_with_nonexistent_patient(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test import with patient that doesn't exist"""
        # Modify Firebase data to reference non-existent patient
        firebase_data_with_missing_patient = self.firebase_data.copy()
        firebase_data_with_missing_patient['report-key-1']['patient'] = 'nonexistent-patient'

        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = firebase_data_with_missing_patient
        mock_db.reference.return_value = mock_ref

        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()

        # Capture command output
        out = StringIO()

        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('Skipped 1 reports', output)
        self.assertIn('Patient not found', output)

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_import_with_invalid_date_format(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test import with invalid date format"""
        # Modify Firebase data to have invalid date
        firebase_data_with_invalid_date = self.firebase_data.copy()
        firebase_data_with_invalid_date['report-key-1']['content']['admissionDate'] = 'invalid-date'

        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = firebase_data_with_invalid_date
        mock_db.reference.return_value = mock_ref

        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()

        # Capture command output
        out = StringIO()

        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('Skipped 1 reports', output)
        self.assertIn('Invalid date format', output)

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_import_with_missing_required_fields(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test import with missing required fields"""
        # Modify Firebase data to remove required fields
        firebase_data_missing_fields = {
            'report-key-1': {
                'content': {
                    'admissionDate': '2024-01-01',
                    'dischargeDate': '2024-01-05',
                    # Missing specialty and other required fields
                },
                'datetime': 1704067200000,
                'patient': 'firebase-patient-key',
                'username': 'Dr. Test'
            }
        }

        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = firebase_data_missing_fields
        mock_db.reference.return_value = mock_ref

        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()

        # Capture command output
        out = StringIO()

        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('Skipped 1 reports', output)
        self.assertIn('Missing required fields', output)

    def test_command_requires_credentials_file(self):
        """Test that command requires credentials file"""
        with self.assertRaises(CommandError):
            call_command(
                'import_firebase_discharge_reports',
                '--database-url', 'https://fake.firebaseio.com',
                '--dry-run',
                stdout=StringIO()
            )

    def test_command_requires_database_url(self):
        """Test that command requires database URL"""
        with self.assertRaises(CommandError):
            call_command(
                'import_firebase_discharge_reports',
                '--credentials-file', '/fake/path.json',
                '--dry-run',
                stdout=StringIO()
            )

    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_import_with_multiple_reports(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test import with multiple reports"""
        # Create multiple patients
        patient2 = Patient.objects.create(
            name='Test Patient 2',
            birthday=date(1995, 1, 1),
            gender=Patient.GenderChoices.FEMALE,
            created_by=self.user,
            updated_by=self.user
        )
        PatientRecordNumber.objects.create(
            patient=patient2,
            record_number='firebase-patient-key-2',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        # Create Firebase data with multiple reports
        firebase_data_multiple = {
            'report-key-1': {
                'content': {
                    'admissionDate': '2024-01-01',
                    'dischargeDate': '2024-01-05',
                    'specialty': 'Cardiologia',
                    'admissionHistory': 'Paciente admitido com dor torácica...',
                    'problemsAndDiagnostics': 'Angina instável',
                    'examsList': 'ECG, Ecocardiograma',
                    'proceduresList': 'Cateterismo cardíaco',
                    'inpatientMedicalHistory': 'Evolução favorável...',
                    'patientDischargeStatus': 'Alta melhorada',
                    'dischargeRecommendations': 'Seguimento ambulatorial'
                },
                'datetime': 1704067200000,
                'patient': 'firebase-patient-key',
                'username': 'Dr. Test'
            },
            'report-key-2': {
                'content': {
                    'admissionDate': '2024-02-01',
                    'dischargeDate': '2024-02-10',
                    'specialty': 'Neurologia',
                    'admissionHistory': 'Paciente admitido com cefaleia...',
                    'problemsAndDiagnostics': 'Enxaqueca',
                    'examsList': 'Ressonância magnética',
                    'proceduresList': 'Tratamento medicamentoso',
                    'inpatientMedicalHistory': 'Evolução favorável...',
                    'patientDischargeStatus': 'Alta melhorada',
                    'dischargeRecommendations': 'Acompanhamento ambulatorial'
                },
                'datetime': 1706745600000,
                'patient': 'firebase-patient-key-2',
                'username': 'Dra. Test'
            }
        }

        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = firebase_data_multiple
        mock_db.reference.return_value = mock_ref

        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()

        # Capture command output
        out = StringIO()

        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('2 discharge reports', output)
        self.assertIn('DRY RUN', output)
