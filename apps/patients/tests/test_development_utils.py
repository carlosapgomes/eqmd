from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from datetime import timedelta
from io import StringIO

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class RefreshCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
    
    def test_refresh_patient_data_command(self):
        """Test the refresh patient data management command"""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            current_record_number='OLD_REC',  # Will be updated
            total_admissions_count=999,  # Will be corrected
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add correct source data
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number='CORRECT_REC',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timedelta(days=5),
            discharge_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Run refresh command
        out = StringIO()
        call_command('refresh_patient_data', stdout=out)
        
        # Check that data was corrected
        patient.refresh_from_db()
        self.assertEqual(patient.current_record_number, 'CORRECT_REC')
        self.assertEqual(patient.total_admissions_count, 1)
        self.assertEqual(patient.total_inpatient_days, 5)
        
        # Check command output
        output = out.getvalue()
        self.assertIn('Refreshed denormalized fields', output)
    
    def test_refresh_single_patient(self):
        """Test refreshing single patient data"""
        patient = Patient.objects.create(
            name='Single Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            current_record_number='WRONG',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add correct data
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number='CORRECT',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Run command for specific patient
        out = StringIO()
        call_command('refresh_patient_data', f'--patient-id={patient.pk}', stdout=out)
        
        # Check correction
        patient.refresh_from_db()
        self.assertEqual(patient.current_record_number, 'CORRECT')
        
        output = out.getvalue()
        self.assertIn('Refreshed denormalized fields for 1 patients', output)

class DataConsistencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
    
    def test_denormalized_field_refresh(self):
        """Test refreshing denormalized fields"""
        patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create record number
        record = PatientRecordNumber.objects.create(
            patient=patient,
            record_number='REC001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Manually set wrong denormalized data
        Patient.objects.filter(pk=patient.pk).update(
            current_record_number='WRONG'
        )
        
        # Refresh should fix it
        patient.refresh_from_db()
        patient.refresh_denormalized_fields()
        
        self.assertEqual(patient.current_record_number, 'REC001')
    
    def test_sample_data_generation(self):
        """Test that sample data command creates record tracking data"""
        out = StringIO()
        call_command('populate_sample_data', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('patient with record number and admission history', output)
        self.assertIn('DRY RUN COMPLETED', output)
    
    def test_data_migration_scenarios(self):
        """Test various data migration scenarios"""
        # Create patient without denormalized fields
        patient = Patient.objects.create(
            name='Migration Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            current_record_number=None,
            total_admissions_count=0,
            total_inpatient_days=0,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add historical data
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number='MIG001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add multiple admissions
        for i in range(3):
            admission_time = timezone.now() - timedelta(days=(i+1)*30)
            discharge_time = admission_time + timedelta(days=7)
            
            PatientAdmission.objects.create(
                patient=patient,
                admission_datetime=admission_time,
                discharge_datetime=discharge_time,
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                created_by=self.user,
                updated_by=self.user
            )
        
        # Migrate data
        patient.refresh_denormalized_fields()
        patient.refresh_from_db()
        
        # Verify migration
        self.assertEqual(patient.current_record_number, 'MIG001')
        self.assertEqual(patient.total_admissions_count, 3)
        self.assertEqual(patient.total_inpatient_days, 21)
    
    def test_edge_case_data_consistency(self):
        """Test edge cases for data consistency"""
        # Create patient with no record numbers
        patient1 = Patient.objects.create(
            name='No Record Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create patient with no admissions
        patient2 = Patient.objects.create(
            name='No Admission Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        PatientRecordNumber.objects.create(
            patient=patient2,
            record_number='REC002',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create patient with only active admission
        patient3 = Patient.objects.create(
            name='Active Only Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        PatientRecordNumber.objects.create(
            patient=patient3,
            record_number='REC003',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        admission = PatientAdmission.objects.create(
            patient=patient3,
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Refresh all patients
        for patient in [patient1, patient2, patient3]:
            patient.refresh_denormalized_fields()
            patient.refresh_from_db()
        
        # Verify consistency
        self.assertIsNone(patient1.current_record_number)
        self.assertEqual(patient1.total_admissions_count, 0)
        self.assertEqual(patient1.total_inpatient_days, 0)
        
        self.assertEqual(patient2.current_record_number, 'REC002')
        self.assertEqual(patient2.total_admissions_count, 0)
        self.assertEqual(patient2.total_inpatient_days, 0)
        
        self.assertEqual(patient3.current_record_number, 'REC003')
        self.assertEqual(patient3.total_admissions_count, 1)
        self.assertIsNone(patient3.total_inpatient_days)  # Active admission
    
    def test_command_error_handling(self):
        """Test command error handling"""
        # Test with invalid patient ID
        out = StringIO()
        call_command('refresh_patient_data', '--patient-id=99999', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Patient not found', output)
    
    def test_command_verbosity_levels(self):
        """Test command verbosity levels"""
        # Create test data
        patient = Patient.objects.create(
            name='Verbose Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number='VERBOSE001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test verbose output
        out = StringIO()
        call_command('refresh_patient_data', '--verbosity=2', stdout=out)
        
        output = out.getvalue()
        self.assertIn('VERBOSE001', output)
        self.assertIn('Refreshed denormalized fields', output)
    
    def test_command_dry_run_mode(self):
        """Test command dry run mode"""
        patient = Patient.objects.create(
            name='Dry Run Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            current_record_number='OLD',
            created_by=self.user,
            updated_by=self.user
        )
        
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number='NEW',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Run dry run
        out = StringIO()
        call_command('refresh_patient_data', '--dry-run', stdout=out)
        
        # Check that data was NOT actually updated
        patient.refresh_from_db()
        self.assertEqual(patient.current_record_number, 'OLD')
        
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
        self.assertIn('NEW', output)