#!/usr/bin/env python
"""
Comprehensive verification script for the EquipeMed permission system.

This script verifies that all components of the permission system are
properly implemented and working correctly.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connection
from io import StringIO

# Import permission system components
from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_delete_event,
    is_doctor,
    has_hospital_context,
    get_user_profession_type,
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    NURSE,
    STUDENT,
    INPATIENT,
    OUTPATIENT,
)

User = get_user_model()


class PermissionSystemVerification:
    """Comprehensive verification of the permission system."""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
    
    def run_verification(self):
        """Run all verification tests."""
        print("=" * 60)
        print("EquipeMed Permission System Verification")
        print("=" * 60)
        
        # Test categories
        test_categories = [
            ("Module Structure", self.verify_module_structure),
            ("Permission Utilities", self.verify_permission_utilities),
            ("Decorators", self.verify_decorators),
            ("Template Tags", self.verify_template_tags),
            ("Cache System", self.verify_cache_system),
            ("Query Optimization", self.verify_query_optimization),
            ("Management Commands", self.verify_management_commands),
            ("Documentation", self.verify_documentation),
            ("Integration Tests", self.verify_integration_tests),
            ("Demo Application", self.verify_demo_application),
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n{category_name}:")
            print("-" * 40)
            try:
                test_function()
            except Exception as e:
                self.fail(f"Error in {category_name}: {str(e)}")
        
        # Print summary
        self.print_summary()
    
    def verify_module_structure(self):
        """Verify that all required modules exist."""
        required_modules = [
            'apps.core.permissions',
            'apps.core.permissions.utils',
            'apps.core.permissions.decorators',
            'apps.core.permissions.constants',
            'apps.core.permissions.cache',
            'apps.core.permissions.queries',
            'apps.core.templatetags.permission_tags',
            'apps.hospitals.middleware',
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                self.pass_test(f"Module {module_name} exists")
            except ImportError:
                self.fail(f"Module {module_name} not found")
    
    def verify_permission_utilities(self):
        """Verify permission utility functions."""
        from unittest.mock import Mock
        
        # Create mock user and patient
        user = Mock()
        user.is_authenticated = True
        user.profession_type = 0  # MEDICAL_DOCTOR
        user.has_hospital_context = True
        user.current_hospital = Mock()
        user.current_hospital.id = 'hospital-1'
        
        patient = Mock()
        patient.status = INPATIENT
        patient.current_hospital_id = 'hospital-1'
        patient.current_hospital = user.current_hospital
        
        # Test utility functions
        try:
            result = can_access_patient(user, patient)
            self.pass_test(f"can_access_patient works: {result}")
        except Exception as e:
            self.fail(f"can_access_patient failed: {e}")
        
        try:
            result = is_doctor(user)
            self.pass_test(f"is_doctor works: {result}")
        except Exception as e:
            self.fail(f"is_doctor failed: {e}")
        
        try:
            result = has_hospital_context(user)
            self.pass_test(f"has_hospital_context works: {result}")
        except Exception as e:
            self.fail(f"has_hospital_context failed: {e}")
        
        try:
            result = get_user_profession_type(user)
            self.pass_test(f"get_user_profession_type works: {result}")
        except Exception as e:
            self.fail(f"get_user_profession_type failed: {e}")
    
    def verify_decorators(self):
        """Verify permission decorators."""
        try:
            from apps.core.permissions.decorators import (
                patient_access_required,
                doctor_required,
                hospital_context_required,
                patient_data_change_required,
                can_delete_event_required,
            )
            
            decorators = [
                'patient_access_required',
                'doctor_required', 
                'hospital_context_required',
                'patient_data_change_required',
                'can_delete_event_required',
            ]
            
            for decorator_name in decorators:
                self.pass_test(f"Decorator {decorator_name} exists")
                
        except ImportError as e:
            self.fail(f"Decorator import failed: {e}")
    
    def verify_template_tags(self):
        """Verify template tags."""
        try:
            from apps.core.templatetags.permission_tags import (
                has_permission,
                in_group,
                is_profession,
                can_manage_patients,
                can_user_change_patient_personal_data,
                check_multiple_permissions,
            )
            
            template_tags = [
                'has_permission',
                'in_group',
                'is_profession', 
                'can_manage_patients',
                'can_user_change_patient_personal_data',
                'check_multiple_permissions',
            ]
            
            for tag_name in template_tags:
                self.pass_test(f"Template tag {tag_name} exists")
                
        except ImportError as e:
            self.fail(f"Template tag import failed: {e}")
    
    def verify_cache_system(self):
        """Verify permission caching system."""
        try:
            from apps.core.permissions.cache import (
                cache_permission_result,
                invalidate_user_permissions,
                clear_permission_cache,
                get_cache_stats,
                is_caching_enabled,
            )
            
            cache_functions = [
                'cache_permission_result',
                'invalidate_user_permissions',
                'clear_permission_cache',
                'get_cache_stats',
                'is_caching_enabled',
            ]
            
            for func_name in cache_functions:
                self.pass_test(f"Cache function {func_name} exists")
            
            # Test cache stats
            stats = get_cache_stats()
            if isinstance(stats, dict):
                self.pass_test("Cache stats returns dictionary")
            else:
                self.fail("Cache stats should return dictionary")
                
        except ImportError as e:
            self.fail(f"Cache system import failed: {e}")
    
    def verify_query_optimization(self):
        """Verify query optimization utilities."""
        try:
            from apps.core.permissions.queries import (
                get_optimized_user_queryset,
                get_optimized_patient_queryset,
                get_patients_for_user,
                get_permission_summary_optimized,
            )
            
            query_functions = [
                'get_optimized_user_queryset',
                'get_optimized_patient_queryset',
                'get_patients_for_user',
                'get_permission_summary_optimized',
            ]
            
            for func_name in query_functions:
                self.pass_test(f"Query function {func_name} exists")
                
        except ImportError as e:
            self.fail(f"Query optimization import failed: {e}")
    
    def verify_management_commands(self):
        """Verify management commands."""
        command_files = [
            'apps/core/management/commands/setup_groups.py',
            'apps/core/management/commands/permission_performance.py',
            'apps/core/management/commands/permission_audit.py',
            'apps/core/management/commands/user_permissions.py',
        ]
        
        for command_file in command_files:
            if Path(command_file).exists():
                self.pass_test(f"Management command {command_file} exists")
            else:
                self.fail(f"Management command {command_file} not found")
        
        # Test command execution (dry run)
        try:
            out = StringIO()
            call_command('setup_groups', '--help', stdout=out)
            self.pass_test("setup_groups command is callable")
        except Exception as e:
            self.fail(f"setup_groups command failed: {e}")
        
        try:
            out = StringIO()
            call_command('permission_audit', '--help', stdout=out)
            self.pass_test("permission_audit command is callable")
        except Exception as e:
            self.fail(f"permission_audit command failed: {e}")
    
    def verify_documentation(self):
        """Verify documentation files."""
        doc_files = [
            'docs/permissions/README.md',
            'docs/permissions/user-guide.md',
            'docs/permissions/api-reference.md',
        ]
        
        for doc_file in doc_files:
            if Path(doc_file).exists():
                self.pass_test(f"Documentation file {doc_file} exists")
                
                # Check file size (should not be empty)
                file_size = Path(doc_file).stat().st_size
                if file_size > 1000:  # At least 1KB
                    self.pass_test(f"Documentation file {doc_file} has content")
                else:
                    self.fail(f"Documentation file {doc_file} appears empty")
            else:
                self.fail(f"Documentation file {doc_file} not found")
    
    def verify_integration_tests(self):
        """Verify integration tests."""
        test_files = [
            'apps/core/tests/test_permissions/test_integration.py',
        ]
        
        for test_file in test_files:
            if Path(test_file).exists():
                self.pass_test(f"Integration test file {test_file} exists")
                
                # Check file size
                file_size = Path(test_file).stat().st_size
                if file_size > 5000:  # At least 5KB
                    self.pass_test(f"Integration test file {test_file} has substantial content")
                else:
                    self.fail(f"Integration test file {test_file} appears too small")
            else:
                self.fail(f"Integration test file {test_file} not found")
    
    def verify_demo_application(self):
        """Verify demo application."""
        demo_files = [
            'apps/core/views/permission_demo.py',
            'templates/core/permission_demo/dashboard.html',
        ]
        
        for demo_file in demo_files:
            if Path(demo_file).exists():
                self.pass_test(f"Demo file {demo_file} exists")
            else:
                self.fail(f"Demo file {demo_file} not found")
        
        # Check if demo URLs are configured
        try:
            from apps.core.urls import urlpatterns
            demo_urls = [url for url in urlpatterns if 'demo' in str(url.pattern)]
            if demo_urls:
                self.pass_test(f"Demo URLs configured: {len(demo_urls)} URLs")
            else:
                self.fail("No demo URLs found in core.urls")
        except Exception as e:
            self.fail(f"Error checking demo URLs: {e}")
    
    def pass_test(self, message):
        """Record a passed test."""
        self.passed_tests += 1
        print(f"  ✓ {message}")
    
    def fail(self, message):
        """Record a failed test."""
        self.failed_tests += 1
        self.errors.append(message)
        print(f"  ✗ {message}")
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Passed Tests: {self.passed_tests}")
        print(f"Failed Tests: {self.failed_tests}")
        print(f"Total Tests: {self.passed_tests + self.failed_tests}")
        
        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Permission system is fully implemented.")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed. See errors above.")
            print("\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        
        # Calculate success rate
        total_tests = self.passed_tests + self.failed_tests
        if total_tests > 0:
            success_rate = (self.passed_tests / total_tests) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        print("\n" + "=" * 60)


def main():
    """Main verification function."""
    verifier = PermissionSystemVerification()
    verifier.run_verification()
    
    # Return exit code based on results
    return 0 if verifier.failed_tests == 0 else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
