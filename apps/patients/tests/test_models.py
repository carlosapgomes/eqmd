from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient

User = get_user_model()

class PatientModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test patients with different statuses
        cls.inpatient = Patient.objects.create(
            name='John Doe',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.outpatient = Patient.objects.create(
            name='Jane Smith',
            birthday='1985-05-15',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.emergency_patient = Patient.objects.create(
            name='Bob Johnson',
            birthday='1978-12-03',
            status=Patient.Status.EMERGENCY,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.discharged_patient = Patient.objects.create(
            name='Alice Brown',
            birthday='1992-08-20',
            status=Patient.Status.DISCHARGED,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_creation_inpatient(self):
        """Test that an inpatient can be created with required fields"""
        self.assertEqual(self.inpatient.name, 'John Doe')
        self.assertEqual(self.inpatient.status, Patient.Status.INPATIENT)
        self.assertEqual(str(self.inpatient), 'John Doe')

    def test_patient_creation_outpatient(self):
        """Test that an outpatient can be created with required fields"""
        self.assertEqual(self.outpatient.name, 'Jane Smith')
        self.assertEqual(self.outpatient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(str(self.outpatient), 'Jane Smith')

    def test_patient_creation_emergency(self):
        """Test that an emergency patient can be created with required fields"""
        self.assertEqual(self.emergency_patient.name, 'Bob Johnson')
        self.assertEqual(self.emergency_patient.status, Patient.Status.EMERGENCY)
        self.assertEqual(str(self.emergency_patient), 'Bob Johnson')

    def test_patient_creation_discharged(self):
        """Test that a discharged patient can be created with required fields"""
        self.assertEqual(self.discharged_patient.name, 'Alice Brown')
        self.assertEqual(self.discharged_patient.status, Patient.Status.DISCHARGED)
        self.assertEqual(str(self.discharged_patient), 'Alice Brown')

    def test_patient_status_choices(self):
        """Test that all patient status choices are available"""
        # Test that status choices exist
        status_choices = [choice[0] for choice in Patient.Status.choices]
        
        self.assertIn(Patient.Status.INPATIENT, status_choices)
        self.assertIn(Patient.Status.OUTPATIENT, status_choices)
        self.assertIn(Patient.Status.EMERGENCY, status_choices)
        self.assertIn(Patient.Status.DISCHARGED, status_choices)
        self.assertIn(Patient.Status.TRANSFERRED, status_choices)

    def test_patient_name_property(self):
        """Test patient name property"""
        # Test name property
        self.assertEqual(self.inpatient.name, 'John Doe')
        
    def test_patient_string_representation(self):
        """Test patient string representation"""
        self.assertEqual(str(self.inpatient), 'John Doe')
        self.assertEqual(str(self.outpatient), 'Jane Smith')
        self.assertEqual(str(self.emergency_patient), 'Bob Johnson')
        self.assertEqual(str(self.discharged_patient), 'Alice Brown')

    def test_patient_meta_options(self):
        """Test patient model meta options"""
        # Test ordering if defined
        if hasattr(Patient._meta, 'ordering'):
            # Just check that ordering is defined, don't assume specific order
            self.assertIsInstance(Patient._meta.ordering, (list, tuple))

    def test_patient_required_fields(self):
        """Test patient required fields validation"""
        # Test that required fields are properly defined
        patient_fields = [field.name for field in Patient._meta.get_fields()]
        
        self.assertIn('name', patient_fields)
        self.assertIn('birthday', patient_fields)
        self.assertIn('status', patient_fields)
        self.assertIn('created_by', patient_fields)
        self.assertIn('updated_by', patient_fields)

    def test_patient_status_change(self):
        """Test patient status can be changed"""
        # Change status and save
        original_status = self.outpatient.status
        new_status = Patient.Status.INPATIENT
        
        self.outpatient.status = new_status
        self.outpatient.save()
        
        # Refresh from database
        self.outpatient.refresh_from_db()
        self.assertEqual(self.outpatient.status, new_status)
        self.assertNotEqual(self.outpatient.status, original_status)

    def test_patient_timestamps(self):
        """Test patient creation and update timestamps"""
        # Test that timestamps are set
        self.assertIsNotNone(self.inpatient.created_at)
        self.assertIsNotNone(self.inpatient.updated_at)
        
        # Test that created_by and updated_by are set
        self.assertEqual(self.inpatient.created_by, self.user)
        self.assertEqual(self.inpatient.updated_by, self.user)

    def test_patient_simplified_model_structure(self):
        """Test that the simplified patient model structure works correctly"""
        # Test that we can create patients without hospital assignments
        simple_patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(simple_patient.name, 'Test Patient')
        self.assertEqual(simple_patient.status, Patient.Status.OUTPATIENT)
        
        # Test that all statuses work without hospital requirements
        for i, status in enumerate([Patient.Status.INPATIENT, Patient.Status.OUTPATIENT, 
                      Patient.Status.EMERGENCY, Patient.Status.DISCHARGED, 
                      Patient.Status.TRANSFERRED]):
            test_patient = Patient.objects.create(
                name=f'Status Test {i}',
                birthday='1990-01-01',
                status=status,
                created_by=self.user,
                updated_by=self.user
            )
            self.assertEqual(test_patient.status, status)

    def test_patient_model_no_hospital_references(self):
        """Test that patient model has no hospital field references"""
        # Verify that hospital-related fields are not present
        patient_field_names = [field.name for field in Patient._meta.get_fields()]
        
        # These fields should not exist in the simplified model
        hospital_fields = ['current_hospital', 'hospital', 'hospital_records']
        
        for field_name in hospital_fields:
            self.assertNotIn(field_name, patient_field_names, 
                           f"Hospital field '{field_name}' should not exist in simplified model")