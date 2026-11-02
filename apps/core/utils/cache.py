"""
Cache utility functions for dashboard and ward mapping data
"""
from django.utils import timezone

from apps.core.models import DashboardCache, WardMappingCache


def get_cached_dashboard_stats():
    """Get dashboard stats from cache with fallback"""
    try:
        # Try to get from cache
        stats_cache = DashboardCache.objects.get(key='patient_counts')
        recent_cache = DashboardCache.objects.get(key='recent_patients')
        
        # Check staleness (20 minutes max)
        if (timezone.now() - stats_cache.updated_at).total_seconds() < 1200:
            return {
                'stats': stats_cache.data,
                'recent_patients': recent_cache.data['patients'],
                'from_cache': True
            }
    except DashboardCache.DoesNotExist:
        pass
    
    # Fallback to real-time (show loading message)
    return {
        'stats': {'total_patients': '...', 'inpatients': '...', 'outpatients': '...'},
        'recent_patients': [],
        'from_cache': False,
        'updating': True
    }


def get_cached_ward_mapping(filters=None, *, viewer=None):
    """Get ward mapping from cache with the request filters applied.

    ``viewer`` is the requesting user: cached tag metadata is replaced by a
    requester-aware projection before any filtering or serialization. Without
    a viewer only public tag metadata is readable. ``filters`` is a
    ``ward_tag_overlay.WardMapFilters``; page totals are recomputed from the
    rows that survive it, never from the shared global counts.
    """
    from apps.patients.services import ward_tag_overlay

    try:
        # Get full ward data from cache
        ward_cache = WardMappingCache.objects.get(cache_key='ward_mapping_full')
        filter_cache = WardMappingCache.objects.get(cache_key='ward_filters')
        
        # Check staleness (20 minutes max)
        if (timezone.now() - ward_cache.updated_at).total_seconds() < 1200:
            # Reproject before filtering: the cached tag payload is not an
            # authorization decision and stale labels are never trusted.
            ward_data = ward_tag_overlay.project_patients(
                ward_cache.ward_data['ward_data'], actor=viewer
            )
            if filters is not None:
                ward_data = ward_tag_overlay.apply_filters(ward_data, filters)
            totals = ward_tag_overlay.map_totals(ward_data)

            return {
                'ward_data': ward_data,
                'total_patients': totals['total_patients'],
                'total_wards': totals['total_wards'],
                'all_wards': filter_cache.ward_data['all_wards'],
                'available_tags': _project_available_tags(viewer),
                'from_cache': True
            }
    except WardMappingCache.DoesNotExist:
        pass
    
    # Fallback - show updating message
    return {
        'ward_data': [],
        'total_patients': 0,
        'total_wards': 0,
        'all_wards': [],
        'available_tags': _project_available_tags(viewer),
        'from_cache': False,
        'updating': True
    }


def _project_available_tags(viewer):
    """Return the tag selector options this viewer may currently read."""
    from apps.patients.services import tag_projection

    return tag_projection.filter_tag_options(viewer)


def get_cache_status():
    """Get status of all caches for monitoring"""
    status = {
        'dashboard_stats': {'exists': False, 'age_seconds': None, 'stale': False},
        'recent_patients': {'exists': False, 'age_seconds': None, 'stale': False},
        'ward_mapping': {'exists': False, 'age_seconds': None, 'stale': False},
        'ward_filters': {'exists': False, 'age_seconds': None, 'stale': False},
    }
    
    now = timezone.now()
    
    # Check dashboard caches
    try:
        stats_cache = DashboardCache.objects.get(key='patient_counts')
        age = (now - stats_cache.updated_at).total_seconds()
        status['dashboard_stats'] = {
            'exists': True,
            'age_seconds': age,
            'stale': age > 1200  # 20 minutes
        }
    except DashboardCache.DoesNotExist:
        pass
    
    try:
        recent_cache = DashboardCache.objects.get(key='recent_patients')
        age = (now - recent_cache.updated_at).total_seconds()
        status['recent_patients'] = {
            'exists': True,
            'age_seconds': age,
            'stale': age > 1200  # 20 minutes
        }
    except DashboardCache.DoesNotExist:
        pass
    
    # Check ward mapping caches
    try:
        ward_cache = WardMappingCache.objects.get(cache_key='ward_mapping_full')
        age = (now - ward_cache.updated_at).total_seconds()
        status['ward_mapping'] = {
            'exists': True,
            'age_seconds': age,
            'stale': age > 1200  # 20 minutes
        }
    except WardMappingCache.DoesNotExist:
        pass
    
    try:
        filter_cache = WardMappingCache.objects.get(cache_key='ward_filters')
        age = (now - filter_cache.updated_at).total_seconds()
        status['ward_filters'] = {
            'exists': True,
            'age_seconds': age,
            'stale': age > 1200  # 20 minutes
        }
    except WardMappingCache.DoesNotExist:
        pass
    
    return status