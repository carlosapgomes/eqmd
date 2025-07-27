from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Ward, Patient, PatientAdmission
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class WardPatientModelIntegrationTest(TestCase):
    """Test integration between Ward and Patient models only (no views/forms)"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123",
            profession_type=0
        )
        
        self.ward = Ward.objects.create(
            name="Integration Test Ward",
            abbreviation="ITW",
            description="Ward for integration testing",
            floor="2nd Floor",
            capacity_estimate=10,
            created_by=self.user,
            updated_by=self.user,
        )
        
    def test_patient_ward_assignment_model_level(self):
        """Test patient ward assignment at model level"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=self.ward,
            bed="101",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Verify patient was created with ward
        self.assertEqual(patient.ward, self.ward)
        self.assertEqual(patient.bed, "101")
        
        # Verify ward shows the patient
        self.assertEqual(self.ward.get_current_patients_count(), 1)
        self.assertIn("101", self.ward.get_available_beds_list())
        
    def test_patient_ward_update_model_level(self):
        """Test updating patient ward assignment at model level"""
        # Create patient
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create another ward
        new_ward = Ward.objects.create(
            name="New Ward",
            abbreviation="NW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Update patient ward
        patient.ward = new_ward
        patient.bed = "202"
        patient.save()
        
        # Verify patient ward was updated
        self.assertEqual(patient.ward, new_ward)
        self.assertEqual(patient.bed, "202")
        
        # Verify ward counts
        self.assertEqual(self.ward.get_current_patients_count(), 0)  # Original ward
        self.assertEqual(new_ward.get_current_patients_count(), 1)  # New ward
        
    def test_ward_patient_status_filtering(self):
        """Test ward correctly filters patients by status"""
        # Create patients with different statuses
        inpatient = Patient.objects.create(
            name="Inpatient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=self.ward,
            bed="101",
            created_by=self.user,
            updated_by=self.user,
        )
        
        emergency_patient = Patient.objects.create(
            name="Emergency Patient",
            birthday="1990-02-01",
            status=Patient.Status.EMERGENCY,
            ward=self.ward,
            bed="102",
            created_by=self.user,
            updated_by=self.user,
        )
        
        outpatient = Patient.objects.create(
            name="Outpatient",
            birthday="1990-03-01",
            status=Patient.Status.OUTPATIENT,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        discharged_patient = Patient.objects.create(
            name="Discharged Patient",
            birthday="1990-04-01",
            status=Patient.Status.DISCHARGED,
            ward=self.ward,
            bed="103",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Ward should only count inpatient and emergency patients
        current_patients = self.ward.patients.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
        )
        
        self.assertEqual(current_patients.count(), 2)
        self.assertIn(inpatient, current_patients)
        self.assertIn(emergency_patient, current_patients)
        
        # Ward patient count method should return 2
        self.assertEqual(self.ward.get_current_patients_count(), 2)


class WardAdmissionModelIntegrationTest(TestCase):
    """Test integration between Ward and PatientAdmission models only (no views/forms)"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123"
        )
        
        self.ward = Ward.objects.create(
            name="Admission Test Ward",
            abbreviation="ATW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        
    def test_admission_ward_assignment_model_level(self):
        """Test patient admission with ward assignment at model level"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            initial_bed="101",
            admission_diagnosis="Emergency admission",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Verify admission was created with ward
        self.assertEqual(admission.ward, self.ward)
        self.assertEqual(admission.initial_bed, "101")
        
        # Verify ward relationship
        self.assertIn(admission, self.ward.admissions.all())
        
    def test_admission_ward_synchronization(self):
        """Test that patient ward can be synchronized with admission ward"""
        # Create admission
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            ward=self.ward,
            initial_bed="102",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Update patient to match admission
        self.patient.status = Patient.Status.INPATIENT
        self.patient.ward = admission.ward
        self.patient.bed = admission.initial_bed
        self.patient.save()
        
        # Verify synchronization
        self.assertEqual(self.patient.ward, admission.ward)
        self.assertEqual(self.patient.bed, admission.initial_bed)
        self.assertEqual(self.ward.get_current_patients_count(), 1)


class WardDeletionModelIntegrationTest(TestCase):
    """Test ward deletion and its effects on related data"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        
        self.ward = Ward.objects.create(
            name="Deletion Test Ward",
            abbreviation="DTW",
            created_by=self.user,
            updated_by=self.user,
        )
        
    def test_ward_deletion_nullifies_patient_ward(self):
        """Test that deleting ward sets patient.ward to NULL"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Delete ward
        self.ward.delete()
        
        # Verify patient.ward is now NULL
        patient.refresh_from_db()
        self.assertIsNone(patient.ward)
        
    def test_ward_deletion_nullifies_admission_ward(self):
        """Test that deleting ward sets admission.ward to NULL"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            created_by=self.user,
            updated_by=self.user,
        )
        
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Delete ward
        self.ward.delete()
        
        # Verify admission.ward is now NULL
        admission.refresh_from_db()
        self.assertIsNone(admission.ward)
        
    def test_ward_deletion_preserves_patients_and_admissions(self):
        """Test that deleting ward doesn't delete patients or admissions"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Store IDs before deletion
        patient_id = patient.id
        admission_id = admission.id
        
        # Delete ward
        self.ward.delete()
        
        # Verify patient and admission still exist
        self.assertTrue(Patient.objects.filter(id=patient_id).exists())
        self.assertTrue(PatientAdmission.objects.filter(id=admission_id).exists())


# NOTE: View-based and form-based integration tests are placeholders for future phases
class WardIntegrationPlaceholderTest(TestCase):
    """Placeholder for view and form integration tests that will be implemented in later phases"""
    
    def test_placeholder(self):
        """Placeholder test to prevent empty test suite"""
        self.assertTrue(True)
        
    # TODO: Implement these integration tests when views and forms are created:
    # Phase 3: test_patient_creation_with_ward_form_submission
    # Phase 3: test_admission_form_with_ward_selection
    # Phase 3: test_ward_detail_view_shows_current_patients
    # Phase 5: test_complete_ward_patient_workflow_through_views