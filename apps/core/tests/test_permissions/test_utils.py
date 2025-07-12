"""
Tests for simplified permission utility functions.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock

from apps.core.permissions.utils import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT,
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
    DISCHARGED,
)

User = get_user_model()


class SimplifiedPermissionUtilsTestCase(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        self.resident = User.objects.create_user(
            username='resident',
            email='resident@test.com',
            password='testpass123',
            profession_type=User.RESIDENT
        )
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        self.physiotherapist = User.objects.create_user(
            username='physio',
            email='physio@test.com',
            password='testpass123',
            profession_type=User.PHYSIOTERAPIST
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            profession_type=User.STUDENT
        )
        
        # Mock patient objects with different statuses
        self.inpatient = Mock()
        self.inpatient.status = INPATIENT
        
        self.outpatient = Mock()
        self.outpatient.status = OUTPATIENT
        
        self.discharged_patient = Mock()
        self.discharged_patient.status = DISCHARGED
        
        # Mock event object
        self.event = Mock()
        self.event.created_by = self.doctor
        self.event.created_at = timezone.now()

    def test_all_roles_can_access_all_patients(self):
        """All roles can access all patients regardless of status"""
        # Test all user types can access inpatients
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))
        self.assertTrue(can_access_patient(self.resident, self.inpatient))
        self.assertTrue(can_access_patient(self.nurse, self.inpatient))
        self.assertTrue(can_access_patient(self.physiotherapist, self.inpatient))
        self.assertTrue(can_access_patient(self.student, self.inpatient))
        
        # Test all user types can access outpatients
        self.assertTrue(can_access_patient(self.doctor, self.outpatient))
        self.assertTrue(can_access_patient(self.resident, self.outpatient))
        self.assertTrue(can_access_patient(self.nurse, self.outpatient))
        self.assertTrue(can_access_patient(self.physiotherapist, self.outpatient))
        self.assertTrue(can_access_patient(self.student, self.outpatient))
        
        # Test all user types can access discharged patients
        self.assertTrue(can_access_patient(self.doctor, self.discharged_patient))
        self.assertTrue(can_access_patient(self.resident, self.discharged_patient))
        self.assertTrue(can_access_patient(self.nurse, self.discharged_patient))
        self.assertTrue(can_access_patient(self.physiotherapist, self.discharged_patient))
        self.assertTrue(can_access_patient(self.student, self.discharged_patient))

    def test_can_access_patient_unauthenticated_user(self):
        """Unauthenticated users cannot access patients"""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        self.assertFalse(can_access_patient(unauthenticated_user, self.inpatient))
        self.assertFalse(can_access_patient(unauthenticated_user, self.outpatient))
        
    def test_can_access_patient_none_values(self):
        """Test edge cases with None values"""
        self.assertFalse(can_access_patient(None, self.inpatient))
        self.assertFalse(can_access_patient(self.doctor, None))
        self.assertFalse(can_access_patient(None, None))

    def test_can_edit_event_creator_within_time_limit(self):
        """Event creators can edit events within 24 hours"""
        result = can_edit_event(self.doctor, self.event)
        self.assertTrue(result)

    def test_can_edit_event_creator_after_time_limit(self):
        """Event creators cannot edit events after 24 hours"""
        self.event.created_at = timezone.now() - timedelta(hours=25)
        result = can_edit_event(self.doctor, self.event)
        self.assertFalse(result)

    def test_can_edit_event_non_creator(self):
        """Non-creators cannot edit events regardless of role"""
        result = can_edit_event(self.nurse, self.event)
        self.assertFalse(result)
        
        result = can_edit_event(self.resident, self.event)
        self.assertFalse(result)
        
        result = can_edit_event(self.student, self.event)
        self.assertFalse(result)

    def test_can_edit_event_edge_cases(self):
        """Test event editing edge cases"""
        # Test with None values
        self.assertFalse(can_edit_event(None, self.event))
        self.assertFalse(can_edit_event(self.doctor, None))
        
        # Test with unauthenticated user
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        self.assertFalse(can_edit_event(unauthenticated_user, self.event))

    def test_can_change_patient_status_doctors_and_residents(self):
        """Doctors and residents can change any patient status including discharge"""
        # Test doctors can discharge
        self.assertTrue(can_change_patient_status(self.doctor, self.inpatient, DISCHARGED))
        self.assertTrue(can_change_patient_status(self.doctor, self.outpatient, INPATIENT))
        
        # Test residents can discharge
        self.assertTrue(can_change_patient_status(self.resident, self.inpatient, DISCHARGED))
        self.assertTrue(can_change_patient_status(self.resident, self.outpatient, INPATIENT))

    def test_can_change_patient_status_others_limited(self):
        """Nurses, physiotherapists, and students cannot discharge patients"""
        # Test nurses cannot discharge
        self.assertFalse(can_change_patient_status(self.nurse, self.inpatient, DISCHARGED))
        
        # Test physiotherapists cannot discharge
        self.assertFalse(can_change_patient_status(self.physiotherapist, self.inpatient, DISCHARGED))
        
        # Test students cannot discharge
        self.assertFalse(can_change_patient_status(self.student, self.inpatient, DISCHARGED))
        
        # But they can make other status changes
        self.assertTrue(can_change_patient_status(self.nurse, self.outpatient, INPATIENT))
        self.assertTrue(can_change_patient_status(self.physiotherapist, self.outpatient, INPATIENT))
        self.assertTrue(can_change_patient_status(self.student, self.outpatient, INPATIENT))

    def test_can_change_patient_personal_data_doctors_and_residents_only(self):
        """Only doctors and residents can change patient personal data"""
        # Doctors and residents can change personal data
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.inpatient))
        self.assertTrue(can_change_patient_personal_data(self.resident, self.inpatient))
        
        # Others cannot change personal data
        self.assertFalse(can_change_patient_personal_data(self.nurse, self.inpatient))
        self.assertFalse(can_change_patient_personal_data(self.physiotherapist, self.inpatient))
        self.assertFalse(can_change_patient_personal_data(self.student, self.inpatient))

    def test_simplified_permission_model_integration(self):
        """Test that the simplified permission model works as expected"""
        # All users can access all patients
        for user in [self.doctor, self.resident, self.nurse, self.physiotherapist, self.student]:
            for patient in [self.inpatient, self.outpatient, self.discharged_patient]:
                self.assertTrue(can_access_patient(user, patient), 
                               f"{user.username} should access {patient.status} patient")
        
        # Only doctors and residents can discharge
        for user in [self.doctor, self.resident]:
            self.assertTrue(can_change_patient_status(user, self.inpatient, DISCHARGED))
            
        for user in [self.nurse, self.physiotherapist, self.student]:
            self.assertFalse(can_change_patient_status(user, self.inpatient, DISCHARGED))
        
        # Only doctors and residents can change personal data
        for user in [self.doctor, self.resident]:
            self.assertTrue(can_change_patient_personal_data(user, self.inpatient))
            
        for user in [self.nurse, self.physiotherapist, self.student]:
            self.assertFalse(can_change_patient_personal_data(user, self.inpatient))