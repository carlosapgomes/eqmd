"""
Cache utility functions for dashboard and ward mapping data
"""
from django.utils import timezone
from apps.core.models import DashboardCache, WardMappingCache
from apps.core.utils.text import normalize_text_for_search
from datetime import timedelta
import uuid


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


def apply_client_side_filters(ward_data, filters):
    """Apply filters to ward data on the client side"""
    if not filters:
        # Default behavior: hide empty wards unless explicitly requested
        return [ward_info for ward_info in ward_data if ward_info['patient_count'] > 0]
        
    filtered_data = []
    
    for ward_info in ward_data:
        # Ward filter
        if filters.get('ward') and str(ward_info['ward']['id']) != str(filters['ward']):
            continue
            
        # If we're filtering by tag or search, we need to filter patients within each ward
        if filters.get('tag') or filters.get('q'):
            filtered_patients = []
            
            for patient_info in ward_info['patients']:
                # Search filter
                if filters.get('q'):
                    search_term = normalize_text_for_search(filters['q'])
                    patient_name = normalize_text_for_search(
                        patient_info['patient']['name']
                    )
                    patient_bed = normalize_text_for_search(patient_info['bed'])
                    if search_term not in patient_name and search_term not in patient_bed:
                        continue
                
                # Tag filter
                if filters.get('tag'):
                    patient_tags = [str(tag['allowed_tag']['id']) for tag in patient_info['tags']]
                    if str(filters['tag']) not in patient_tags:
                        continue
                
                filtered_patients.append(patient_info)
            
            # Sort filtered patients by bed
            filtered_patients.sort(key=lambda p: p['bed'])
            
            # Update ward info with filtered patients
            ward_info_copy = ward_info.copy()
            ward_info_copy['patients'] = filtered_patients
            ward_info_copy['patient_count'] = len(filtered_patients)
            
            # Only include wards that have patients after filtering (unless showing empty wards)
            if filtered_patients or (not (filters.get('tag') or filters.get('q')) and filters.get('show_empty_wards')):
                filtered_data.append(ward_info_copy)
        else:
            # If not filtering by tag/search, apply empty ward filter
            if filters.get('show_empty_wards', False) or ward_info['patient_count'] > 0:
                filtered_data.append(ward_info)
    
    return filtered_data


def _project_ward_patients(ward_data, *, viewer):
    """Rebuild cached ward rows with current, requester-visible tag metadata.

    The shared payload is only a structural base (ward, bed, patient id). Tag
    names, colours, identifiers and associations are re-read from the current
    catalogue and projected for this viewer (design D7), so revocation and
    reclassification are effective on the very next request. The cached
    structure itself is never mutated.
    """
    from apps.patients.services import tag_projection

    patient_ids = [
        patient_info["patient"]["pk"]
        for ward_info in ward_data
        for patient_info in ward_info.get("patients", [])
    ]
    # Cached identifiers are JSON strings; the projection keys by patient UUID.
    ids_by_cached_key = {
        str(raw_id): uuid.UUID(str(raw_id))
        for raw_id in patient_ids
        if str(raw_id).strip()
    }
    badges_by_patient = tag_projection.patient_tag_badges_by_patient(
        viewer, list(set(ids_by_cached_key.values()))
    )
    projected = []
    for ward_info in ward_data:
        ward_copy = dict(ward_info)
        patients = []
        for patient_info in ward_info.get("patients", []):
            patient_copy = dict(patient_info)
            patient_id = ids_by_cached_key.get(str(patient_info["patient"]["pk"]))
            patient_copy["tags"] = [
                {
                    "allowed_tag": {
                        "id": badge.tag_id,
                        "name": badge.name,
                        "color": badge.color,
                    },
                    "state": badge.state,
                    "state_label": badge.state_label,
                }
                for badge in badges_by_patient.get(patient_id, [])
            ]
            patients.append(patient_copy)
        ward_copy["patients"] = patients
        projected.append(ward_copy)
    return projected


def get_cached_ward_mapping(filters=None, *, viewer=None):
    """Get ward mapping from cache with optional filtering.

    ``viewer`` is the requesting user: cached tag metadata is replaced by a
    requester-aware projection before any filtering or serialization. Without
    a viewer only public tag metadata is readable.
    """
    try:
        # Get full ward data from cache
        ward_cache = WardMappingCache.objects.get(cache_key='ward_mapping_full')
        filter_cache = WardMappingCache.objects.get(cache_key='ward_filters')
        
        # Check staleness (20 minutes max)
        if (timezone.now() - ward_cache.updated_at).total_seconds() < 1200:
            # Reproject before filtering: the cached tag payload is not an
            # authorization decision and stale labels are never trusted.
            projected_ward_data = _project_ward_patients(
                ward_cache.ward_data['ward_data'], viewer=viewer
            )
            
            # Apply filters if provided
            filtered_ward_data = projected_ward_data
            if filters:
                filtered_ward_data = apply_client_side_filters(
                    projected_ward_data, filters
                )
            
            return {
                'ward_data': filtered_ward_data,
                'total_patients': ward_cache.ward_data['total_patients'],
                'total_wards': ward_cache.ward_data['total_wards'],
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

    return tag_projection.map_tag_options(viewer)


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