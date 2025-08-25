"""
Cache utility functions for dashboard and ward mapping data
"""
from django.utils import timezone
from apps.core.models import DashboardCache, WardMappingCache
from datetime import timedelta


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
        return ward_data
        
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
                    search_term = filters['q'].lower()
                    if (search_term not in patient_info['patient']['name'].lower() and
                        search_term not in patient_info['bed'].lower()):
                        continue
                
                # Tag filter
                if filters.get('tag'):
                    patient_tags = [str(tag['allowed_tag']['id']) for tag in patient_info['tags']]
                    if str(filters['tag']) not in patient_tags:
                        continue
                
                filtered_patients.append(patient_info)
            
            # Update ward info with filtered patients
            ward_info_copy = ward_info.copy()
            ward_info_copy['patients'] = filtered_patients
            ward_info_copy['patient_count'] = len(filtered_patients)
            
            # Only include wards that have patients after filtering
            if filtered_patients or not (filters.get('tag') or filters.get('q')):
                filtered_data.append(ward_info_copy)
        else:
            filtered_data.append(ward_info)
    
    return filtered_data


def get_cached_ward_mapping(filters=None):
    """Get ward mapping from cache with optional filtering"""
    try:
        # Get full ward data from cache
        ward_cache = WardMappingCache.objects.get(cache_key='ward_mapping_full')
        filter_cache = WardMappingCache.objects.get(cache_key='ward_filters')
        
        # Check staleness (20 minutes max)
        if (timezone.now() - ward_cache.updated_at).total_seconds() < 1200:
            ward_data = ward_cache.ward_data
            
            # Apply filters if provided
            filtered_ward_data = ward_data['ward_data']
            if filters:
                filtered_ward_data = apply_client_side_filters(ward_data['ward_data'], filters)
            
            return {
                'ward_data': filtered_ward_data,
                'total_patients': ward_data['total_patients'],
                'total_wards': ward_data['total_wards'],
                'all_wards': filter_cache.ward_data['all_wards'],
                'available_tags': filter_cache.ward_data['available_tags'],
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
        'available_tags': [],
        'from_cache': False,
        'updating': True
    }


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