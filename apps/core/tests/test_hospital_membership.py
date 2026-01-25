"""
Tests for hospital membership functionality.
"""

import pytest

pytest.skip(
    "Hospital membership tests are deprecated after the single-hospital refactor.",
    allow_module_level=True,
)

import uuid
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from apps.hospitals.models import Hospital, Ward
from apps.hospitals.middleware import HospitalContextMiddleware
from apps.patients.models import Patient
from apps.core.permissions.utils import (
    is_hospital_member,
    has_any_hospital_membership,
    get_user_accessible_patients,
    can_access_patient,
    can_change_patient_personal_data,
    can_change_patient_status,
    can_create_event_type,
)
from apps.core.permissions.constants import MEDICAL_DOCTOR, NURSE, STUDENT, INPATIENT, OUTPATIENT


User = get_user_model()


class HospitalMembershipTestCase(TestCase):
    """Test hospital membership functionality."""

    def setUp(self):
        """Set up test data."""
        # Create hospitals
        self.hospital1 = Hospital.objects.create(
            name="Hospital A",
            short_name="HA"
        )
        self.hospital2 = Hospital.objects.create(
            name="Hospital B", 
            short_name="HB"
        )
        
        # Create ward
        self.ward1 = Ward.objects.create(
            name="Ward 1",
            hospital=self.hospital1,
            capacity=20
        )
        
        # Create users with different professions
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            profession_type=User.MEDICAL_DOCTOR
        )
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com', 
            profession_type=User.NURSE
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            profession_type=User.STUDENT
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com'
        )
        
        # Assign doctor to hospital1, nurse to both hospitals
        self.doctor.hospitals.add(self.hospital1)
        self.doctor.last_hospital = self.hospital1
        self.doctor.save()
        
        self.nurse.hospitals.add(self.hospital1, self.hospital2)
        self.nurse.last_hospital = self.hospital2
        self.nurse.save()
        
        # Student has no hospital assignments
        
        # Create patients
        from datetime import date
        self.patient1 = Patient.objects.create(
            name="Patient One",
            birthday=date(1990, 1, 1),
            current_hospital=self.hospital1,
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        self.patient2 = Patient.objects.create(
            name="Patient Two",
            birthday=date(1990, 1, 1),
            current_hospital=self.hospital2,
            status=Patient.Status.OUTPATIENT,
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        # Set up request factory and middleware
        self.factory = RequestFactory()
        self.middleware = HospitalContextMiddleware(lambda r: None)

    def _add_session_to_request(self, request):
        """Add session to request."""
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

    def test_is_hospital_member(self):
        """Test hospital membership checking."""
        # Doctor is member of hospital1 only
        self.assertTrue(is_hospital_member(self.doctor, self.hospital1))
        self.assertFalse(is_hospital_member(self.doctor, self.hospital2))
        
        # Nurse is member of both hospitals
        self.assertTrue(is_hospital_member(self.nurse, self.hospital1))
        self.assertTrue(is_hospital_member(self.nurse, self.hospital2))
        
        # Student is not member of any hospital
        self.assertFalse(is_hospital_member(self.student, self.hospital1))
        self.assertFalse(is_hospital_member(self.student, self.hospital2))
        
        # Superuser has access to all hospitals
        self.assertTrue(is_hospital_member(self.superuser, self.hospital1))
        self.assertTrue(is_hospital_member(self.superuser, self.hospital2))

    def test_has_any_hospital_membership(self):
        """Test checking if user has any hospital membership."""
        self.assertTrue(has_any_hospital_membership(self.doctor))
        self.assertTrue(has_any_hospital_membership(self.nurse))
        self.assertFalse(has_any_hospital_membership(self.student))
        self.assertTrue(has_any_hospital_membership(self.superuser))

    def test_get_user_accessible_patients(self):
        """Test getting patients accessible to user."""
        # Doctor can access patients in hospital1
        doctor_patients = get_user_accessible_patients(self.doctor)
        self.assertIn(self.patient1, doctor_patients)
        self.assertNotIn(self.patient2, doctor_patients)
        
        # Nurse can access patients in both hospitals
        nurse_patients = get_user_accessible_patients(self.nurse)
        self.assertIn(self.patient1, nurse_patients)
        self.assertIn(self.patient2, nurse_patients)
        
        # Student can access no patients (no hospital membership)
        student_patients = get_user_accessible_patients(self.student)
        self.assertEqual(student_patients.count(), 0)

    def test_hospital_context_middleware_auto_selection(self):
        """Test middleware auto-selects user's last hospital."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Initially no hospital context
        self.assertFalse(hasattr(request.user, 'current_hospital'))
        
        # Middleware should auto-select doctor's last hospital
        self.middleware._add_hospital_context(request)
        
        self.assertTrue(request.user.has_hospital_context)
        self.assertEqual(request.user.current_hospital, self.hospital1)
        self.assertEqual(request.session['current_hospital_id'], str(self.hospital1.id))

    def test_hospital_context_middleware_membership_validation(self):
        """Test middleware validates hospital membership."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Try to set hospital context to hospital the user is not a member of
        request.session['current_hospital_id'] = str(self.hospital2.id)
        
        # Middleware should clear invalid context and set to user's default
        self.middleware._add_hospital_context(request)
        
        # Should fall back to doctor's default hospital (hospital1)
        self.assertTrue(request.user.has_hospital_context)
        self.assertEqual(request.user.current_hospital, self.hospital1)

    def test_can_access_patient_with_membership(self):
        """Test patient access with hospital membership validation."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Set hospital context
        self.middleware.set_hospital_context(request, self.hospital1.id)
        
        # Doctor can access patient in hospital1
        self.assertTrue(can_access_patient(self.doctor, self.patient1))
        
        # Doctor cannot access patient in hospital2 (not a member)
        self.assertFalse(can_access_patient(self.doctor, self.patient2))

    def test_can_change_patient_personal_data_with_membership(self):
        """Test personal data change with membership validation."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Set hospital context
        self.middleware.set_hospital_context(request, self.hospital1.id)
        
        # Doctor can change personal data for inpatient in their hospital
        self.assertTrue(can_change_patient_personal_data(self.doctor, self.patient1))
        
        # Doctor cannot change personal data for patient in hospital they're not a member of
        self.assertFalse(can_change_patient_personal_data(self.doctor, self.patient2))

    def test_can_change_patient_status_with_membership(self):
        """Test status change with membership validation."""
        request = self.factory.get('/')
        request.user = self.nurse
        self._add_session_to_request(request)
        
        # Set hospital context to hospital1
        self.middleware.set_hospital_context(request, self.hospital1.id)
        
        # Nurse can change status for patient in hospital1
        self.assertTrue(can_change_patient_status(self.nurse, self.patient1, Patient.Status.OUTPATIENT))
        
        # Nurse cannot change status for patient in hospital2 without switching context
        self.assertFalse(can_change_patient_status(self.nurse, self.patient2, Patient.Status.INPATIENT))
        
        # Switch to hospital2
        self.middleware.set_hospital_context(request, self.hospital2.id)
        
        # Now nurse can change status for patient2
        self.assertTrue(can_change_patient_status(self.nurse, self.patient2, Patient.Status.INPATIENT))

    def test_can_create_event_type_with_membership(self):
        """Test event creation with membership validation."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Set hospital context
        self.middleware.set_hospital_context(request, self.hospital1.id)
        
        # Doctor can create events for patient in their hospital
        self.assertTrue(can_create_event_type(self.doctor, self.patient1, "Daily Notes"))
        
        # Doctor cannot create events for patient in hospital they're not a member of
        self.assertFalse(can_create_event_type(self.doctor, self.patient2, "Daily Notes"))

    def test_student_with_hospital_membership(self):
        """Test student permissions when they have hospital membership."""
        # Give student membership to hospital2
        self.student.hospitals.add(self.hospital2)
        self.student.last_hospital = self.hospital2
        self.student.save()
        
        request = self.factory.get('/')
        request.user = self.student
        self._add_session_to_request(request)
        
        # Set hospital context
        self.middleware.set_hospital_context(request, self.hospital2.id)
        
        # Student can access outpatient in their hospital
        self.assertTrue(can_access_patient(self.student, self.patient2))
        
        # Student cannot access inpatient even in their hospital
        self.assertFalse(can_access_patient(self.student, self.patient1))
        
        # Student cannot change patient status
        self.assertFalse(can_change_patient_status(self.student, self.patient2, Patient.Status.INPATIENT))
        
        # Student can only create basic events
        self.assertTrue(can_create_event_type(self.student, self.patient2, "Daily Notes"))
        self.assertFalse(can_create_event_type(self.student, self.patient2, "History and Physical"))

    def test_middleware_set_hospital_context_validation(self):
        """Test that middleware validates membership when setting context."""
        request = self.factory.get('/')
        request.user = self.doctor
        self._add_session_to_request(request)
        
        # Doctor can set context to hospital1 (member)
        result = self.middleware.set_hospital_context(request, self.hospital1.id)
        self.assertEqual(result, self.hospital1)
        self.assertEqual(request.user.current_hospital, self.hospital1)
        
        # Doctor cannot set context to hospital2 (not a member)
        result = self.middleware.set_hospital_context(request, self.hospital2.id)
        self.assertIsNone(result)
        # Context should remain hospital1
        self.assertEqual(request.user.current_hospital, self.hospital1)

    def test_middleware_get_available_hospitals(self):
        """Test getting available hospitals for users."""
        # Doctor gets only hospital1
        doctor_hospitals = self.middleware.get_available_hospitals(self.doctor)
        self.assertIn(self.hospital1, doctor_hospitals)
        self.assertNotIn(self.hospital2, doctor_hospitals)
        
        # Nurse gets both hospitals
        nurse_hospitals = self.middleware.get_available_hospitals(self.nurse)
        self.assertIn(self.hospital1, nurse_hospitals)
        self.assertIn(self.hospital2, nurse_hospitals)
        
        # Student gets no hospitals
        student_hospitals = self.middleware.get_available_hospitals(self.student)
        self.assertEqual(student_hospitals.count(), 0)
        
        # Superuser gets all hospitals
        superuser_hospitals = self.middleware.get_available_hospitals(self.superuser)
        self.assertIn(self.hospital1, superuser_hospitals)
        self.assertIn(self.hospital2, superuser_hospitals)

    def test_last_hospital_update_on_context_switch(self):
        """Test that last_hospital is updated when switching context."""
        request = self.factory.get('/')
        request.user = self.nurse
        self._add_session_to_request(request)
        
        # Initial last_hospital is hospital2
        self.assertEqual(self.nurse.last_hospital, self.hospital2)
        
        # Switch to hospital1
        self.middleware.set_hospital_context(request, self.hospital1.id)
        
        # Refresh from database
        self.nurse.refresh_from_db()
        
        # last_hospital should be updated to hospital1
        self.assertEqual(self.nurse.last_hospital, self.hospital1)
