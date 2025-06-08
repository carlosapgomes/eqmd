"""
Tests for object-level permission functions.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock

from apps.core.permissions.utils import (
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
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
    TRANSFERRED,
    EVENT_EDIT_TIME_LIMIT,
)

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
        """Test that doctors cannot change inpatient data in different hospital."""
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = True
        self.user.current_hospital = self.hospital
        self.patient.status = INPATIENT
        
        other_hospital = Mock()
        other_hospital.id = 'hospital-456'
        self.patient.current_hospital = other_hospital
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertFalse(result)
    
    def test_doctor_cannot_change_inpatient_data_no_hospital_context(self):
        """Test that doctors cannot change inpatient data without hospital context."""
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.has_hospital_context = False
        self.patient.status = INPATIENT
        
        result = can_change_patient_personal_data(self.user, self.patient)
        self.assertFalse(result)
    
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
    """Test can_delete_event function."""
    
    def setUp(self):
        self.user = Mock()
        self.user.is_authenticated = True
        self.event = Mock()
        self.event.created_by = self.user
        self.event.created_at = timezone.now()
    
    def test_unauthenticated_user_cannot_delete_event(self):
        """Test that unauthenticated users cannot delete events."""
        self.user.is_authenticated = False
        result = can_delete_event(self.user, self.event)
        self.assertFalse(result)
    
    def test_non_creator_cannot_delete_event(self):
        """Test that non-creators cannot delete events."""
        other_user = Mock()
        self.event.created_by = other_user
        result = can_delete_event(self.user, self.event)
        self.assertFalse(result)
    
    def test_creator_can_delete_recent_event(self):
        """Test that creators can delete recent events."""
        self.event.created_at = timezone.now() - timedelta(hours=1)
        result = can_delete_event(self.user, self.event)
        self.assertTrue(result)
    
    def test_creator_cannot_delete_old_event(self):
        """Test that creators cannot delete old events."""
        self.event.created_at = timezone.now() - timedelta(hours=EVENT_EDIT_TIME_LIMIT + 1)
        result = can_delete_event(self.user, self.event)
        self.assertFalse(result)
    
    def test_event_without_created_at_cannot_be_deleted(self):
        """Test that events without created_at cannot be deleted."""
        self.event.created_at = None
        result = can_delete_event(self.user, self.event)
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
        """Test that users cannot see patients they don't have access to."""
        # Different hospital
        other_hospital = Mock()
        other_hospital.id = 'hospital-456'
        self.patient.current_hospital = other_hospital
        
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertFalse(result)
    
    def test_student_can_see_outpatient_only(self):
        """Test that students can only see outpatients in search."""
        self.user.profession_type = 4  # STUDENT
        
        # Student cannot see inpatient
        self.patient.status = INPATIENT
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertFalse(result)
        
        # Student can see outpatient
        self.patient.status = OUTPATIENT
        result = can_see_patient_in_search(self.user, self.patient)
        self.assertTrue(result)
