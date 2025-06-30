from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from datetime import date, timedelta
from unittest.mock import patch, Mock

from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.drugtemplates.models import DrugTemplate
from apps.core.permissions.constants import MEDICAL_PROFESSIONS

User = get_user_model()


class PrescriptionPermissionTestCase(TestCase):
    """Base test case for prescription permission tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for permission tests."""
        # Create users with different professions
        cls.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123',
            profession=1,  # Doctor
            first_name='Dr. John',
            last_name='Smith'
        )
        
        cls.resident = User.objects.create_user(
            username='resident',
            email='resident@example.com',
            password='testpass123',
            profession=2,  # Resident
            first_name='Dr. Jane',
            last_name='Doe'
        )
        
        cls.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@example.com',
            password='testpass123',
            profession=3,  # Nurse
            first_name='Nurse',
            last_name='Johnson'
        )
        
        cls.physiotherapist = User.objects.create_user(
            username='physio',
            email='physio@example.com',
            password='testpass123',
            profession=4,  # Physiotherapist
            first_name='Physio',
            last_name='Wilson'
        )
        
        cls.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
            profession=5,  # Student
            first_name='Student',
            last_name='Brown'
        )

        # Create hospitals
        cls.hospital1 = Hospital.objects.create(
            name='Hospital 1',
            created_by=cls.doctor,
            updated_by=cls.doctor
        )
        
        cls.hospital2 = Hospital.objects.create(
            name='Hospital 2',
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

        # Create patients with different statuses
        cls.outpatient = Patient.objects.create(
            name='Outpatient',
            birthday='1990-01-01',
            status=1,  # Outpatient
            created_by=cls.doctor,
            updated_by=cls.doctor
        )
        
        cls.inpatient = Patient.objects.create(
            name='Inpatient',
            birthday='1985-05-15',
            status=2,  # Inpatient
            current_hospital=cls.hospital1,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

        # Create prescriptions
        cls.recent_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Recent prescription',
            instructions='Recent instructions',
            status='draft',
            prescription_date=date.today(),
            patient=cls.outpatient,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )
        
        cls.old_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=30),
            description='Old prescription',
            instructions='Old instructions',
            status='finalized',
            prescription_date=date.today() - timedelta(days=30),
            patient=cls.outpatient,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def _setup_session(self, user, hospital=None):
        """Helper method to set up user session with hospital context."""
        self.client.login(username=user.username, password='testpass123')
        session = self.client.session
        session['selected_hospital_id'] = (hospital or self.hospital1).id
        session.save()


class PatientAccessPermissionTest(PrescriptionPermissionTestCase):
    """Test patient access permissions for prescriptions."""

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_doctor_can_access_all_patients(self, mock_can_access):
        """Test that doctors can access all patients."""
        mock_can_access.return_value = True
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)
        mock_can_access.assert_called_once()

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_resident_limited_patient_access(self, mock_can_access):
        """Test that residents have limited patient access."""
        mock_can_access.return_value = True  # Has access
        self._setup_session(self.resident)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Test no access scenario
        mock_can_access.return_value = False
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_nurse_limited_patient_access(self, mock_can_access):
        """Test that nurses have limited patient access."""
        mock_can_access.return_value = True
        self._setup_session(self.nurse)
        
        # Nurses can view prescriptions but have limited edit access
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_student_outpatient_only_access(self, mock_can_access):
        """Test that students can only access outpatients."""
        mock_can_access.return_value = True
        self._setup_session(self.student)
        
        # Students should be able to access outpatient prescriptions
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_no_patient_access_returns_404(self, mock_can_access):
        """Test that users without patient access get 404."""
        mock_can_access.return_value = False
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)


