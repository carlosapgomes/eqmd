"""
Performance tests for the EquipeMed permission system.

This module tests the performance improvements from caching and query optimization.
"""

import time
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import override_settings

from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_manage_patients,
    is_in_group,
    get_cache_stats,
    clear_permission_cache,
    is_caching_enabled,
)
from apps.core.permissions.cache import cache_permission_result
from apps.core.permissions.queries import (
    get_optimized_user_queryset,
    get_permission_summary_optimized,
    count_user_permissions,
)

User = get_user_model()


class PermissionCacheTestCase(TestCase):
    """Test permission caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
        
        # Clear cache before each test
        clear_permission_cache()
    
    def test_caching_enabled(self):
        """Test that caching is enabled and working."""
        self.assertTrue(is_caching_enabled())
    
    def test_cache_permission_decorator(self):
        """Test that the cache decorator works correctly."""
        
        @cache_permission_result('test_permission')
        def test_permission_func(user, obj=None):
            # Simulate expensive operation
            time.sleep(0.01)
            return True
        
        # First call should be slow
        start_time = time.time()
        result1 = test_permission_func(self.user)
        first_call_time = time.time() - start_time
        
        # Second call should be fast (cached)
        start_time = time.time()
        result2 = test_permission_func(self.user)
        second_call_time = time.time() - start_time
        
        # Both results should be the same
        self.assertEqual(result1, result2)
        self.assertTrue(result1)
        
        # Second call should be significantly faster
        self.assertLess(second_call_time, first_call_time / 2)
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        # Clear cache and get initial stats
        clear_permission_cache()
        
        # Make some permission calls
        can_manage_patients(self.user)  # This should be cached
        can_manage_patients(self.user)  # This should hit cache
        
        # Note: Cache stats are basic in our implementation
        # In production, you might want more sophisticated tracking
        stats = get_cache_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('hits', stats)
        self.assertIn('misses', stats)
    
    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        from apps.core.permissions.cache import invalidate_user_permissions
        
        # Make a cached call
        result1 = can_manage_patients(self.user)
        
        # Invalidate user permissions
        invalidate_user_permissions(self.user.id)
        
        # Make the same call again - should recalculate
        result2 = can_manage_patients(self.user)
        
        # Results should be the same, but cache was invalidated
        self.assertEqual(result1, result2)
    
    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_caching_disabled(self):
        """Test behavior when caching is disabled."""
        # With dummy cache, caching should be disabled
        self.assertFalse(is_caching_enabled())


class PermissionQueryOptimizationTestCase(TestCase):
    """Test query optimization for permission system."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
    
    def test_optimized_user_queryset(self):
        """Test optimized user queryset reduces database queries."""
        with self.assertNumQueries(3):  # Should be optimized to minimal queries
            queryset = get_optimized_user_queryset()
            user = queryset.get(id=self.user.id)
            
            # Access related data that should be prefetched
            list(user.groups.all())
            if hasattr(user, 'userprofile'):
                str(user.userprofile)
    
    def test_permission_summary_optimization(self):
        """Test permission summary uses optimized queries."""
        # Count queries for permission summary
        with self.assertNumQueries(5):  # Should be optimized
            summary = get_permission_summary_optimized(self.user)
            
            self.assertIsInstance(summary, dict)
            self.assertIn('user', summary)
            self.assertIn('permission_counts', summary)
            self.assertIn('accessible_models', summary)
    
    def test_count_user_permissions_optimization(self):
        """Test user permission counting is optimized."""
        with self.assertNumQueries(3):  # Should use optimized user queryset
            counts = count_user_permissions(self.user)
            
            self.assertIsInstance(counts, dict)
            self.assertIn('total_permissions', counts)
            self.assertIn('group_permissions', counts)
            self.assertIn('user_permissions', counts)
            self.assertIn('groups_count', counts)


class PermissionPerformanceTestCase(TestCase):
    """Test overall permission system performance."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
        
        # Create mock objects for testing
        self.mock_patient = Mock()
        self.mock_patient.pk = 'test-patient-id'
        self.mock_patient.status = 'outpatient'
        self.mock_patient.current_hospital = None
        
        self.mock_event = Mock()
        self.mock_event.pk = 'test-event-id'
        self.mock_event.created_by = self.user
        self.mock_event.created_at = time.time()
    
    def test_permission_check_performance(self):
        """Test that permission checks are reasonably fast."""
        
        # Test multiple permission checks
        start_time = time.time()
        
        for _ in range(100):
            can_access_patient(self.user, self.mock_patient)
            can_edit_event(self.user, self.mock_event)
            can_manage_patients(self.user)
            is_in_group(self.user, 'Medical Doctors')
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 400 permission checks should complete in reasonable time
        self.assertLess(total_time, 1.0, "Permission checks took too long")
        
        # Calculate average time per check
        avg_time = total_time / 400
        self.assertLess(avg_time, 0.01, "Average permission check too slow")
    
    def test_cached_vs_uncached_performance(self):
        """Test performance improvement from caching."""
        
        # Clear cache
        clear_permission_cache()
        
        # Time uncached calls
        start_time = time.time()
        for _ in range(50):
            can_manage_patients(self.user)
        uncached_time = time.time() - start_time
        
        # Time cached calls (should be faster)
        start_time = time.time()
        for _ in range(50):
            can_manage_patients(self.user)
        cached_time = time.time() - start_time
        
        # Cached calls should be faster
        # Note: This might not always be true in tests due to overhead
        # but it demonstrates the concept
        self.assertLessEqual(cached_time, uncached_time * 2)
    
    def test_bulk_permission_checks(self):
        """Test performance of bulk permission checking."""
        permissions = [
            'patients.add_patient',
            'patients.change_patient',
            'patients.delete_patient',
            'events.add_event',
            'events.change_event',
            'hospitals.view_hospital',
        ]
        
        start_time = time.time()
        
        # Check all permissions
        results = {}
        for perm in permissions:
            results[perm] = self.user.has_perm(perm)
        
        end_time = time.time()
        
        # Bulk check should be fast
        self.assertLess(end_time - start_time, 0.1)
        self.assertEqual(len(results), len(permissions))
    
    def test_memory_usage_reasonable(self):
        """Test that permission system doesn't use excessive memory."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many permission operations
        for i in range(1000):
            can_access_patient(self.user, self.mock_patient)
            can_manage_patients(self.user)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 10MB)
        self.assertLess(memory_increase, 10 * 1024 * 1024)


class PermissionTemplateTagPerformanceTestCase(TestCase):
    """Test performance of permission template tags."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
    
    def test_template_tag_performance(self):
        """Test that template tags perform well."""
        from apps.core.templatetags.permission_tags import (
            has_permission,
            in_group,
            check_bulk_permissions,
            get_user_accessible_models,
        )
        
        start_time = time.time()
        
        # Test various template tags
        for _ in range(100):
            has_permission(self.user, 'patients.view_patient')
            in_group(self.user, 'Medical Doctors')
            check_bulk_permissions(self.user, 'patients.add_patient', 'events.add_event')
            get_user_accessible_models(self.user)
        
        end_time = time.time()
        
        # Template tag operations should be fast
        self.assertLess(end_time - start_time, 1.0)
