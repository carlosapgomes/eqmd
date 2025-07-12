"""
Tests for the simplified permission system without hospital context.

This test file validates that the new simplified permission model works correctly:
- All roles can access all patients
- Only doctors/residents can discharge patients 
- Only doctors/residents can change patient personal data
- Event editing still has 24-hour time restrictions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock

from apps.core.permissions.utils import (
    can_access_patient,
    can_edit_event,
    can_delete_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    get_user_accessible_patients,
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
)

User = get_user_model()


class SimplifiedPermissionSystemTests(TestCase):
    """Test the simplified permission system comprehensively."""

    def setUp(self):
        """Set up test users and mock objects."""
        # Create users with all profession types
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
        
        # Create user without profession type
        self.no_profession_user = User.objects.create_user(
            username='noprof',
            email='noprof@test.com',
            password='testpass123'
        )
        
        # Create mock patients with all status types
        self.patients = {}
        statuses = [INPATIENT, OUTPATIENT, EMERGENCY, DISCHARGED, TRANSFERRED]
        for i, status in enumerate(statuses):
            patient = Mock()
            patient.id = f'patient-{i+1}'
            patient.status = status
            self.patients[status] = patient
        
        # Create mock events
        self.recent_event = Mock()
        self.recent_event.id = 'event-1'
        self.recent_event.created_by = self.doctor
        self.recent_event.created_at = timezone.now() - timedelta(hours=1)
        
        self.old_event = Mock()
        self.old_event.id = 'event-2'
        self.old_event.created_by = self.doctor
        self.old_event.created_at = timezone.now() - timedelta(hours=25)

    def test_universal_patient_access(self):
        """Test that all roles can access all patients regardless of status."""
        all_users = [
            self.doctor, self.resident, self.nurse, 
            self.physiotherapist, self.student, self.no_profession_user
        ]
        
        for user in all_users:
            for status, patient in self.patients.items():
                with self.subTest(user=user.username, status=status):
                    self.assertTrue(
                        can_access_patient(user, patient),
                        f"{user.username} should access {status} patient"
                    )

    def test_discharge_permissions_doctors_residents_only(self):
        """Test that only doctors and residents can discharge patients."""
        discharge_users = [self.doctor, self.resident]
        non_discharge_users = [self.nurse, self.physiotherapist, self.student, self.no_profession_user]
        
        # Test users who CAN discharge
        for user in discharge_users:
            for status, patient in self.patients.items():
                with self.subTest(user=user.username, status=status):
                    self.assertTrue(
                        can_change_patient_status(user, patient, DISCHARGED),
                        f"{user.username} should be able to discharge {status} patient"
                    )
        
        # Test users who CANNOT discharge
        for user in non_discharge_users:
            for status, patient in self.patients.items():
                if status != DISCHARGED:  # Skip already discharged patients
                    with self.subTest(user=user.username, status=status):
                        self.assertFalse(
                            can_change_patient_status(user, patient, DISCHARGED),
                            f"{user.username} should NOT be able to discharge {status} patient"
                        )

    def test_personal_data_permissions_doctors_residents_only(self):
        """Test that only doctors and residents can change patient personal data."""
        privileged_users = [self.doctor, self.resident]
        restricted_users = [self.nurse, self.physiotherapist, self.student, self.no_profession_user]
        
        # Test users who CAN change personal data
        for user in privileged_users:
            for status, patient in self.patients.items():
                with self.subTest(user=user.username, status=status):
                    self.assertTrue(
                        can_change_patient_personal_data(user, patient),
                        f"{user.username} should be able to change personal data for {status} patient"
                    )
        
        # Test users who CANNOT change personal data
        for user in restricted_users:
            for status, patient in self.patients.items():
                with self.subTest(user=user.username, status=status):
                    self.assertFalse(
                        can_change_patient_personal_data(user, patient),
                        f"{user.username} should NOT be able to change personal data for {status} patient"
                    )

    def test_other_status_changes_all_roles(self):
        """Test that all roles can make non-discharge status changes."""
        all_users = [
            self.doctor, self.resident, self.nurse, 
            self.physiotherapist, self.student, self.no_profession_user
        ]
        
        # Test common status changes (non-discharge)
        test_changes = [
            (OUTPATIENT, INPATIENT),
            (EMERGENCY, INPATIENT),
            (INPATIENT, OUTPATIENT),
            (OUTPATIENT, TRANSFERRED),
        ]
        
        for user in all_users:
            for from_status, to_status in test_changes:
                patient = self.patients[from_status]
                with self.subTest(user=user.username, change=f"{from_status}->{to_status}"):
                    self.assertTrue(
                        can_change_patient_status(user, patient, to_status),
                        f"{user.username} should be able to change {from_status} to {to_status}"
                    )

    def test_event_editing_time_restrictions(self):
        """Test that event editing follows 24-hour time restrictions."""
        all_users = [
            self.doctor, self.resident, self.nurse, 
            self.physiotherapist, self.student, self.no_profession_user
        ]
        
        # Test recent event - only creator can edit
        self.assertTrue(can_edit_event(self.doctor, self.recent_event))
        self.assertTrue(can_delete_event(self.doctor, self.recent_event))
        
        for user in [self.resident, self.nurse, self.physiotherapist, self.student, self.no_profession_user]:
            self.assertFalse(can_edit_event(user, self.recent_event))
            self.assertFalse(can_delete_event(user, self.recent_event))
        
        # Test old event - no one can edit
        for user in all_users:
            self.assertFalse(can_edit_event(user, self.old_event))
            self.assertFalse(can_delete_event(user, self.old_event))

    def test_unauthenticated_user_restrictions(self):
        """Test that unauthenticated users have no permissions."""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        for status, patient in self.patients.items():
            # Cannot access patients
            self.assertFalse(can_access_patient(unauthenticated_user, patient))
            
            # Cannot change status
            self.assertFalse(can_change_patient_status(unauthenticated_user, patient, DISCHARGED))
            
            # Cannot change personal data
            self.assertFalse(can_change_patient_personal_data(unauthenticated_user, patient))
        
        # Cannot edit events
        self.assertFalse(can_edit_event(unauthenticated_user, self.recent_event))
        self.assertFalse(can_delete_event(unauthenticated_user, self.recent_event))

    def test_none_value_handling(self):
        """Test proper handling of None values."""
        # Test None user
        for status, patient in self.patients.items():
            self.assertFalse(can_access_patient(None, patient))
            self.assertFalse(can_change_patient_status(None, patient, DISCHARGED))
            self.assertFalse(can_change_patient_personal_data(None, patient))
        
        # Test None patient
        self.assertFalse(can_access_patient(self.doctor, None))
        self.assertFalse(can_change_patient_status(self.doctor, None, DISCHARGED))
        self.assertFalse(can_change_patient_personal_data(self.doctor, None))
        
        # Test None event
        self.assertFalse(can_edit_event(self.doctor, None))
        self.assertFalse(can_delete_event(self.doctor, None))

    def test_permission_matrix_comprehensive(self):
        """Test comprehensive permission matrix for all user types and actions."""
        permission_matrix = {
            'doctor': {
                'access_patients': True,
                'discharge': True,
                'personal_data': True,
                'edit_own_events': True,
                'edit_others_events': False,
            },
            'resident': {
                'access_patients': True,
                'discharge': True,
                'personal_data': True,
                'edit_own_events': True,
                'edit_others_events': False,
            },
            'nurse': {
                'access_patients': True,
                'discharge': False,
                'personal_data': False,
                'edit_own_events': True,
                'edit_others_events': False,
            },
            'physiotherapist': {
                'access_patients': True,
                'discharge': False,
                'personal_data': False,
                'edit_own_events': True,
                'edit_others_events': False,
            },
            'student': {
                'access_patients': True,
                'discharge': False,
                'personal_data': False,
                'edit_own_events': True,
                'edit_others_events': False,
            },
            'no_profession': {
                'access_patients': True,
                'discharge': False,
                'personal_data': False,
                'edit_own_events': True,
                'edit_others_events': False,
            },
        }
        
        user_map = {
            'doctor': self.doctor,
            'resident': self.resident,
            'nurse': self.nurse,
            'physiotherapist': self.physiotherapist,
            'student': self.student,
            'no_profession': self.no_profession_user,
        }
        
        for user_type, permissions in permission_matrix.items():
            user = user_map[user_type]
            patient = self.patients[INPATIENT]
            
            with self.subTest(user_type=user_type):
                # Test patient access
                self.assertEqual(
                    can_access_patient(user, patient),
                    permissions['access_patients'],
                    f"{user_type} patient access permission mismatch"
                )
                
                # Test discharge permission
                self.assertEqual(
                    can_change_patient_status(user, patient, DISCHARGED),
                    permissions['discharge'],
                    f"{user_type} discharge permission mismatch"
                )
                
                # Test personal data permission
                self.assertEqual(
                    can_change_patient_personal_data(user, patient),
                    permissions['personal_data'],
                    f"{user_type} personal data permission mismatch"
                )
                
                # Test own event editing (within time limit)
                own_event = Mock()
                own_event.created_by = user
                own_event.created_at = timezone.now() - timedelta(hours=1)
                
                self.assertEqual(
                    can_edit_event(user, own_event),
                    permissions['edit_own_events'],
                    f"{user_type} own event editing permission mismatch"
                )
                
                # Test others' event editing (self.recent_event belongs to self.doctor)
                # Only the doctor should be able to edit self.recent_event
                if user == self.doctor:
                    # Doctor editing their own event should follow own_events rule
                    expected = permissions['edit_own_events']
                else:
                    # Others editing doctor's event should follow others_events rule
                    expected = permissions['edit_others_events']
                
                self.assertEqual(
                    can_edit_event(user, self.recent_event),
                    expected,
                    f"{user_type} others' event editing permission mismatch"
                )

    def test_simplified_system_performance(self):
        """Test that the simplified system is performant."""
        # This test ensures that removing hospital context improves performance
        # by running many permission checks quickly
        
        import time
        start_time = time.time()
        
        # Run 1000 permission checks
        for _ in range(1000):
            can_access_patient(self.doctor, self.patients[INPATIENT])
            can_change_patient_status(self.nurse, self.patients[OUTPATIENT], INPATIENT)
            can_change_patient_personal_data(self.student, self.patients[EMERGENCY])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 1000 checks in under 1 second
        self.assertLess(execution_time, 1.0, 
                       f"Permission checks took too long: {execution_time:.3f}s")

    def test_backwards_compatibility_edge_cases(self):
        """Test edge cases that might arise from the hospital context removal."""
        # Test that patient status changes work for all combinations
        all_statuses = [INPATIENT, OUTPATIENT, EMERGENCY, DISCHARGED, TRANSFERRED]
        
        for from_status in all_statuses:
            for to_status in all_statuses:
                if from_status != to_status:
                    patient = self.patients[from_status]
                    
                    with self.subTest(change=f"{from_status}->{to_status}"):
                        # Doctors should be able to make any status change
                        self.assertTrue(
                            can_change_patient_status(self.doctor, patient, to_status),
                            f"Doctor should be able to change {from_status} to {to_status}"
                        )
                        
                        # Non-doctors should be able to make non-discharge changes
                        if to_status != DISCHARGED:
                            self.assertTrue(
                                can_change_patient_status(self.nurse, patient, to_status),
                                f"Nurse should be able to change {from_status} to {to_status}"
                            )

    def test_system_simplification_benefits(self):
        """Test that system simplification provides expected benefits."""
        # Benefit 1: All users can access all patients (no hospital barriers)
        all_users = [self.doctor, self.resident, self.nurse, self.physiotherapist, self.student]
        all_patients = list(self.patients.values())
        
        for user in all_users:
            for patient in all_patients:
                self.assertTrue(can_access_patient(user, patient))
        
        # Benefit 2: No hospital context needed for any operation
        # (This is implicitly tested by all other tests working without hospital setup)
        
        # Benefit 3: Reduced complexity while maintaining role-based security
        # Doctors still have more permissions than others
        doctor_can_discharge = can_change_patient_status(self.doctor, self.patients[INPATIENT], DISCHARGED)
        nurse_can_discharge = can_change_patient_status(self.nurse, self.patients[INPATIENT], DISCHARGED)
        
        self.assertTrue(doctor_can_discharge)
        self.assertFalse(nurse_can_discharge)
        
        # Benefit 4: Role hierarchy preserved for personal data
        doctor_can_change_data = can_change_patient_personal_data(self.doctor, self.patients[INPATIENT])
        student_can_change_data = can_change_patient_personal_data(self.student, self.patients[INPATIENT])
        
        self.assertTrue(doctor_can_change_data)
        self.assertFalse(student_can_change_data)