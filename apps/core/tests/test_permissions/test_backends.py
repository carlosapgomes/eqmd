"""
Tests for custom permission backend.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch

from apps.core.backends import EquipeMedPermissionBackend
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    NURSE,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
)

User = get_user_model()


class TestEquipeMedPermissionBackend(TestCase):
    """Test custom permission backend."""
    
    def setUp(self):
        self.backend = EquipeMedPermissionBackend()
        self.user = Mock()
        self.user.is_authenticated = True
        self.patient = Mock()
        self.patient._meta = Mock()
        self.patient._meta.model_name = 'patient'
        self.event = Mock()
        self.event._meta = Mock()
        self.event._meta.model_name = 'event'
    
    def test_authenticate_returns_none(self):
        """Test that authenticate method returns None."""
        result = self.backend.authenticate(None)
        self.assertIsNone(result)
    
    def test_has_perm_unauthenticated_user(self):
        """Test that unauthenticated users have no permissions."""
        self.user.is_authenticated = False
        result = self.backend.has_perm(self.user, 'patients.access_patient', self.patient)
        self.assertFalse(result)
    
    def test_has_perm_no_object(self):
        """Test that permissions without objects return False."""
        result = self.backend.has_perm(self.user, 'patients.access_patient', None)
        self.assertFalse(result)
    
    @patch('apps.core.backends.can_access_patient')
    def test_has_perm_patient_access(self, mock_can_access):
        """Test patient access permission."""
        mock_can_access.return_value = True
        result = self.backend.has_perm(self.user, 'patients.access_patient', self.patient)
        self.assertTrue(result)
        mock_can_access.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.backends.can_change_patient_personal_data')
    def test_has_perm_patient_personal_data_change(self, mock_can_change):
        """Test patient personal data change permission."""
        mock_can_change.return_value = True
        result = self.backend.has_perm(self.user, 'patients.change_patient_personal_data', self.patient)
        self.assertTrue(result)
        mock_can_change.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.backends.can_see_patient_in_search')
    def test_has_perm_patient_search_visibility(self, mock_can_see):
        """Test patient search visibility permission."""
        mock_can_see.return_value = True
        result = self.backend.has_perm(self.user, 'patients.see_patient_in_search', self.patient)
        self.assertTrue(result)
        mock_can_see.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.backends.can_edit_event')
    def test_has_perm_event_edit(self, mock_can_edit):
        """Test event edit permission."""
        mock_can_edit.return_value = True
        result = self.backend.has_perm(self.user, 'events.edit_event', self.event)
        self.assertTrue(result)
        mock_can_edit.assert_called_once_with(self.user, self.event)
    
    @patch('apps.core.backends.can_delete_event')
    def test_has_perm_event_delete(self, mock_can_delete):
        """Test event delete permission."""
        mock_can_delete.return_value = True
        result = self.backend.has_perm(self.user, 'events.delete_event', self.event)
        self.assertTrue(result)
        mock_can_delete.assert_called_once_with(self.user, self.event)
    
    def test_has_perm_unknown_permission(self):
        """Test that unknown permissions return False."""
        result = self.backend.has_perm(self.user, 'unknown.permission', self.patient)
        self.assertFalse(result)
    
    def test_has_perm_patient_status_change(self):
        """Test that patient status change permission returns False (requires new_status)."""
        result = self.backend.has_perm(self.user, 'patients.change_patient_status', self.patient)
        self.assertFalse(result)
    
    def test_has_module_perms_unauthenticated(self):
        """Test that unauthenticated users have no module permissions."""
        self.user.is_authenticated = False
        result = self.backend.has_module_perms(self.user, 'patients')
        self.assertFalse(result)
    
    def test_has_module_perms_authenticated(self):
        """Test that authenticated users have no module permissions (handled by default backend)."""
        result = self.backend.has_module_perms(self.user, 'patients')
        self.assertFalse(result)
    
    @patch('apps.core.backends.can_access_patient')
    @patch('apps.core.backends.can_change_patient_personal_data')
    @patch('apps.core.backends.can_see_patient_in_search')
    def test_get_user_permissions_patient(self, mock_can_see, mock_can_change, mock_can_access):
        """Test getting user permissions for patient object."""
        mock_can_access.return_value = True
        mock_can_change.return_value = True
        mock_can_see.return_value = True
        
        permissions = self.backend.get_user_permissions(self.user, self.patient)
        
        expected_permissions = {
            'patients.access_patient',
            'patients.change_patient_personal_data',
            'patients.see_patient_in_search',
        }
        self.assertEqual(permissions, expected_permissions)
    
    @patch('apps.core.backends.can_edit_event')
    @patch('apps.core.backends.can_delete_event')
    def test_get_user_permissions_event(self, mock_can_delete, mock_can_edit):
        """Test getting user permissions for event object."""
        mock_can_edit.return_value = True
        mock_can_delete.return_value = False
        
        permissions = self.backend.get_user_permissions(self.user, self.event)
        
        expected_permissions = {
            'events.edit_event',
        }
        self.assertEqual(permissions, expected_permissions)
    
    def test_get_user_permissions_unauthenticated(self):
        """Test that unauthenticated users get no permissions."""
        self.user.is_authenticated = False
        permissions = self.backend.get_user_permissions(self.user, self.patient)
        self.assertEqual(permissions, set())
    
    def test_get_user_permissions_no_object(self):
        """Test that no object returns empty permissions."""
        permissions = self.backend.get_user_permissions(self.user, None)
        self.assertEqual(permissions, set())
    
    def test_get_user_permissions_unknown_object(self):
        """Test that unknown object types return empty permissions."""
        unknown_obj = Mock()
        unknown_obj._meta = Mock()
        unknown_obj._meta.model_name = 'unknown'
        
        permissions = self.backend.get_user_permissions(self.user, unknown_obj)
        self.assertEqual(permissions, set())
    
    def test_get_group_permissions(self):
        """Test that group permissions return empty set."""
        permissions = self.backend.get_group_permissions(self.user, self.patient)
        self.assertEqual(permissions, set())
    
    def test_get_all_permissions(self):
        """Test that get_all_permissions returns same as get_user_permissions."""
        with patch.object(self.backend, 'get_user_permissions') as mock_get_user:
            mock_get_user.return_value = {'test.permission'}
            
            permissions = self.backend.get_all_permissions(self.user, self.patient)
            
            self.assertEqual(permissions, {'test.permission'})
            mock_get_user.assert_called_once_with(self.user, self.patient)
