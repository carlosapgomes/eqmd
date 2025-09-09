# Phase 7 Prompt: Testing & Documentation

````
Create comprehensive tests and complete documentation for discharge reports feature.

CONTEXT:
- All previous phases completed: Full discharge reports functionality
- Need comprehensive test coverage for models, views, permissions, Firebase import
- Need to complete feature documentation
- Project uses pytest and Django test runner

GOAL: Complete test suite and comprehensive documentation.

TASKS:

1. CREATE TEST DIRECTORY STRUCTURE:
```bash
mkdir -p apps/dischargereports/tests
touch apps/dischargereports/tests/__init__.py
````

2. CREATE MODEL TESTS:
   apps/dischargereports/tests/test_models.py:

```python
from datetime import date, datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.events.models import Event
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

    def test_save_sets_event_type(self):
        """Test that save() sets correct event type"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            admission_history='Test history',
            problems_and_diagnosis='Test diagnosis',
            exams_list='Test exams',
            procedures_list='Test procedures',
            inpatient_medical_history='Test medical history',
            discharge_status='Test status',
            discharge_recommendations='Test recommendations',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(report.event_type, Event.DISCHARGE_REPORT_EVENT)

    def test_is_draft_default_true(self):
        """Test that is_draft defaults to True"""
        report = DischargeReport(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.is_draft)

    def test_string_representation(self):
        """Test __str__ method"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        expected = f"Relatório de Alta - {self.patient.name} - 01/01/2024 (Rascunho)"
        self.assertEqual(str(report), expected)

    def test_can_be_edited_by_user_draft(self):
        """Test that drafts can be edited by creator"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.can_be_edited_by_user(self.user))

    def test_can_be_deleted_by_user_draft_only(self):
        """Test that only drafts can be deleted"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Draft report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )

        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertTrue(draft_report.can_be_deleted_by_user(self.user))
        self.assertFalse(final_report.can_be_deleted_by_user(self.user))

    def test_status_display_properties(self):
        """Test status display properties"""
        draft_report = DischargeReport(is_draft=True)
        final_report = DischargeReport(is_draft=False)

        self.assertEqual(draft_report.status_display, "Rascunho")
        self.assertEqual(final_report.status_display, "Finalizado")

        self.assertEqual(draft_report.status_badge_class, "badge bg-warning text-dark")
        self.assertEqual(final_report.status_badge_class, "badge bg-success")
```

3. CREATE VIEW TESTS:
   apps/dischargereports/tests/test_views.py:

```python
from datetime import date, datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

    def test_create_view_requires_login(self):
        """Test that create view requires authentication"""
        url = reverse('apps.dischargereports:dischargereport_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_view_saves_draft_by_default(self):
        """Test that create view saves as draft by default"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')

        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_draft': 'Save Draft'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after save

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)

    def test_create_view_saves_final(self):
        """Test that create view can save as final"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')

        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_final': 'Save Final'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertFalse(report.is_draft)

    def test_update_view_blocks_non_editable(self):
        """Test that update view blocks non-editable reports"""
        # Create final report older than 24 hours
        old_datetime = datetime.now() - timedelta(hours=25)
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description='Old final report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        # Manually set created_at to simulate old report
        DischargeReport.objects.filter(pk=report.pk).update(created_at=old_datetime)

        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_delete_view_allows_drafts_only(self):
        """Test that delete view only allows draft deletion"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Draft report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )

        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )

        self.client.login(username='testuser', password='testpass123')

        # Draft can be deleted
        draft_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': draft_report.pk})
        response = self.client.get(draft_url)
        self.assertEqual(response.status_code, 200)

        # Final report cannot be deleted
        final_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': final_report.pk})
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 403)
```

4. CREATE FIREBASE IMPORT TESTS:
   apps/dischargereports/tests/test_firebase_import.py:

```python
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class FirebaseImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
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

        # Mock file operations
        with patch('builtins.open', mock_open(read_data='{"test": "data"}')):
            with patch('os.path.exists', return_value=True):
                with patch('json.load', return_value={"test": "data"}):
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
```

5. CREATE INTEGRATION TESTS:
   apps/dischargereports/tests/test_integration.py:

```python
from datetime import date, datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportIntegrationTests(TestCase):
    """Test complete workflows"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Integration Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )

    def test_complete_draft_to_final_workflow(self):
        """Test creating draft, editing, and finalizing"""
        self.client.login(username='testuser', password='testpass123')

        # Create draft
        create_url = reverse('apps.dischargereports:dischargereport_create')
        create_data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test workflow report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Integration Test',
            'admission_history': 'Initial history',
            'problems_and_diagnosis': 'Initial diagnosis',
            'exams_list': 'Initial exams',
            'procedures_list': 'Initial procedures',
            'inpatient_medical_history': 'Initial medical history',
            'discharge_status': 'Initial status',
            'discharge_recommendations': 'Initial recommendations',
            'save_draft': 'Save Draft'
        }

        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)

        # Edit draft
        update_url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        update_data = create_data.copy()
        update_data.update({
            'problems_and_diagnosis': 'Updated diagnosis',
            'save_final': 'Save Final'  # Finalize this time
        })

        response = self.client.post(update_url, update_data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertFalse(report.is_draft)
        self.assertEqual(report.problems_and_diagnosis, 'Updated diagnosis')

        # Verify can't delete finalized report
        delete_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': report.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)
```

6. COMPLETE FEATURE DOCUMENTATION:
   Create comprehensive docs/apps/dischargereports.md using the template from docs-template.md, including:

- All testing commands
- Troubleshooting section
- Development notes
- Firebase import documentation

7. CREATE TEST RUNNER SCRIPT:

```bash
# Add to documentation - testing commands
# All tests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ -v

# Specific test files
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_models.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_views.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_firebase_import.py -v

# With coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ --cov=apps.dischargereports --cov-report=term-missing -v
```

VERIFICATION:

- All tests pass
- Good test coverage (>80%)
- Integration tests cover complete workflows
- Firebase import tests work with mocking
- Documentation is comprehensive and accurate

DELIVERABLES:

- Comprehensive test suite
- Feature documentation in docs/apps/dischargereports.md
- Testing command documentation
- Integration test coverage
