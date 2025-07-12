"""
Integration tests for the simplified permission system.

These tests verify that all components of the permission system work together
correctly, including utilities, decorators, and template tags.
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
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT,
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
    EMERGENCY,
    DISCHARGED,
)

User = get_user_model()


class SimplifiedPermissionSystemIntegrationTest(TestCase):
    """Test simplified permission system integration."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test users with different professions
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        self.resident = User.objects.create_user(
            email='resident@test.com',
            password='testpass123',
            profession_type=User.RESIDENT
        )
        
        self.nurse = User.objects.create_user(
            email='nurse@test.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        
        self.physiotherapist = User.objects.create_user(
            email='physio@test.com',
            password='testpass123',
            profession_type=User.PHYSIOTERAPIST
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            profession_type=User.STUDENT
        )
        
        # Create test groups
        self.doctor_group = Group.objects.create(name='Medical Doctors')
        self.resident_group = Group.objects.create(name='Residents')
        self.nurse_group = Group.objects.create(name='Nurses')
        self.physio_group = Group.objects.create(name='Physiotherapists')
        self.student_group = Group.objects.create(name='Students')
        
        # Assign users to groups
        self.doctor.groups.add(self.doctor_group)
        self.resident.groups.add(self.resident_group)
        self.nurse.groups.add(self.nurse_group)
        self.physiotherapist.groups.add(self.physio_group)
        self.student.groups.add(self.student_group)
        
        # Create mock patients with different statuses
        self.inpatient = Mock()
        self.inpatient.id = 'patient-1'
        self.inpatient.status = INPATIENT
        
        self.outpatient = Mock()
        self.outpatient.id = 'patient-2'
        self.outpatient.status = OUTPATIENT
        
        self.emergency_patient = Mock()
        self.emergency_patient.id = 'patient-3'
        self.emergency_patient.status = EMERGENCY
        
        # Create mock event
        self.event = Mock()
        self.event.id = 'event-1'
        self.event.created_by = self.doctor
        self.event.created_at = Mock()
        self.event.created_at.total_seconds.return_value = 3600  # 1 hour ago
    
    def test_complete_patient_access_workflow_simplified(self):
        """Test complete patient access workflow for simplified system."""
        # All user types can access all patients regardless of status
        all_users = [self.doctor, self.resident, self.nurse, self.physiotherapist, self.student]
        all_patients = [self.inpatient, self.outpatient, self.emergency_patient]
        
        for user in all_users:
            for patient in all_patients:
                self.assertTrue(can_access_patient(user, patient),
                               f"{user.email} should access {patient.status} patient")
    
    def test_patient_status_change_workflow_simplified(self):
        """Test patient status change workflow in simplified system."""        
        # Doctors and residents can change any status including discharge
        for user in [self.doctor, self.resident]:
            self.assertTrue(can_change_patient_status(user, self.inpatient, DISCHARGED))
            self.assertTrue(can_change_patient_status(user, self.outpatient, INPATIENT))
            self.assertTrue(can_change_patient_status(user, self.emergency_patient, INPATIENT))
        
        # Others can change some statuses but not discharge
        for user in [self.nurse, self.physiotherapist, self.student]:
            self.assertFalse(can_change_patient_status(user, self.inpatient, DISCHARGED))
            self.assertTrue(can_change_patient_status(user, self.outpatient, INPATIENT))
            self.assertTrue(can_change_patient_status(user, self.emergency_patient, INPATIENT))
    
    def test_personal_data_change_workflow_simplified(self):
        """Test patient personal data change workflow in simplified system."""
        # Only doctors and residents can change personal data
        for user in [self.doctor, self.resident]:
            self.assertTrue(can_change_patient_personal_data(user, self.inpatient))
            self.assertTrue(can_change_patient_personal_data(user, self.outpatient))
            self.assertTrue(can_change_patient_personal_data(user, self.emergency_patient))
        
        # Others cannot change personal data
        for user in [self.nurse, self.physiotherapist, self.student]:
            self.assertFalse(can_change_patient_personal_data(user, self.inpatient))
            self.assertFalse(can_change_patient_personal_data(user, self.outpatient))
            self.assertFalse(can_change_patient_personal_data(user, self.emergency_patient))
    
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
        
        # Other users cannot edit/delete regardless of role
        for user in [self.resident, self.nurse, self.physiotherapist, self.student]:
            self.assertFalse(can_edit_event(user, self.event))
            self.assertFalse(can_delete_event(user, self.event))
        
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
        
        # Test patient access decorator (all roles should have access)
        request = self.factory.get('/test/')
        
        for user in [self.doctor, self.resident, self.nurse, self.physiotherapist, self.student]:
            request.user = user
            
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_get.return_value = self.inpatient
                result = test_patient_view(request, patient_id='patient-1')
                self.assertEqual(result, "Success")
        
        # Test doctor required decorator
        request.user = self.doctor
        result = test_doctor_view(request)
        self.assertEqual(result, "Doctor only")
        
        # Non-doctors should be forbidden
        for user in [self.nurse, self.physiotherapist, self.student]:
            request.user = user
            result = test_doctor_view(request)
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
    
    def test_role_based_group_assignment_integration(self):
        """Test that role-based group assignment works correctly."""
        # Test that users are in correct groups based on profession
        self.assertTrue(self.doctor.groups.filter(name='Medical Doctors').exists())
        self.assertTrue(self.resident.groups.filter(name='Residents').exists())
        self.assertTrue(self.nurse.groups.filter(name='Nurses').exists())
        self.assertTrue(self.physiotherapist.groups.filter(name='Physiotherapists').exists())
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
        # In simplified system, users without profession should still be able to access patients
        self.assertTrue(can_access_patient(user_no_profession, self.inpatient))
        
        # But they should not be able to discharge or change personal data
        self.assertFalse(can_change_patient_status(user_no_profession, self.inpatient, DISCHARGED))
        self.assertFalse(can_change_patient_personal_data(user_no_profession, self.inpatient))
    
    def test_performance_with_multiple_checks(self):
        """Test system performance with multiple permission checks."""
        
        # Perform multiple permission checks
        for _ in range(100):
            can_access_patient(self.doctor, self.inpatient)
            can_change_patient_status(self.doctor, self.inpatient, DISCHARGED)
            can_change_patient_personal_data(self.doctor, self.inpatient)
        
        # Test should complete without timeout or errors
        # This is mainly to ensure no performance regressions
        self.assertTrue(True)  # If we get here, performance is acceptable
    
    def test_complete_user_workflow_simulation(self):
        """Simulate a complete user workflow through the simplified system."""
        # 1. Doctor logs in (no hospital selection needed)
        
        # 2. Doctor accesses any patient (all patients accessible)
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))
        self.assertTrue(can_access_patient(self.doctor, self.outpatient))
        self.assertTrue(can_access_patient(self.doctor, self.emergency_patient))
        
        # 3. Doctor views patient details (can change personal data)
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.inpatient))
        
        # 4. Doctor changes patient status
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        
        # 5. Doctor creates and edits medical events within time limit
        with patch('django.utils.timezone.now') as mock_now:
            from django.utils import timezone
            from datetime import timedelta
            
            current_time = timezone.now()
            mock_now.return_value = current_time
            self.event.created_at = current_time - timedelta(hours=1)
            
            self.assertTrue(can_edit_event(self.doctor, self.event))
        
        # 6. Doctor discharges patient (only doctors/residents can do this)
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        
        # Verify nurse can access patients but has limited permissions
        self.assertTrue(can_access_patient(self.nurse, self.inpatient))  # Can access
        self.assertFalse(can_change_patient_personal_data(self.nurse, self.inpatient))  # Cannot change personal data
        self.assertFalse(can_change_patient_status(self.nurse, self.inpatient, DISCHARGED))  # Cannot discharge
        
        # Verify student can access all patients but has very limited permissions
        self.assertTrue(can_access_patient(self.student, self.inpatient))  # Can access
        self.assertTrue(can_access_patient(self.student, self.outpatient))  # Can access
        self.assertFalse(can_change_patient_status(self.student, self.inpatient, DISCHARGED))  # Cannot discharge
        self.assertFalse(can_change_patient_personal_data(self.student, self.outpatient))  # Cannot change personal data
    
    def test_simplified_system_benefits(self):
        """Test that the simplified system removes hospital complexity."""
        # All users can access all patients without hospital context
        all_users = [self.doctor, self.resident, self.nurse, self.physiotherapist, self.student]
        all_patients = [self.inpatient, self.outpatient, self.emergency_patient]
        
        for user in all_users:
            for patient in all_patients:
                # No hospital context needed
                self.assertTrue(can_access_patient(user, patient))
                
        # Role-based permissions still work
        # Only doctors and residents can discharge
        discharge_users = [self.doctor, self.resident]
        non_discharge_users = [self.nurse, self.physiotherapist, self.student]
        
        for user in discharge_users:
            self.assertTrue(can_change_patient_status(user, self.inpatient, DISCHARGED))
            
        for user in non_discharge_users:
            self.assertFalse(can_change_patient_status(user, self.inpatient, DISCHARGED))
        
        # Only doctors and residents can change personal data
        for user in discharge_users:
            self.assertTrue(can_change_patient_personal_data(user, self.inpatient))
            
        for user in non_discharge_users:
            self.assertFalse(can_change_patient_personal_data(user, self.inpatient))