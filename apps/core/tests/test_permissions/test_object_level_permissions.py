"""
Tests for object-level permission functions.
"""

from datetime import date, timedelta
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

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
    TRANSFERRED,
    EVENT_EDIT_TIME_LIMIT,
)
from apps.core.permissions.utils import (
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
)
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()


class TestCanChangePatientPersonalData(TestCase):
    """Test can_change_patient_personal_data function."""
    
    def setUp(self):
        self.user = Mock()
        self.user.is_authenticated = True
        self.patient = Mock()
        self.hospital = Mock()
        self.hospital.id = 'hospital-123'
    
    def test_unauthenticated_user_cannot_change_data(self):
        """Test that unauthenticated users cannot change patient data."""
        self.user.is_authenticated = False
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertFalse(result)
    
    def test_non_doctor_cannot_change_data(self):
        """Test that non-doctors cannot change patient data."""
        self.user.profession_type = 2  # NURSE
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertFalse(result)
    
    def test_doctor_can_change_outpatient_data(self):
        """Test that doctors can change outpatient data."""
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.patient.status = OUTPATIENT
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertTrue(result)
    
    def test_doctor_can_change_inpatient_data_same_hospital(self):
        """Test that doctors can change inpatient data in same hospital."""
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = True
        self.user.current_hospital = self.hospital
        self.patient.status = INPATIENT
        self.patient.current_hospital = self.hospital
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertTrue(result)
    
    def test_doctor_cannot_change_inpatient_data_different_hospital(self):
        """Test that doctors can change inpatient data regardless of hospital.

        The single-hospital refactor (f210bc5) removed hospital-membership
        rules: personal-data changes only require doctor/resident role.
        """
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = True
        self.user.current_hospital = self.hospital
        self.patient.status = INPATIENT
        
        other_hospital = Mock()
        other_hospital.id = 'hospital-456'
        self.patient.current_hospital = other_hospital
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertTrue(result)
    
    def test_doctor_cannot_change_inpatient_data_no_hospital_context(self):
        """Test that doctors can change inpatient data without hospital context.

        The single-hospital refactor (f210bc5) removed the hospital-context
        requirement: personal-data changes only require doctor/resident role.
        """
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = False
        self.patient.status = INPATIENT
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertTrue(result)
    
    def test_doctor_can_change_emergency_patient_data_same_hospital(self):
        """Test that doctors can change emergency patient data in same hospital."""
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = True
        self.user.current_hospital = self.hospital
        self.patient.status = EMERGENCY
        self.patient.current_hospital = self.hospital
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertTrue(result)


class TestCanDeleteEvent(TestCase):
    """Test can_delete_event function.

    The predicate reads the finalization metadata of real rows, so these cases
    use persisted events (``created_at`` is not nullable).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="deletepredicateuser",
            email="deletepredicateuser@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.other_user = User.objects.create_user(
            username="deletepredicateother",
            email="deletepredicateother@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.patient = Patient.objects.create(
            name="Delete Predicate Patient",
            birthday=date(1990, 1, 1),
            created_by=self.user,
            updated_by=self.user,
        )

    def _create_owned_event(self, created_at):
        event = Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Delete predicate event",
            event_type=Event.SIMPLE_NOTE_EVENT,
            created_by=self.user,
            updated_by=self.user,
        )
        Event.all_objects.filter(pk=event.pk).update(created_at=created_at)
        event.refresh_from_db()
        return event

    def test_unauthenticated_user_cannot_delete_event(self):
        """Test that unauthenticated users cannot delete events."""
        event = self._create_owned_event(timezone.now())

        result = can_delete_event(AnonymousUser(), event)

        self.assertFalse(result)

    def test_non_creator_cannot_delete_event(self):
        """Test that non-creators cannot delete events."""
        event = self._create_owned_event(timezone.now())

        result = can_delete_event(self.other_user, event)

        self.assertFalse(result)

    def test_creator_can_delete_recent_event(self):
        """Test that creators can delete recent events."""
        event = self._create_owned_event(timezone.now() - timedelta(hours=1))

        result = can_delete_event(self.user, event)

        self.assertTrue(result)

    def test_creator_cannot_delete_old_event(self):
        """Test that creators cannot delete old events."""
        event = self._create_owned_event(
            timezone.now() - timedelta(hours=EVENT_EDIT_TIME_LIMIT + 1)
        )

        result = can_delete_event(self.user, event)

        self.assertFalse(result)

    def test_event_without_created_at_cannot_be_deleted(self):
        """Test that events without created_at cannot be deleted."""
        unsaved_event = Event(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Unsaved event",
            event_type=Event.SIMPLE_NOTE_EVENT,
            created_by=self.user,
            updated_by=self.user,
        )

        result = can_delete_event(self.user, unsaved_event)

        self.assertFalse(result)


class TestCanSeePatientInSearch(TestCase):
    """Test can_see_patient_in_search function."""
    
    def setUp(self):
        self.user = Mock()
        self.user.is_authenticated = True
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = True
        self.patient = Mock()
        self.hospital = Mock()
        self.hospital.id = 'hospital-123'
        self.user.current_hospital = self.hospital
        self.patient.current_hospital = self.hospital
        self.patient.status = INPATIENT
    
    def test_unauthenticated_user_cannot_see_patient(self):
        """Test that unauthenticated users cannot see patients in search."""
        self.user.is_authenticated = False
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertFalse(result)
    
    def test_user_can_see_accessible_patient(self):
        """Test that users can see patients they have access to."""
        # This should use the same logic as can_access_patient
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertTrue(result)
    
    def test_user_cannot_see_inaccessible_patient(self):
        """Test that all authenticated users can see patients in search.

        The single-hospital refactor (f210bc5) removed hospital-membership
        visibility rules: search visibility equals can_access_patient.
        """
        # Different hospital
        other_hospital = Mock()
        other_hospital.id = 'hospital-456'
        self.patient.current_hospital = other_hospital
        
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertTrue(result)
    
    def test_student_can_see_outpatient_only(self):
        """Test that students can see both inpatients and outpatients in search.

        The single-hospital refactor (f210bc5) removed the
        student-outpatient-only rule: search visibility equals
        can_access_patient for every authenticated user.
        """
        self.user.profession_type = 4  # STUDENT
        
        # Student can see inpatient
        self.patient.status = INPATIENT
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertTrue(result)
        
        # Student can see outpatient
        self.patient.status = OUTPATIENT
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertTrue(result)
