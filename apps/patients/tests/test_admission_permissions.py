"""
Tests for admission edit permissions functionality.

This module tests the admission-specific permission functions for editing
admission data, discharge data, and cancelling discharges.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth.models import User
from unittest.mock import Mock, patch

from apps.core.permissions.utils import (
    can_edit_admission_data,
    can_discharge_patient,
    can_edit_discharge_data,
    can_cancel_discharge,
)
from apps.core.permissions.constants import (
    ADMISSION_EDIT_TIME_LIMIT,
    DISCHARGE_EDIT_TIME_LIMIT,
)


class AdmissionEditPermissionTests(TestCase):
    """Test admission edit permission functions."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        
        # Create mock users with different profession types
        self.doctor = Mock()
        self.doctor.is_authenticated = True
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR
        
        self.resident = Mock()
        self.resident.is_authenticated = True
        self.resident.profession_type = 1  # RESIDENT
        
        self.nurse = Mock()
        self.nurse.is_authenticated = True
        self.nurse.profession_type = 2  # NURSE
        
        self.student = Mock()
        self.student.is_authenticated = True
        self.student.profession_type = 4  # STUDENT
        
        self.unauthenticated_user = Mock()
        self.unauthenticated_user.is_authenticated = False
        
        # Create mock active admission (not discharged)
        self.active_admission = Mock()
        self.active_admission.discharge_datetime = None
        self.active_admission.created_at = self.now - timedelta(hours=1)
        self.active_admission.created_by = self.nurse
        
        # Create mock old active admission (beyond 24h)
        self.old_active_admission = Mock()
        self.old_active_admission.discharge_datetime = None
        self.old_active_admission.created_at = self.now - timedelta(hours=25)
        self.old_active_admission.created_by = self.nurse
        
        # Create mock discharged admission (within 24h)
        self.discharged_admission = Mock()
        self.discharged_admission.discharge_datetime = self.now - timedelta(hours=1)
        self.discharged_admission.created_at = self.now - timedelta(hours=48)
        self.discharged_admission.created_by = self.nurse
        
        # Create mock old discharged admission (beyond 24h)
        self.old_discharged_admission = Mock()
        self.old_discharged_admission.discharge_datetime = self.now - timedelta(hours=25)
        self.old_discharged_admission.created_at = self.now - timedelta(hours=72)
        self.old_discharged_admission.created_by = self.nurse

    def test_can_edit_admission_data_doctor_on_active_admission(self):
        """Doctors can always edit active admissions."""
        result = can_edit_admission_data(self.doctor, self.active_admission)
        self.assertTrue(result)

    def test_can_edit_admission_data_resident_on_active_admission(self):
        """Residents can always edit active admissions."""
        result = can_edit_admission_data(self.resident, self.active_admission)
        self.assertTrue(result)

    def test_can_edit_admission_data_doctor_on_old_active_admission(self):
        """Doctors can edit active admissions regardless of time."""
        result = can_edit_admission_data(self.doctor, self.old_active_admission)
        self.assertTrue(result)

    def test_can_edit_admission_data_creator_within_24h(self):
        """Creator can edit admission data within 24h."""
        result = can_edit_admission_data(self.nurse, self.active_admission)
        self.assertTrue(result)

    def test_cannot_edit_admission_data_creator_after_24h(self):
        """Creator cannot edit admission data after 24h."""
        result = can_edit_admission_data(self.nurse, self.old_active_admission)
        self.assertFalse(result)

    def test_cannot_edit_admission_data_non_creator_non_doctor(self):
        """Non-creator non-doctors cannot edit admission data."""
        result = can_edit_admission_data(self.student, self.active_admission)
        self.assertFalse(result)

    def test_cannot_edit_admission_data_on_discharged_admission(self):
        """Cannot edit admission data on discharged admissions."""
        result = can_edit_admission_data(self.doctor, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_edit_admission_data_unauthenticated_user(self):
        """Unauthenticated users cannot edit admission data."""
        result = can_edit_admission_data(self.unauthenticated_user, self.active_admission)
        self.assertFalse(result)

    def test_cannot_edit_admission_data_none_user(self):
        """None user cannot edit admission data."""
        result = can_edit_admission_data(None, self.active_admission)
        self.assertFalse(result)

    def test_cannot_edit_admission_data_none_admission(self):
        """Cannot edit None admission."""
        result = can_edit_admission_data(self.doctor, None)
        self.assertFalse(result)

    def test_can_edit_admission_data_missing_created_at(self):
        """Handle admission without created_at gracefully."""
        admission_no_created_at = Mock()
        admission_no_created_at.discharge_datetime = None
        admission_no_created_at.created_at = None
        admission_no_created_at.created_by = self.nurse
        
        # Doctor should still be able to edit
        result = can_edit_admission_data(self.doctor, admission_no_created_at)
        self.assertTrue(result)
        
        # Creator should not be able to edit (missing created_at)
        result = can_edit_admission_data(self.nurse, admission_no_created_at)
        self.assertFalse(result)


class DischargePatientPermissionTests(TestCase):
    """Test discharge patient permission functions."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        
        # Create mock users
        self.doctor = Mock()
        self.doctor.is_authenticated = True
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR
        
        self.resident = Mock()
        self.resident.is_authenticated = True
        self.resident.profession_type = 1  # RESIDENT
        
        self.nurse = Mock()
        self.nurse.is_authenticated = True
        self.nurse.profession_type = 2  # NURSE
        
        # Create mock active admission
        self.active_admission = Mock()
        self.active_admission.discharge_datetime = None
        
        # Create mock discharged admission
        self.discharged_admission = Mock()
        self.discharged_admission.discharge_datetime = self.now - timedelta(hours=1)

    def test_can_discharge_patient_doctor(self):
        """Doctors can discharge patients."""
        result = can_discharge_patient(self.doctor, self.active_admission)
        self.assertTrue(result)

    def test_can_discharge_patient_resident(self):
        """Residents can discharge patients."""
        result = can_discharge_patient(self.resident, self.active_admission)
        self.assertTrue(result)

    def test_cannot_discharge_patient_nurse(self):
        """Nurses cannot discharge patients."""
        result = can_discharge_patient(self.nurse, self.active_admission)
        self.assertFalse(result)

    def test_cannot_discharge_already_discharged_patient(self):
        """Cannot discharge already discharged patient."""
        result = can_discharge_patient(self.doctor, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_discharge_patient_none_user(self):
        """None user cannot discharge patient."""
        result = can_discharge_patient(None, self.active_admission)
        self.assertFalse(result)

    def test_cannot_discharge_patient_none_admission(self):
        """Cannot discharge None admission."""
        result = can_discharge_patient(self.doctor, None)
        self.assertFalse(result)


class EditDischargeDataPermissionTests(TestCase):
    """Test edit discharge data permission functions."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        
        # Create mock users
        self.doctor = Mock()
        self.doctor.is_authenticated = True
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR
        
        self.resident = Mock()
        self.resident.is_authenticated = True
        self.resident.profession_type = 1  # RESIDENT
        
        self.nurse = Mock()
        self.nurse.is_authenticated = True
        self.nurse.profession_type = 2  # NURSE
        
        # Create mock discharged admission (within 24h)
        self.discharged_admission = Mock()
        self.discharged_admission.discharge_datetime = self.now - timedelta(hours=1)
        
        # Create mock old discharged admission (beyond 24h)
        self.old_discharged_admission = Mock()
        self.old_discharged_admission.discharge_datetime = self.now - timedelta(hours=25)
        
        # Create mock active admission
        self.active_admission = Mock()
        self.active_admission.discharge_datetime = None

    def test_can_edit_discharge_data_doctor_within_24h(self):
        """Doctors can edit discharge data within 24h."""
        result = can_edit_discharge_data(self.doctor, self.discharged_admission)
        self.assertTrue(result)

    def test_can_edit_discharge_data_resident_within_24h(self):
        """Residents can edit discharge data within 24h."""
        result = can_edit_discharge_data(self.resident, self.discharged_admission)
        self.assertTrue(result)

    def test_cannot_edit_discharge_data_nurse(self):
        """Nurses cannot edit discharge data."""
        result = can_edit_discharge_data(self.nurse, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_edit_discharge_data_after_24h(self):
        """Cannot edit discharge data after 24h window."""
        result = can_edit_discharge_data(self.doctor, self.old_discharged_admission)
        self.assertFalse(result)

    def test_cannot_edit_discharge_data_on_active_admission(self):
        """Cannot edit discharge data on active admissions."""
        result = can_edit_discharge_data(self.doctor, self.active_admission)
        self.assertFalse(result)

    def test_cannot_edit_discharge_data_none_user(self):
        """None user cannot edit discharge data."""
        result = can_edit_discharge_data(None, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_edit_discharge_data_none_admission(self):
        """Cannot edit None admission discharge data."""
        result = can_edit_discharge_data(self.doctor, None)
        self.assertFalse(result)


class CancelDischargePermissionTests(TestCase):
    """Test cancel discharge permission functions."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        
        # Create mock users
        self.doctor = Mock()
        self.doctor.is_authenticated = True
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR
        
        self.resident = Mock()
        self.resident.is_authenticated = True
        self.resident.profession_type = 1  # RESIDENT
        
        self.nurse = Mock()
        self.nurse.is_authenticated = True
        self.nurse.profession_type = 2  # NURSE
        
        # Create mock discharged admission (within 24h)
        self.discharged_admission = Mock()
        self.discharged_admission.discharge_datetime = self.now - timedelta(hours=1)
        
        # Create mock old discharged admission (beyond 24h)
        self.old_discharged_admission = Mock()
        self.old_discharged_admission.discharge_datetime = self.now - timedelta(hours=25)
        
        # Create mock active admission
        self.active_admission = Mock()
        self.active_admission.discharge_datetime = None

    def test_can_cancel_discharge_doctor_within_24h(self):
        """Doctors can cancel discharge within 24h."""
        result = can_cancel_discharge(self.doctor, self.discharged_admission)
        self.assertTrue(result)

    def test_can_cancel_discharge_resident_within_24h(self):
        """Residents can cancel discharge within 24h."""
        result = can_cancel_discharge(self.resident, self.discharged_admission)
        self.assertTrue(result)

    def test_cannot_cancel_discharge_nurse(self):
        """Nurses cannot cancel discharge."""
        result = can_cancel_discharge(self.nurse, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_cancel_discharge_after_24h(self):
        """Cannot cancel discharge after 24h window."""
        result = can_cancel_discharge(self.doctor, self.old_discharged_admission)
        self.assertFalse(result)

    def test_cannot_cancel_discharge_on_active_admission(self):
        """Cannot cancel discharge on active admissions."""
        result = can_cancel_discharge(self.doctor, self.active_admission)
        self.assertFalse(result)

    def test_cannot_cancel_discharge_none_user(self):
        """None user cannot cancel discharge."""
        result = can_cancel_discharge(None, self.discharged_admission)
        self.assertFalse(result)

    def test_cannot_cancel_discharge_none_admission(self):
        """Cannot cancel discharge on None admission."""
        result = can_cancel_discharge(self.doctor, None)
        self.assertFalse(result)


class EdgeCasePermissionTests(TestCase):
    """Test edge cases in admission permissions."""

    def setUp(self):
        """Set up test data."""
        self.doctor = Mock()
        self.doctor.is_authenticated = True
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR

    def test_admission_permissions_with_missing_attributes(self):
        """Test permission functions handle missing attributes gracefully."""
        # Admission without created_by
        admission_no_creator = Mock()
        admission_no_creator.discharge_datetime = None
        admission_no_creator.created_at = timezone.now()
        admission_no_creator.created_by = None
        
        result = can_edit_admission_data(self.doctor, admission_no_creator)
        self.assertTrue(result)  # Doctor can still edit
        
        # Admission without discharge_datetime attribute
        admission_no_discharge_attr = Mock()
        delattr(admission_no_discharge_attr, 'discharge_datetime')
        admission_no_discharge_attr.created_at = timezone.now()
        admission_no_discharge_attr.created_by = self.doctor
        
        # Should handle missing attribute gracefully
        result = can_edit_admission_data(self.doctor, admission_no_discharge_attr)
        self.assertTrue(result)

    def test_time_boundary_conditions(self):
        """Test permission functions at exact time boundaries."""
        now = timezone.now()
        
        # Admission at exactly 24 hours
        admission_exact_24h = Mock()
        admission_exact_24h.discharge_datetime = None
        admission_exact_24h.created_at = now - timedelta(hours=24)
        admission_exact_24h.created_by = Mock()
        admission_exact_24h.created_by.is_authenticated = True
        admission_exact_24h.created_by.profession_type = 2  # NURSE
        
        with patch('apps.core.permissions.utils.timezone.now', return_value=now):
            result = can_edit_admission_data(admission_exact_24h.created_by, admission_exact_24h)
            self.assertTrue(result)  # At exactly 24h, should still be allowed
        
        # Discharge at exactly 24 hours
        discharged_exact_24h = Mock()
        discharged_exact_24h.discharge_datetime = now - timedelta(hours=24)
        
        with patch('apps.core.permissions.utils.timezone.now', return_value=now):
            result = can_edit_discharge_data(self.doctor, discharged_exact_24h)
            self.assertTrue(result)  # At exactly 24h, should still be allowed

    def test_unauthenticated_user_all_permissions(self):
        """Test that unauthenticated users are denied all permissions."""
        unauthenticated = Mock()
        unauthenticated.is_authenticated = False
        
        admission = Mock()
        admission.discharge_datetime = None
        admission.created_at = timezone.now()
        
        self.assertFalse(can_edit_admission_data(unauthenticated, admission))
        self.assertFalse(can_discharge_patient(unauthenticated, admission))
        self.assertFalse(can_edit_discharge_data(unauthenticated, admission))
        self.assertFalse(can_cancel_discharge(unauthenticated, admission))