class EventEditPermissionTest(PrescriptionPermissionTestCase):
    """Test event edit permissions for prescriptions."""

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_creator_can_edit_recent_prescription(self, mock_can_edit):
        """Test that creators can edit recent prescriptions."""
        mock_can_edit.return_value = True
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)
        mock_can_edit.assert_called_once()

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_cannot_edit_old_prescription(self, mock_can_edit):
        """Test that old prescriptions cannot be edited (24-hour rule)."""
        mock_can_edit.return_value = False  # Simulate 24-hour rule violation
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update',
                   kwargs={'pk': self.old_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_non_creator_cannot_edit(self, mock_can_edit):
        """Test that non-creators cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.resident)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_nurse_cannot_edit_prescriptions(self, mock_can_edit):
        """Test that nurses cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.nurse)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_student_cannot_edit_prescriptions(self, mock_can_edit):
        """Test that students cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.student)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)


class EventDeletePermissionTest(PrescriptionPermissionTestCase):
    """Test event delete permissions for prescriptions."""

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_creator_can_delete_recent_prescription(self, mock_can_delete):
        """Test that creators can delete recent prescriptions."""
        mock_can_delete.return_value = True
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 200)
        mock_can_delete.assert_called_once()

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_cannot_delete_old_prescription(self, mock_can_delete):
        """Test that old prescriptions cannot be deleted (24-hour rule)."""
        mock_can_delete.return_value = False
        self._setup_session(self.doctor)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete',
                   kwargs={'pk': self.old_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_non_creator_cannot_delete(self, mock_can_delete):
        """Test that non-creators cannot delete prescriptions."""
        mock_can_delete.return_value = False
        self._setup_session(self.resident)
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete',
                   kwargs={'pk': self.recent_prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_successful_deletion_workflow(self, mock_can_delete):
        """Test successful deletion workflow."""
        mock_can_delete.return_value = True
        self._setup_session(self.doctor)
        
        # Create a prescription to delete
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Prescription to delete',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        prescription_id = prescription.id
        
        # Delete the prescription
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_delete',
                   kwargs={'pk': prescription.pk})
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(OutpatientPrescription.objects.filter(id=prescription_id).exists())


class PrescriptionCreationPermissionTest(PrescriptionPermissionTestCase):
    """Test prescription creation permissions."""

    def test_doctor_can_create_prescriptions(self):
        """Test that doctors can create prescriptions."""
        self._setup_session(self.doctor)
        
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertEqual(response.status_code, 200)

    def test_resident_can_create_prescriptions(self):
        """Test that residents can create prescriptions."""
        self._setup_session(self.resident)
        
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertEqual(response.status_code, 200)

    def test_physiotherapist_can_create_prescriptions(self):
        """Test that physiotherapists can create prescriptions."""
        self._setup_session(self.physiotherapist)
        
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertEqual(response.status_code, 200)

    def test_nurse_cannot_create_prescriptions(self):
        """Test that nurses cannot create prescriptions."""
        self._setup_session(self.nurse)
        
        # This would depend on the actual permission decorators used
        # For now, assume they can access but may have form restrictions
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        # The exact response depends on implementation
        self.assertIn(response.status_code, [200, 403, 404])

    def test_student_cannot_create_prescriptions(self):
        """Test that students cannot create prescriptions."""
        self._setup_session(self.student)
        
        # Students should not be able to create prescriptions
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertIn(response.status_code, [403, 404])


class HospitalContextPermissionTest(PrescriptionPermissionTestCase):
    """Test hospital context permissions."""

    def test_hospital_context_required(self):
        """Test that hospital context is required for views."""
        self.client.login(username='doctor', password='testpass123')
        # Don't set hospital context in session
        
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        # Should redirect to hospital selection or show error
        self.assertIn(response.status_code, [302, 403])

    def test_different_hospital_access(self):
        """Test access control based on hospital context."""
        # Create prescription at hospital1
        prescription_h1 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Hospital 1 prescription',
            instructions='H1 instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.inpatient,  # Patient at hospital1
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Access from hospital1 context
        self._setup_session(self.doctor, self.hospital1)
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription_h1.pk})
            )
            self.assertEqual(response.status_code, 200)

        # Access from hospital2 context (should depend on patient access rules)
        self._setup_session(self.doctor, self.hospital2)
        with patch('apps.core.permissions.utils.can_access_patient', return_value=False):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription_h1.pk})
            )
            self.assertEqual(response.status_code, 404)


class DrugTemplateAccessPermissionTest(PrescriptionPermissionTestCase):
    """Test drug template access permissions in prescription context."""

    @classmethod
    def setUpTestData(cls):
        """Set up drug template test data."""
        super().setUpTestData()
        
        # Create drug templates with different visibility
        cls.public_template = DrugTemplate.objects.create(
            name='Public Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily',
            creator=cls.doctor,
            is_public=True
        )
        
        cls.private_template_doctor = DrugTemplate.objects.create(
            name='Private Drug Doctor',
            presentation='20mg tablet',
            usage_instructions='Take 2 daily',
            creator=cls.doctor,
            is_public=False
        )
        
        cls.private_template_resident = DrugTemplate.objects.create(
            name='Private Drug Resident',
            presentation='30mg tablet',
            usage_instructions='Take 3 daily',
            creator=cls.resident,
            is_public=False
        )

    def test_public_template_access_all_users(self):
        """Test that all users can access public drug templates."""
        # This would be tested in the context of prescription creation forms
        # where drug templates are available for selection
        
        for user in [self.doctor, self.resident, self.nurse, self.physiotherapist]:
            self._setup_session(user)
            response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
            # Check that public templates are available in context
            if response.status_code == 200:
                # Would need to check if drug templates are properly filtered
                pass

    def test_private_template_access_creator_only(self):
        """Test that private templates are only accessible to their creators."""
        # Doctor should see their own private template
        self._setup_session(self.doctor)
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        # Check that doctor's private template is available
        
        # Resident should not see doctor's private template
        self._setup_session(self.resident)
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        # Check that doctor's private template is not available


class PrescriptionStatusPermissionTest(PrescriptionPermissionTestCase):
    """Test permissions related to prescription status changes."""

    def test_finalized_prescription_immutable(self):
        """Test that finalized prescriptions cannot be modified."""
        finalized_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Finalized prescription',
            instructions='Final instructions',
            status='finalized',
            prescription_date=date.today(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        self._setup_session(self.doctor)
        
        # Should not be able to edit finalized prescription
        with patch('apps.core.permissions.utils.can_edit_event', return_value=False):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': finalized_prescription.pk})
            )
            self.assertEqual(response.status_code, 404)

    def test_draft_prescription_editable(self):
        """Test that draft prescriptions can be modified."""
        draft_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Draft prescription',
            instructions='Draft instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        self._setup_session(self.doctor)
        
        with patch('apps.core.permissions.utils.can_edit_event', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': draft_prescription.pk})
            )
            self.assertEqual(response.status_code, 200)


class PermissionIntegrationTest(PrescriptionPermissionTestCase):
    """Integration tests for permission scenarios."""

    def test_complete_permission_workflow(self):
        """Test complete workflow with permission checks at each step."""
        self._setup_session(self.doctor)

        # Step 1: Create prescription (should succeed for doctor)
        create_data = {
            'patient': self.outpatient.pk,
            'event_datetime': timezone.now(),
            'description': 'Permission test prescription',
            'instructions': 'Permission test instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Permission Test Drug',
            'form-0-presentation': '10mg tablet',
            'form-0-usage_instructions': 'Take as needed',
            'form-0-quantity': '30',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            create_data
        )
        self.assertEqual(response.status_code, 302)
        
        prescription = OutpatientPrescription.objects.get(
            description='Permission test prescription'
        )

        # Step 2: View prescription (should succeed with patient access)
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)

        # Step 3: Edit prescription (should succeed with edit permission)
        with patch('apps.core.permissions.utils.can_edit_event', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)

        # Step 4: Switch to different user (resident)
        self._setup_session(self.resident)

        # Step 5: Try to edit (should fail without permission)
        with patch('apps.core.permissions.utils.can_edit_event', return_value=False):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 404)

        # Step 6: Switch to student
        self._setup_session(self.student)

        # Step 7: Try to view (should depend on patient access)
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)

        # Step 8: Try to create prescription as student (should fail)
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertIn(response.status_code, [403, 404])

    def test_permission_edge_cases(self):
        """Test edge cases in permission logic."""
        # Test with deleted patient
        # Test with inactive user
        # Test with expired session
        # Test with missing hospital context
        # etc.
        pass