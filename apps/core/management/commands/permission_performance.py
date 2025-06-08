"""
Management command for monitoring permission system performance.

This command provides tools for analyzing and optimizing the permission system.
"""

import time
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.cache import cache

from apps.core.permissions import (
    can_access_patient,
    can_manage_patients,
    get_cache_stats,
    clear_permission_cache,
    is_caching_enabled,
)
from apps.core.permissions.queries import (
    get_optimized_user_queryset,
    get_permission_summary_optimized,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Monitor and analyze permission system performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['stats', 'benchmark', 'clear-cache', 'test-queries'],
            default='stats',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID for testing (optional)'
        )
        
        parser.add_argument(
            '--iterations',
            type=int,
            default=100,
            help='Number of iterations for benchmarking'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'stats':
            self.show_cache_stats()
        elif action == 'benchmark':
            self.run_benchmark(options['iterations'], options.get('user_id'))
        elif action == 'clear-cache':
            self.clear_cache()
        elif action == 'test-queries':
            self.test_query_optimization(options.get('user_id'))
    
    def show_cache_stats(self):
        """Display cache statistics."""
        self.stdout.write(self.style.SUCCESS('Permission System Cache Statistics'))
        self.stdout.write('=' * 50)
        
        if not is_caching_enabled():
            self.stdout.write(self.style.WARNING('Caching is disabled'))
            return
        
        stats = get_cache_stats()
        
        self.stdout.write(f"Cache Hits: {stats['hits']}")
        self.stdout.write(f"Cache Misses: {stats['misses']}")
        self.stdout.write(f"Total Requests: {stats['total_requests']}")
        self.stdout.write(f"Hit Ratio: {stats['hit_ratio']:.2%}")
        
        if stats['hit_ratio'] > 0.7:
            self.stdout.write(self.style.SUCCESS('✓ Good cache performance'))
        elif stats['hit_ratio'] > 0.4:
            self.stdout.write(self.style.WARNING('⚠ Moderate cache performance'))
        else:
            self.stdout.write(self.style.ERROR('✗ Poor cache performance'))
    
    def run_benchmark(self, iterations, user_id=None):
        """Run performance benchmarks."""
        self.stdout.write(self.style.SUCCESS('Running Permission System Benchmarks'))
        self.stdout.write('=' * 50)
        
        # Get test user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f'User with ID {user_id} does not exist')
        else:
            user = User.objects.first()
            if not user:
                raise CommandError('No users found in database')
        
        self.stdout.write(f"Testing with user: {user.email}")
        self.stdout.write(f"Iterations: {iterations}")
        self.stdout.write()
        
        # Benchmark permission checks
        self._benchmark_permission_checks(user, iterations)
        
        # Benchmark with and without cache
        self._benchmark_cache_performance(user, iterations)
        
        # Benchmark query optimization
        self._benchmark_query_optimization(user, iterations)
    
    def _benchmark_permission_checks(self, user, iterations):
        """Benchmark basic permission checks."""
        self.stdout.write("Benchmarking permission checks...")
        
        # Create mock objects
        from unittest.mock import Mock
        mock_patient = Mock()
        mock_patient.pk = 'test-patient'
        mock_patient.status = 'outpatient'
        
        start_time = time.time()
        
        for _ in range(iterations):
            can_access_patient(user, mock_patient)
            can_manage_patients(user)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / (iterations * 2)  # 2 checks per iteration
        
        self.stdout.write(f"  Total time: {total_time:.4f}s")
        self.stdout.write(f"  Average per check: {avg_time:.6f}s")
        self.stdout.write(f"  Checks per second: {1/avg_time:.0f}")
        self.stdout.write()
    
    def _benchmark_cache_performance(self, user, iterations):
        """Benchmark cache performance."""
        self.stdout.write("Benchmarking cache performance...")
        
        if not is_caching_enabled():
            self.stdout.write(self.style.WARNING("  Caching disabled, skipping"))
            return
        
        # Clear cache and benchmark without cache
        clear_permission_cache()
        
        start_time = time.time()
        for _ in range(iterations):
            can_manage_patients(user)
        uncached_time = time.time() - start_time
        
        # Benchmark with cache (second run should be cached)
        start_time = time.time()
        for _ in range(iterations):
            can_manage_patients(user)
        cached_time = time.time() - start_time
        
        improvement = (uncached_time - cached_time) / uncached_time * 100
        
        self.stdout.write(f"  Uncached time: {uncached_time:.4f}s")
        self.stdout.write(f"  Cached time: {cached_time:.4f}s")
        self.stdout.write(f"  Improvement: {improvement:.1f}%")
        self.stdout.write()
    
    def _benchmark_query_optimization(self, user, iterations):
        """Benchmark query optimization."""
        self.stdout.write("Benchmarking query optimization...")
        
        # Count queries for optimized user loading
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
            
            for _ in range(min(iterations, 10)):  # Limit to avoid too many queries
                optimized_user = get_optimized_user_queryset().get(id=user.id)
                # Access related data
                list(optimized_user.groups.all())
            
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
        
        self.stdout.write(f"  Queries for {min(iterations, 10)} optimized user loads: {query_count}")
        self.stdout.write(f"  Average queries per load: {query_count / min(iterations, 10):.1f}")
        self.stdout.write()
    
    def clear_cache(self):
        """Clear permission cache."""
        self.stdout.write("Clearing permission cache...")
        clear_permission_cache()
        self.stdout.write(self.style.SUCCESS("Cache cleared successfully"))
    
    def test_query_optimization(self, user_id=None):
        """Test query optimization features."""
        self.stdout.write(self.style.SUCCESS('Testing Query Optimization'))
        self.stdout.write('=' * 50)
        
        # Get test user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f'User with ID {user_id} does not exist')
        else:
            user = User.objects.first()
            if not user:
                raise CommandError('No users found in database')
        
        # Test optimized user queryset
        self.stdout.write("Testing optimized user queryset...")
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
            
            optimized_user = get_optimized_user_queryset().get(id=user.id)
            groups = list(optimized_user.groups.all())
            permissions = list(optimized_user.user_permissions.all())
            
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
        
        self.stdout.write(f"  Queries used: {query_count}")
        self.stdout.write(f"  Groups loaded: {len(groups)}")
        self.stdout.write(f"  User permissions: {len(permissions)}")
        
        # Test permission summary
        self.stdout.write("\nTesting permission summary optimization...")
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
            
            summary = get_permission_summary_optimized(user)
            
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
        
        self.stdout.write(f"  Queries used: {query_count}")
        self.stdout.write(f"  Total permissions: {summary['permission_counts']['total_permissions']}")
        self.stdout.write(f"  Accessible models: {len(summary['accessible_models'])}")
        
        self.stdout.write(self.style.SUCCESS("\nQuery optimization test completed"))
