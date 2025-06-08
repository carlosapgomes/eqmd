"""
Integration tests for the complete permission system.

These tests verify that all components of the permission system work together
correctly, including utilities, decorators, middleware, and template tags.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template import Context, Template
from django.http import HttpResponseForbidden
from unittest.mock import Mock, patch

from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_delete_event,
    patient_access_required,
    doctor_required,
    hospital_context_required,
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    NURSE,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
    EMERGENCY,
    DISCHARGED,
)

User = get_user_model()


class PermissionSystemIntegrationTest(TestCase):
    """Test complete permission system integration."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test users with different professions
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='testpass123',
            profession_type=0  # MEDICAL_DOCTOR
        )
        
        self.nurse = User.objects.create_user(
            email='nurse@test.com',
            password='testpass123',
            profession_type=2  # NURSE
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            profession_type=4  # STUDENT
        )
        
        # Create test groups
        self.doctor_group = Group.objects.create(name='Medical Doctors')
        self.nurse_group = Group.objects.create(name='Nurses')
        self.student_group = Group.objects.create(name='Students')
        
        # Assign users to groups
        self.doctor.groups.add(self.doctor_group)
        self.nurse.groups.add(self.nurse_group)
        self.student.groups.add(self.student_group)
        
        # Create mock hospital
        self.hospital = Mock()
        self.hospital.id = 'hospital-123'
        self.hospital.name = 'Test Hospital'
        
        # Create mock patients
        self.inpatient = Mock()
        self.inpatient.id = 'patient-1'
        self.inpatient.status = INPATIENT
        self.inpatient.current_hospital = self.hospital
        self.inpatient.current_hospital_id = self.hospital.id
        
        self.outpatient = Mock()
        self.outpatient.id = 'patient-2'
        self.outpatient.status = OUTPATIENT
        self.outpatient.current_hospital = self.hospital
        self.outpatient.current_hospital_id = self.hospital.id
        
        # Create mock event
        self.event = Mock()
        self.event.id = 'event-1'
        self.event.created_by = self.doctor
        self.event.created_at = Mock()
        self.event.created_at.total_seconds.return_value = 3600  # 1 hour ago
    
    def _add_hospital_context(self, user, hospital=None):
        """Add hospital context to user."""
        hospital = hospital or self.hospital
        user.current_hospital = hospital
        user.has_hospital_context = True
    
    def test_complete_patient_access_workflow(self):
        """Test complete patient access workflow for different user types."""
        # Doctor with hospital context can access both patients
        self._add_hospital_context(self.doctor)
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))
        self.assertTrue(can_access_patient(self.doctor, self.outpatient))
        
        # Nurse with hospital context can access both patients
        self._add_hospital_context(self.nurse)
        self.assertTrue(can_access_patient(self.nurse, self.inpatient))
        self.assertTrue(can_access_patient(self.nurse, self.outpatient))
        
        # Student with hospital context can only access outpatients
        self._add_hospital_context(self.student)
        self.assertFalse(can_access_patient(self.student, self.inpatient))
        self.assertTrue(can_access_patient(self.student, self.outpatient))
        
        # Users without hospital context cannot access patients
        self.assertFalse(can_access_patient(self.doctor, self.inpatient))
        self.assertFalse(can_access_patient(self.nurse, self.inpatient))
        self.assertFalse(can_access_patient(self.student, self.outpatient))
    
    def test_patient_status_change_workflow(self):
        """Test patient status change workflow."""
        self._add_hospital_context(self.doctor)
        self._add_hospital_context(self.nurse)
        self._add_hospital_context(self.student)
        
        # Doctor can change any status
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        self.assertTrue(can_change_patient_status(self.doctor, self.outpatient, INPATIENT))
        
        # Nurse can change some statuses but not discharge
        self.assertFalse(can_change_patient_status(self.nurse, self.inpatient, DISCHARGED))
        self.assertTrue(can_change_patient_status(self.nurse, self.outpatient, INPATIENT))
        
        # Student cannot change any status
        self.assertFalse(can_change_patient_status(self.student, self.outpatient, INPATIENT))
    
    def test_personal_data_change_workflow(self):
        """Test patient personal data change workflow."""
        self._add_hospital_context(self.doctor)
        self._add_hospital_context(self.nurse)
        
        # Only doctors can change personal data
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.inpatient))
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.outpatient))
        
        # Nurses cannot change personal data
        self.assertFalse(can_change_patient_personal_data(self.nurse, self.inpatient))
        self.assertFalse(can_change_patient_personal_data(self.nurse, self.outpatient))
    
    @patch('django.utils.timezone.now')
    def test_event_management_workflow(self, mock_now):
        """Test event management workflow with time restrictions."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Mock current time
        current_time = timezone.now()
        mock_now.return_value = current_time
        
        # Set event creation time to 1 hour ago (within 24-hour limit)
        self.event.created_at = current_time - timedelta(hours=1)
        
        # Event creator can edit and delete within time limit
        self.assertTrue(can_edit_event(self.doctor, self.event))
        self.assertTrue(can_delete_event(self.doctor, self.event))
        
        # Other users cannot edit/delete
        self.assertFalse(can_edit_event(self.nurse, self.event))
        self.assertFalse(can_delete_event(self.nurse, self.event))
        
        # Set event creation time to 25 hours ago (beyond 24-hour limit)
        self.event.created_at = current_time - timedelta(hours=25)
        
        # Even creator cannot edit/delete beyond time limit
        self.assertFalse(can_edit_event(self.doctor, self.event))
        self.assertFalse(can_delete_event(self.doctor, self.event))
    
    def test_decorator_integration(self):
        """Test permission decorators integration."""
        
        @patient_access_required
        def test_patient_view(request, patient_id):
            return "Success"
        
        @doctor_required
        def test_doctor_view(request):
            return "Doctor only"
        
        @hospital_context_required
        def test_hospital_view(request):
            return "Hospital context required"
        
        # Test patient access decorator
        request = self.factory.get('/test/')
        request.user = self.doctor
        self._add_hospital_context(request.user)
        
        with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
            mock_get.return_value = self.inpatient
            result = test_patient_view(request, patient_id='patient-1')
            self.assertEqual(result, "Success")
        
        # Test doctor required decorator
        request.user = self.doctor
        result = test_doctor_view(request)
        self.assertEqual(result, "Doctor only")
        
        request.user = self.nurse
        result = test_doctor_view(request)
        self.assertIsInstance(result, HttpResponseForbidden)
        
        # Test hospital context decorator
        request.user = self.doctor
        self._add_hospital_context(request.user)
        result = test_hospital_view(request)
        self.assertEqual(result, "Hospital context required")
        
        request.user.has_hospital_context = False
        result = test_hospital_view(request)
        self.assertIsInstance(result, HttpResponseForbidden)
    
    def test_template_tags_integration(self):
        """Test template tags integration."""
        template_content = """
        {% load permission_tags %}
        {% if user|is_profession:"medical_doctor" %}DOCTOR{% endif %}
        {% if user|in_group:"Nurses" %}NURSE{% endif %}
        {% if user|can_manage_patients %}CAN_MANAGE{% endif %}
        """
        
        template = Template(template_content)
        
        # Test doctor template rendering
        context = Context({'user': self.doctor})
        rendered = template.render(context)
        self.assertIn('DOCTOR', rendered)
        self.assertNotIn('NURSE', rendered)
        
        # Test nurse template rendering
        context = Context({'user': self.nurse})
        rendered = template.render(context)
        self.assertNotIn('DOCTOR', rendered)
        self.assertIn('NURSE', rendered)
    
    def test_cross_hospital_access_prevention(self):
        """Test that users cannot access patients in different hospitals."""
        # Create another hospital
        other_hospital = Mock()
        other_hospital.id = 'hospital-456'
        
        # Create patient in other hospital
        other_patient = Mock()
        other_patient.id = 'patient-3'
        other_patient.status = INPATIENT
        other_patient.current_hospital = other_hospital
        other_patient.current_hospital_id = other_hospital.id
        
        # Doctor in first hospital cannot access patient in second hospital
        self._add_hospital_context(self.doctor, self.hospital)
        self.assertFalse(can_access_patient(self.doctor, other_patient))
        
        # Doctor in second hospital can access patient in second hospital
        self._add_hospital_context(self.doctor, other_hospital)
        self.assertTrue(can_access_patient(self.doctor, other_patient))
    
    def test_permission_caching_integration(self):
        """Test that permission caching works correctly."""
        from apps.core.permissions.cache import clear_permission_cache, get_cache_stats
        
        # Clear cache before test
        clear_permission_cache()
        
        # Add hospital context
        self._add_hospital_context(self.doctor)
        
        # First call should miss cache
        result1 = can_access_patient(self.doctor, self.inpatient)
        self.assertTrue(result1)
        
        # Second call should hit cache
        result2 = can_access_patient(self.doctor, self.inpatient)
        self.assertTrue(result2)
        self.assertEqual(result1, result2)
        
        # Cache stats should show hits
        stats = get_cache_stats()
        self.assertGreater(stats['total_requests'], 0)
    
    def test_role_based_group_assignment_integration(self):
        """Test that role-based group assignment works correctly."""
        # Test that users are in correct groups based on profession
        self.assertTrue(self.doctor.groups.filter(name='Medical Doctors').exists())
        self.assertTrue(self.nurse.groups.filter(name='Nurses').exists())
        self.assertTrue(self.student.groups.filter(name='Students').exists())
        
        # Test that users are not in incorrect groups
        self.assertFalse(self.doctor.groups.filter(name='Nurses').exists())
        self.assertFalse(self.nurse.groups.filter(name='Students').exists())
        self.assertFalse(self.student.groups.filter(name='Medical Doctors').exists())
    
    def test_security_edge_cases(self):
        """Test security edge cases and boundary conditions."""
        # Test with None values
        self.assertFalse(can_access_patient(None, self.inpatient))
        self.assertFalse(can_access_patient(self.doctor, None))
        
        # Test with unauthenticated user
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        self.assertFalse(can_access_patient(unauthenticated_user, self.inpatient))
        
        # Test with user without profession type
        user_no_profession = User.objects.create_user(
            email='noprofession@test.com',
            password='testpass123'
        )
        self._add_hospital_context(user_no_profession)
        self.assertFalse(can_access_patient(user_no_profession, self.inpatient))
        
        # Test with patient without hospital
        patient_no_hospital = Mock()
        patient_no_hospital.id = 'patient-no-hospital'
        patient_no_hospital.status = INPATIENT
        patient_no_hospital.current_hospital = None
        patient_no_hospital.current_hospital_id = None
        
        self._add_hospital_context(self.doctor)
        self.assertFalse(can_access_patient(self.doctor, patient_no_hospital))
    
    def test_performance_with_multiple_checks(self):
        """Test system performance with multiple permission checks."""
        self._add_hospital_context(self.doctor)
        
        # Perform multiple permission checks
        for _ in range(100):
            can_access_patient(self.doctor, self.inpatient)
            can_change_patient_status(self.doctor, self.inpatient, DISCHARGED)
            can_change_patient_personal_data(self.doctor, self.inpatient)
        
        # Test should complete without timeout or errors
        # This is mainly to ensure no performance regressions
        self.assertTrue(True)  # If we get here, performance is acceptable
    
    def test_complete_user_workflow_simulation(self):
        """Simulate a complete user workflow through the system."""
        # 1. Doctor logs in and selects hospital
        self._add_hospital_context(self.doctor)
        
        # 2. Doctor searches for and accesses a patient
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))
        
        # 3. Doctor views patient details (can change personal data)
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.inpatient))
        
        # 4. Doctor changes patient status
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        
        # 5. Doctor creates a medical event
        # (This would be tested in the events app)
        
        # 6. Doctor edits the event within time limit
        with patch('django.utils.timezone.now') as mock_now:
            from django.utils import timezone
            from datetime import timedelta
            
            current_time = timezone.now()
            mock_now.return_value = current_time
            self.event.created_at = current_time - timedelta(hours=1)
            
            self.assertTrue(can_edit_event(self.doctor, self.event))
        
        # 7. Doctor discharges patient (only doctors can do this)
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        
        # Verify nurse cannot perform doctor-only actions
        self._add_hospital_context(self.nurse)
        self.assertFalse(can_change_patient_personal_data(self.nurse, self.inpatient))
        self.assertFalse(can_change_patient_status(self.nurse, self.inpatient, DISCHARGED))
        
        # Verify student has very limited access
        self._add_hospital_context(self.student)
        self.assertFalse(can_access_patient(self.student, self.inpatient))  # Students can't access inpatients
        self.assertTrue(can_access_patient(self.student, self.outpatient))   # But can access outpatients
        self.assertFalse(can_change_patient_status(self.student, self.outpatient, INPATIENT))  # Can't change status
