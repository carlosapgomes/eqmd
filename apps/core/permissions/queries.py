"""
Query optimization utilities for the EquipeMed permission system.

This module provides optimized querysets and query utilities for
permission-related database operations to improve performance.
"""

from typing import Any, Optional
from django.db.models import QuerySet, Prefetch


def get_user_model_lazy():
    """Lazy import of user model to avoid Django setup issues."""
    from django.contrib.auth import get_user_model
    return get_user_model()


def get_optimized_user_queryset() -> QuerySet:
    """
    Get an optimized queryset for users with permission-related data.

    Returns:
        QuerySet: Optimized user queryset with prefetched groups and permissions
    """
    User = get_user_model_lazy()
    return User.objects.select_related(
        'userprofile'
    ).prefetch_related(
        'groups',
        'groups__permissions',
        'user_permissions'
    )


def get_user_with_permissions(user_id: int) -> Optional[Any]:
    """
    Get a user with optimized permission data loading.

    Args:
        user_id: The user's ID

    Returns:
        User object with optimized permission data or None
    """
    User = get_user_model_lazy()
    try:
        return get_optimized_user_queryset().get(id=user_id)
    except User.DoesNotExist:
        return None


def get_optimized_patient_queryset():
    """
    Get an optimized queryset for patients with permission-related data.
    
    Returns:
        QuerySet: Optimized patient queryset with related data
    """
    try:
        from apps.patients.models import Patient
        return Patient.objects.select_related(
            'created_by',
            'updated_by'
        ).prefetch_related(
            'tags',
            'tags__allowed_tag'
        )
    except ImportError:
        # Return empty queryset if patients app is not available
        return None


def get_optimized_event_queryset():
    """
    Get an optimized queryset for events with permission-related data.
    
    Returns:
        QuerySet: Optimized event queryset with related user and patient data
    """
    try:
        from apps.events.models import Event
        return Event.objects.select_related(
            'patient',
            'created_by',
            'updated_by'
        )
    except ImportError:
        # Return empty queryset if events app is not available
        return None


def get_optimized_hospital_queryset():
    """
    Get an optimized queryset for hospitals with permission-related data.
    
    Returns:
        QuerySet: Optimized hospital queryset with related data
    """
    try:
        from apps.hospitals.models import Hospital
        return Hospital.objects.select_related(
            'created_by',
            'updated_by'
        ).prefetch_related(
            'ward_set'
        )
    except ImportError:
        # Return empty queryset if hospitals app is not available
        return None


def get_patients_for_user(user: Any, limit: Optional[int] = None):
    """
    Get patients that a user can access with optimized queries.
    
    Args:
        user: The user requesting access
        limit: Optional limit on number of results
        
    Returns:
        QuerySet: Optimized queryset of accessible patients
    """
    queryset = get_optimized_patient_queryset()
    if queryset is None:
        return None
    
    # Apply permission-based filtering here
    # For now, we'll return all patients - this should be enhanced
    # with proper permission filtering based on hospital context
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def get_events_for_user(user: Any, limit: Optional[int] = None):
    """
    Get events that a user can access with optimized queries.
    
    Args:
        user: The user requesting access
        limit: Optional limit on number of results
        
    Returns:
        QuerySet: Optimized queryset of accessible events
    """
    queryset = get_optimized_event_queryset()
    if queryset is None:
        return None
    
    # Apply permission-based filtering
    # Filter by events created by the user or events for patients they can access
    queryset = queryset.filter(created_by=user)
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def get_hospitals_for_user(user: Any, limit: Optional[int] = None):
    """
    Get hospitals that a user can access with optimized queries.
    
    Args:
        user: The user requesting access
        limit: Optional limit on number of results
        
    Returns:
        QuerySet: Optimized queryset of accessible hospitals
    """
    queryset = get_optimized_hospital_queryset()
    if queryset is None:
        return None
    
    # For now, return all hospitals - this should be enhanced
    # with proper permission filtering based on user role
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def get_recent_patients_optimized(user: Any, limit: int = 5):
    """
    Get recent patients with optimized queries for dashboard widgets.
    
    Args:
        user: The user requesting data
        limit: Number of recent patients to return
        
    Returns:
        QuerySet: Optimized queryset of recent patients
    """
    queryset = get_optimized_patient_queryset()
    if queryset is None:
        return None
    
    return queryset.order_by('-created_at')[:limit]


def get_user_groups_optimized(user: Any):
    """
    Get user groups with optimized permission loading.
    
    Args:
        user: The user to get groups for
        
    Returns:
        QuerySet: Optimized queryset of user groups with permissions
    """
    if not user.is_authenticated:
        return None
    
    return user.groups.prefetch_related('permissions')


def count_user_permissions(user: Any) -> dict:
    """
    Count various permission types for a user with optimized queries.
    
    Args:
        user: The user to count permissions for
        
    Returns:
        dict: Dictionary with permission counts
    """
    if not user.is_authenticated:
        return {
            'total_permissions': 0,
            'group_permissions': 0,
            'user_permissions': 0,
            'groups_count': 0
        }
    
    # Use optimized user queryset
    optimized_user = get_user_with_permissions(user.id)
    if not optimized_user:
        return {
            'total_permissions': 0,
            'group_permissions': 0,
            'user_permissions': 0,
            'groups_count': 0
        }
    
    # Count permissions efficiently
    group_permissions = set()
    for group in optimized_user.groups.all():
        for perm in group.permissions.all():
            group_permissions.add(perm.codename)
    
    user_permissions = set(
        perm.codename for perm in optimized_user.user_permissions.all()
    )
    
    total_permissions = group_permissions.union(user_permissions)
    
    return {
        'total_permissions': len(total_permissions),
        'group_permissions': len(group_permissions),
        'user_permissions': len(user_permissions),
        'groups_count': optimized_user.groups.count()
    }


def get_permission_summary_optimized(user: Any) -> dict:
    """
    Get a comprehensive permission summary with optimized queries.
    
    Args:
        user: The user to get summary for
        
    Returns:
        dict: Comprehensive permission summary
    """
    if not user.is_authenticated:
        return {
            'user': None,
            'has_permissions': False,
            'permission_counts': {},
            'accessible_models': []
        }
    
    permission_counts = count_user_permissions(user)
    
    # Check access to main models
    accessible_models = []
    if user.has_perm('patients.view_patient'):
        accessible_models.append('patients')
    if user.has_perm('events.view_event'):
        accessible_models.append('events')
    if user.has_perm('hospitals.view_hospital'):
        accessible_models.append('hospitals')
    
    return {
        'user': user,
        'has_permissions': permission_counts['total_permissions'] > 0,
        'permission_counts': permission_counts,
        'accessible_models': accessible_models
    }
