from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.patients.models import Ward, Patient, PatientAdmission
from datetime import datetime
from django.utils import timezone

User = get_user_model()

class WardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        
    def test_ward_creation(self):
        """Test basic ward creation with required fields"""
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            description="Test description",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(ward.name, "Test Ward")
        self.assertEqual(ward.abbreviation, "TW")
        self.assertEqual(ward.description, "Test description")
        self.assertTrue(ward.is_active)
        self.assertEqual(ward.created_by, self.user)
        self.assertEqual(ward.updated_by, self.user)
        
    def test_ward_str_representation(self):
        """Test ward string representation"""
        ward = Ward.objects.create(
            name="Intensive Care Unit",
            abbreviation="ICU",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(str(ward), "ICU - Intensive Care Unit")
        
    def test_ward_unique_constraints(self):
        """Test that ward name and abbreviation must be unique"""
        Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Try to create another ward with same name
        with self.assertRaises(Exception):
            Ward.objects.create(
                name="Test Ward",
                abbreviation="TW2",
                created_by=self.user,
                updated_by=self.user,
            )
            
        # Try to create another ward with same abbreviation
        with self.assertRaises(Exception):
            Ward.objects.create(
                name="Another Ward",
                abbreviation="TW",
                created_by=self.user,
                updated_by=self.user,
            )
        
    def test_ward_patient_count_empty(self):
        """Test patient count for empty ward"""
        ward = Ward.objects.create(
            name="Empty Ward",
            abbreviation="EW",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(ward.get_current_patients_count(), 0)
        
    def test_ward_patient_count_with_inpatients(self):
        """Test patient count with inpatients"""
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create inpatients
        patient1 = Patient.objects.create(
            name="Test Patient 1",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        patient2 = Patient.objects.create(
            name="Test Patient 2",
            birthday="1985-05-15",
            status=Patient.Status.INPATIENT,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(ward.get_current_patients_count(), 2)
        
    def test_ward_patient_count_with_emergency_patients(self):
        """Test patient count includes emergency patients"""
        ward = Ward.objects.create(
            name="Emergency Ward",
            abbreviation="ER",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create emergency patient
        patient = Patient.objects.create(
            name="Emergency Patient",
            birthday="1995-03-20",
            status=Patient.Status.EMERGENCY,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(ward.get_current_patients_count(), 1)
        
    def test_ward_patient_count_excludes_non_inpatients(self):
        """Test patient count excludes outpatients, discharged, and transferred patients"""
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create patients with different statuses
        Patient.objects.create(
            name="Inpatient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        Patient.objects.create(
            name="Outpatient",
            birthday="1990-02-01",
            status=Patient.Status.OUTPATIENT,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        Patient.objects.create(
            name="Discharged Patient",
            birthday="1990-03-01",
            status=Patient.Status.DISCHARGED,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        Patient.objects.create(
            name="Transferred Patient",
            birthday="1990-04-01",
            status=Patient.Status.TRANSFERRED,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Only inpatient should be counted
        self.assertEqual(ward.get_current_patients_count(), 1)
        
    def test_ward_available_beds_list_empty(self):
        """Test available beds list for ward with no patients"""
        ward = Ward.objects.create(
            name="Empty Ward",
            abbreviation="EW",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(ward.get_available_beds_list(), [])
        
    def test_ward_available_beds_list_with_patients(self):
        """Test available beds list with patients in different beds"""
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create patients with bed assignments
        Patient.objects.create(
            name="Patient 1",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            bed="101",
            created_by=self.user,
            updated_by=self.user,
        )
        
        Patient.objects.create(
            name="Patient 2",
            birthday="1990-02-01",
            status=Patient.Status.EMERGENCY,
            ward=ward,
            bed="102",
            created_by=self.user,
            updated_by=self.user,
        )
        
        Patient.objects.create(
            name="Patient 3",
            birthday="1990-03-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            bed="101",  # Same bed as Patient 1
            created_by=self.user,
            updated_by=self.user,
        )
        
        beds_in_use = ward.get_available_beds_list()
        self.assertIn("101", beds_in_use)
        self.assertIn("102", beds_in_use)
        # Note: Current implementation returns all bed assignments, not unique beds
        # This behavior may be corrected in future phases
        self.assertEqual(len(beds_in_use), 3)  # All 3 bed assignments
        # Test unique beds using set
        unique_beds = set(beds_in_use)
        self.assertEqual(len(unique_beds), 2)  # Only 2 unique beds
        
    def test_ward_available_beds_excludes_empty_beds(self):
        """Test that empty bed strings are excluded from beds list"""
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create patient with assigned bed
        Patient.objects.create(
            name="Patient with bed",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            bed="101",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create patient without bed assignment
        Patient.objects.create(
            name="Patient without bed",
            birthday="1990-02-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            bed="",  # Empty bed
            created_by=self.user,
            updated_by=self.user,
        )
        
        beds_in_use = ward.get_available_beds_list()
        self.assertEqual(beds_in_use, ["101"])
        
    def test_ward_optional_fields(self):
        """Test ward creation with optional fields"""
        ward = Ward.objects.create(
            name="Complete Ward",
            abbreviation="CW",
            description="A ward with all fields",
            floor="3rd Floor",
            capacity_estimate=20,
            is_active=False,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(ward.floor, "3rd Floor")
        self.assertEqual(ward.capacity_estimate, 20)
        self.assertFalse(ward.is_active)
        
    def test_ward_ordering(self):
        """Test that wards are ordered by name"""
        Ward.objects.create(
            name="Zebra Ward",
            abbreviation="ZW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        Ward.objects.create(
            name="Alpha Ward",
            abbreviation="AW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        Ward.objects.create(
            name="Beta Ward",
            abbreviation="BW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        wards = list(Ward.objects.all())
        self.assertEqual(wards[0].name, "Alpha Ward")
        self.assertEqual(wards[1].name, "Beta Ward")
        self.assertEqual(wards[2].name, "Zebra Ward")


class WardPatientRelationshipTest(TestCase):
    """Test the relationship between Ward and Patient models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        
        self.ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
    def test_patient_ward_assignment(self):
        """Test assigning patient to ward"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(patient.ward, self.ward)
        self.assertIn(patient, self.ward.patients.all())
        
    def test_patient_ward_null_allowed(self):
        """Test that patient can exist without ward assignment"""
        patient = Patient.objects.create(
            name="No Ward Patient",
            birthday="1990-01-01",
            ward=None,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertIsNone(patient.ward)
        
    def test_ward_deletion_sets_patient_ward_to_null(self):
        """Test that deleting ward sets patient.ward to NULL"""
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        ward_id = self.ward.id
        self.ward.delete()
        
        patient.refresh_from_db()
        self.assertIsNone(patient.ward)


class WardAdmissionRelationshipTest(TestCase):
    """Test the relationship between Ward and PatientAdmission models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        
        self.ward = Ward.objects.create(
            name="ICU",
            abbreviation="ICU",
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            created_by=self.user,
            updated_by=self.user,
        )
        
    def test_admission_ward_assignment(self):
        """Test assigning admission to ward"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(admission.ward, self.ward)
        self.assertIn(admission, self.ward.admissions.all())
        
    def test_admission_ward_null_allowed(self):
        """Test that admission can exist without ward assignment"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=None,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertIsNone(admission.ward)
        
    def test_ward_deletion_sets_admission_ward_to_null(self):
        """Test that deleting ward sets admission.ward to NULL"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.ward.delete()
        
        admission.refresh_from_db()
        self.assertIsNone(admission.ward)