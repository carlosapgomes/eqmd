"""
Tests for permission utility functions.
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
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    NURSE,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
    DISCHARGED,
)

User = get_user_model()


class PermissionUtilsTestCase(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            profession_type=User.STUDENT
        )
        
        # Mock patient object
        self.patient = Mock()
        self.patient.status = INPATIENT
        self.patient.current_hospital = Mock()
        self.patient.current_hospital.id = 1
        
        # Mock event object
        self.event = Mock()
        self.event.created_by = self.doctor
        self.event.created_at = timezone.now()

    def test_can_access_patient_doctor_same_hospital(self):
        """Doctors can access patients in their current hospital"""
        # Set up hospital context using middleware attributes
        self.doctor.has_hospital_context = True
        self.doctor.current_hospital = Mock()
        self.doctor.current_hospital.id = 1
        result = can_access_patient(self.doctor, self.patient)
        self.assertTrue(result)

    def test_can_access_patient_doctor_different_hospital(self):
        """Doctors cannot access patients in different hospitals"""
        # Set up hospital context using middleware attributes
        self.doctor.has_hospital_context = True
        self.doctor.current_hospital = Mock()
        self.doctor.current_hospital.id = 2
        result = can_access_patient(self.doctor, self.patient)
        self.assertFalse(result)

    def test_can_access_patient_nurse_same_hospital(self):
        """Nurses can access patients in their current hospital"""
        # Set up hospital context using middleware attributes
        self.nurse.has_hospital_context = True
        self.nurse.current_hospital = Mock()
        self.nurse.current_hospital.id = 1
        result = can_access_patient(self.nurse, self.patient)
        self.assertTrue(result)

    def test_can_access_patient_student_limited_access(self):
        """Students have limited access to patients"""
        # Set up hospital context using middleware attributes
        self.student.has_hospital_context = True
        self.student.current_hospital = Mock()
        self.student.current_hospital.id = 1

        # Students can access outpatients
        self.patient.status = OUTPATIENT
        result = can_access_patient(self.student, self.patient)
        self.assertTrue(result)

        # Students cannot access inpatients
        self.patient.status = INPATIENT
        result = can_access_patient(self.student, self.patient)
        self.assertFalse(result)

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
        """Non-creators cannot edit events"""
        result = can_edit_event(self.nurse, self.event)
        self.assertFalse(result)

    def test_can_change_patient_status_doctor(self):
        """Doctors can change patient status"""
        result = can_change_patient_status(self.doctor, self.patient, DISCHARGED)
        self.assertTrue(result)

    def test_can_change_patient_status_nurse_limited(self):
        """Nurses have limited patient status change abilities"""
        # Nurses can change from emergency to inpatient
        self.patient.status = 'emergency'
        result = can_change_patient_status(self.nurse, self.patient, INPATIENT)
        self.assertTrue(result)
        
        # Nurses cannot discharge patients
        self.patient.status = INPATIENT
        result = can_change_patient_status(self.nurse, self.patient, DISCHARGED)
        self.assertFalse(result)

    def test_can_change_patient_status_student_no_permission(self):
        """Students cannot change patient status"""
        result = can_change_patient_status(self.student, self.patient, OUTPATIENT)
        self.assertFalse(result)