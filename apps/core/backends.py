"""
Custom permission backend for EquipeMed application.

This module provides a custom permission backend that integrates with Django's
permission system to provide object-level permissions for the EquipeMed platform.
"""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from typing import Any, Optional

from .permissions import (
    can_access_patient,
    can_edit_event,
    can_delete_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_see_patient_in_search,
)

User = get_user_model()


class EquipeMedPermissionBackend(BaseBackend):
    """
    Custom permission backend for EquipeMed object-level permissions.
    
    This backend provides object-level permission checking that integrates
    with Django's permission system. It handles permissions for:
    - Patient access and data modification
    - Event editing and deletion
    - Hospital context-based permissions
    """
    
    def authenticate(self, request, **kwargs):
        """
        This backend does not handle authentication.
        """
        return None
    
    def has_perm(self, user_obj: Any, perm: str, obj: Optional[Any] = None) -> bool:
        """
        Check if user has a specific permission on an object.
        
        Args:
            user_obj: The user requesting permission
            perm: Permission string (e.g., 'patients.access_patient')
            obj: The object to check permission against (optional)
            
        Returns:
            bool: True if permission is granted, False otherwise
        """
        if not user_obj.is_authenticated:
            return False
        
        # If no object is provided, fall back to Django's default permission system
        if obj is None:
            return False
        
        # Handle patient-related permissions
        if perm == 'patients.access_patient':
            return can_access_patient(user_obj, obj)
        
        elif perm == 'patients.change_patient_status':
            # This requires a new_status parameter, so we can't handle it here
            # Views should use the utility function directly
            return False
        
        elif perm == 'patients.change_patient_personal_data':
            return can_change_patient_personal_data(user_obj, obj)
        
        elif perm == 'patients.see_patient_in_search':
            return can_see_patient_in_search(user_obj, obj)
        
        # Handle event-related permissions
        elif perm == 'events.edit_event':
            return can_edit_event(user_obj, obj)
        
        elif perm == 'events.delete_event':
            return can_delete_event(user_obj, obj)
        
        # For other permissions, return False (let Django's default backend handle them)
        return False
    
    def has_module_perms(self, user_obj: Any, app_label: str) -> bool:
        """
        Check if user has any permissions in the given app.
        
        Args:
            user_obj: The user to check
            app_label: The app label (e.g., 'patients', 'events')
            
        Returns:
            bool: True if user has any permissions in the app, False otherwise
        """
        if not user_obj.is_authenticated:
            return False
        
        # Let Django's default backend handle module permissions
        return False
    
    def get_user_permissions(self, user_obj: Any, obj: Optional[Any] = None) -> set:
        """
        Get all permissions for a user on a specific object.
        
        Args:
            user_obj: The user to get permissions for
            obj: The object to check permissions against (optional)
            
        Returns:
            set: Set of permission strings
        """
        if not user_obj.is_authenticated:
            return set()
        
        permissions = set()
        
        if obj is None:
            return permissions
        
        # Check patient permissions
        if hasattr(obj, '_meta') and obj._meta.model_name == 'patient':
            if can_access_patient(user_obj, obj):
                permissions.add('patients.access_patient')
            
            if can_change_patient_personal_data(user_obj, obj):
                permissions.add('patients.change_patient_personal_data')
            
            if can_see_patient_in_search(user_obj, obj):
                permissions.add('patients.see_patient_in_search')
        
        # Check event permissions
        elif hasattr(obj, '_meta') and obj._meta.model_name == 'event':
            if can_edit_event(user_obj, obj):
                permissions.add('events.edit_event')
            
            if can_delete_event(user_obj, obj):
                permissions.add('events.delete_event')
        
        return permissions
    
    def get_group_permissions(self, user_obj: Any, obj: Optional[Any] = None) -> set:
        """
        Get all group permissions for a user on a specific object.
        
        Args:
            user_obj: The user to get permissions for
            obj: The object to check permissions against (optional)
            
        Returns:
            set: Set of permission strings from groups
        """
        # This backend doesn't handle group permissions for objects
        # Let Django's default backend handle group permissions
        return set()
    
    def get_all_permissions(self, user_obj: Any, obj: Optional[Any] = None) -> set:
        """
        Get all permissions for a user on a specific object.
        
        Args:
            user_obj: The user to get permissions for
            obj: The object to check permissions against (optional)
            
        Returns:
            set: Set of all permission strings
        """
        return self.get_user_permissions(user_obj, obj)
