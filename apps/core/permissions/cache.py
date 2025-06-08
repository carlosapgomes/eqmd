"""
Caching utilities for the EquipeMed permission system.

This module provides caching mechanisms for expensive permission checks
to improve performance while maintaining security and data consistency.
"""

import hashlib
from typing import Any, Optional, Callable
from functools import wraps

from django.core.cache import cache
from django.conf import settings

from .constants import PERMISSION_CACHE_TIMEOUT, PERMISSION_CACHE_PREFIX


def generate_cache_key(user_id: int, permission_type: str, object_id: Optional[str] = None) -> str:
    """
    Generate a cache key for permission checks.
    
    Args:
        user_id: The user's ID
        permission_type: Type of permission being checked
        object_id: Optional object ID for object-level permissions
        
    Returns:
        str: Cache key for the permission check
    """
    key_parts = [PERMISSION_CACHE_PREFIX, str(user_id), permission_type]
    if object_id:
        key_parts.append(str(object_id))
    
    # Create a hash to ensure key length limits
    key_string = ':'.join(key_parts)
    if len(key_string) > 200:  # Django cache key limit is 250 chars
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{PERMISSION_CACHE_PREFIX}:hash:{key_hash}"
    
    return key_string


def cache_permission_result(
    permission_type: str,
    timeout: Optional[int] = None,
    use_object_id: bool = False
) -> Callable:
    """
    Decorator to cache permission check results.
    
    Args:
        permission_type: Type of permission being cached
        timeout: Cache timeout in seconds (defaults to PERMISSION_CACHE_TIMEOUT)
        use_object_id: Whether to include object ID in cache key
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(user: Any, obj: Any = None, *args, **kwargs) -> bool:
            # Skip caching for unauthenticated users
            if not getattr(user, 'is_authenticated', False):
                return func(user, obj, *args, **kwargs)
            
            # Generate cache key
            object_id = None
            if use_object_id and obj:
                object_id = getattr(obj, 'pk', None) or getattr(obj, 'id', None)
            
            cache_key = generate_cache_key(user.id, permission_type, object_id)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Calculate result and cache it
            result = func(user, obj, *args, **kwargs)
            cache_timeout = timeout or PERMISSION_CACHE_TIMEOUT
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_user_permissions(user_id: int) -> None:
    """
    Invalidate all cached permissions for a specific user.
    
    Args:
        user_id: The user's ID whose permissions should be invalidated
    """
    # Since we can't easily iterate over cache keys, we use a version-based approach
    version_key = f"{PERMISSION_CACHE_PREFIX}:user:{user_id}:version"
    current_version = cache.get(version_key, 0)
    cache.set(version_key, current_version + 1, None)  # Never expire version


def invalidate_object_permissions(object_type: str, object_id: str) -> None:
    """
    Invalidate cached permissions for a specific object.
    
    Args:
        object_type: Type of object (e.g., 'patient', 'event')
        object_id: ID of the object
    """
    # Use version-based invalidation for object permissions
    version_key = f"{PERMISSION_CACHE_PREFIX}:obj:{object_type}:{object_id}:version"
    current_version = cache.get(version_key, 0)
    cache.set(version_key, current_version + 1, None)  # Never expire version


def get_cache_stats() -> dict:
    """
    Get cache statistics for permission system.
    
    Returns:
        dict: Cache statistics including hit/miss ratios
    """
    # This is a basic implementation - in production you might want
    # to use more sophisticated cache monitoring
    stats_key = f"{PERMISSION_CACHE_PREFIX}:stats"
    stats = cache.get(stats_key, {'hits': 0, 'misses': 0})
    
    total_requests = stats['hits'] + stats['misses']
    hit_ratio = stats['hits'] / total_requests if total_requests > 0 else 0
    
    return {
        'hits': stats['hits'],
        'misses': stats['misses'],
        'total_requests': total_requests,
        'hit_ratio': hit_ratio,
    }


def clear_permission_cache() -> None:
    """
    Clear all permission-related cache entries.
    
    This is useful for testing or when you need to force a complete cache refresh.
    """
    # Since Django doesn't provide a way to delete by pattern,
    # we increment a global version number
    global_version_key = f"{PERMISSION_CACHE_PREFIX}:global_version"
    current_version = cache.get(global_version_key, 0)
    cache.set(global_version_key, current_version + 1, None)


def is_caching_enabled() -> bool:
    """
    Check if permission caching is enabled.
    
    Returns:
        bool: True if caching is enabled and available
    """
    try:
        # Test if cache is working
        test_key = f"{PERMISSION_CACHE_PREFIX}:test"
        cache.set(test_key, True, 1)
        result = cache.get(test_key)
        cache.delete(test_key)
        return result is True
    except Exception:
        return False
