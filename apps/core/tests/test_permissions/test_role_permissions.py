"""
Tests for role-based permission system.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from unittest.mock import Mock

from apps.core.permissions.utils import (
    has_django_permission,
    is_in_group,
    get_user_profession_type,
    can_manage_patients,
    can_view_patients,
    can_manage_events,
    can_view_events,
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT,
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
)

User = get_user_model()


class RolePermissionUtilsTestCase(TestCase):
    def setUp(self):
        # Create test users with different profession types
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
        
        # Create test groups
        self.medical_doctors_group, _ = Group.objects.get_or_create(name='Medical Doctors')
        self.residents_group, _ = Group.objects.get_or_create(name='Residents')
        self.nurses_group, _ = Group.objects.get_or_create(name='Nurses')
        self.physiotherapists_group, _ = Group.objects.get_or_create(name='Physiotherapists')
        self.students_group, _ = Group.objects.get_or_create(name='Students')
        
        # Add users to groups
        self.doctor.groups.add(self.medical_doctors_group)
        self.resident.groups.add(self.residents_group)
        self.nurse.groups.add(self.nurses_group)
        self.physiotherapist.groups.add(self.physiotherapists_group)
        self.student.groups.add(self.students_group)

    def test_has_django_permission_authenticated_user(self):
        """Test has_django_permission with authenticated user"""
        # Mock permission check
        self.doctor.has_perm = Mock(return_value=True)
        
        result = has_django_permission(self.doctor, 'patients.add_patient')
        self.assertTrue(result)
        self.doctor.has_perm.assert_called_once_with('patients.add_patient')

    def test_has_django_permission_unauthenticated_user(self):
        """Test has_django_permission with unauthenticated user"""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        result = has_django_permission(unauthenticated_user, 'patients.add_patient')
        self.assertFalse(result)

    def test_is_in_group_member(self):
        """Test is_in_group with group member"""
        result = is_in_group(self.doctor, 'Medical Doctors')
        self.assertTrue(result)

    def test_is_in_group_non_member(self):
        """Test is_in_group with non-member"""
        result = is_in_group(self.doctor, 'Nurses')
        self.assertFalse(result)

    def test_is_in_group_unauthenticated_user(self):
        """Test is_in_group with unauthenticated user"""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        result = is_in_group(unauthenticated_user, 'Medical Doctors')
        self.assertFalse(result)

    def test_get_user_profession_type_doctor(self):
        """Test get_user_profession_type for doctor"""
        result = get_user_profession_type(self.doctor)
        self.assertEqual(result, MEDICAL_DOCTOR)

    def test_get_user_profession_type_resident(self):
        """Test get_user_profession_type for resident"""
        result = get_user_profession_type(self.resident)
        self.assertEqual(result, RESIDENT)

    def test_get_user_profession_type_nurse(self):
        """Test get_user_profession_type for nurse"""
        result = get_user_profession_type(self.nurse)
        self.assertEqual(result, NURSE)

    def test_get_user_profession_type_physiotherapist(self):
        """Test get_user_profession_type for physiotherapist"""
        result = get_user_profession_type(self.physiotherapist)
        self.assertEqual(result, PHYSIOTHERAPIST)

    def test_get_user_profession_type_student(self):
        """Test get_user_profession_type for student"""
        result = get_user_profession_type(self.student)
        self.assertEqual(result, STUDENT)

    def test_get_user_profession_type_unauthenticated(self):
        """Test get_user_profession_type for unauthenticated user"""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        result = get_user_profession_type(unauthenticated_user)
        self.assertIsNone(result)

    def test_get_user_profession_type_no_profession(self):
        """Test get_user_profession_type for user without profession"""
        user_no_profession = User.objects.create_user(
            username='noprof',
            email='noprof@test.com',
            password='testpass123'
        )
        
        result = get_user_profession_type(user_no_profession)
        self.assertIsNone(result)

    def test_can_manage_patients_with_permissions(self):
        """Test can_manage_patients with user having all required permissions"""
        # Mock all required permissions
        self.doctor.has_perm = Mock(return_value=True)
        
        result = can_manage_patients(self.doctor)
        self.assertTrue(result)
        
        # Verify all permissions were checked
        expected_calls = [
            ('patients.add_patient',),
            ('patients.change_patient',),
            ('patients.delete_patient',),
        ]
        actual_calls = [call[0] for call in self.doctor.has_perm.call_args_list]
        self.assertEqual(len(actual_calls), 3)
        for expected_call in expected_calls:
            self.assertIn(expected_call, actual_calls)

    def test_can_manage_patients_missing_permissions(self):
        """Test can_manage_patients with user missing some permissions"""
        # Mock partial permissions
        def mock_has_perm(perm):
            return perm != 'patients.delete_patient'
        
        self.doctor.has_perm = Mock(side_effect=mock_has_perm)
        
        result = can_manage_patients(self.doctor)
        self.assertFalse(result)

    def test_can_view_patients_with_permission(self):
        """Test can_view_patients with user having view permission"""
        self.doctor.has_perm = Mock(return_value=True)
        
        result = can_view_patients(self.doctor)
        self.assertTrue(result)
        self.doctor.has_perm.assert_called_once_with('patients.view_patient')

    def test_can_view_patients_without_permission(self):
        """Test can_view_patients with user lacking view permission"""
        self.doctor.has_perm = Mock(return_value=False)
        
        result = can_view_patients(self.doctor)
        self.assertFalse(result)

    def test_can_manage_events_with_permissions(self):
        """Test can_manage_events with user having all required permissions"""
        self.doctor.has_perm = Mock(return_value=True)
        
        result = can_manage_events(self.doctor)
        self.assertTrue(result)

    def test_can_view_events_with_permission(self):
        """Test can_view_events with user having view permission"""
        self.doctor.has_perm = Mock(return_value=True)
        
        result = can_view_events(self.doctor)
        self.assertTrue(result)
        self.doctor.has_perm.assert_called_once_with('events.view_event')


    def test_unauthenticated_user_all_functions(self):
        """Test all permission functions return False for unauthenticated users"""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False
        
        # Test all permission functions
        self.assertFalse(can_manage_patients(unauthenticated_user))
        self.assertFalse(can_view_patients(unauthenticated_user))
        self.assertFalse(can_manage_events(unauthenticated_user))
        self.assertFalse(can_view_events(unauthenticated_user))
