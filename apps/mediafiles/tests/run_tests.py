#!/usr/bin/env python3
"""
Test runner script for the mediafiles app.
This script provides convenient ways to run different test suites.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and print the result"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Return code: {result.returncode}")
    return result.returncode == 0


def main():
    """Main test runner function"""
    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    os.chdir(project_root)
    
    print(f"Running tests from: {os.getcwd()}")
    
    # Test commands to run
    test_commands = [
        # Run all mediafiles tests
        ("uv run python manage.py test apps.mediafiles.tests", "All MediaFiles Tests"),
        
        # Run specific test modules
        ("uv run python manage.py test apps.mediafiles.tests.test_models", "Model Tests"),
        ("uv run python manage.py test apps.mediafiles.tests.test_utils", "Utility Tests"),
        ("uv run python manage.py test apps.mediafiles.tests.test_views", "View Tests"),
        ("uv run python manage.py test apps.mediafiles.tests.test_forms", "Form Tests"),
        ("uv run python manage.py test apps.mediafiles.tests.test_security", "Security Tests"),
        ("uv run python manage.py test apps.mediafiles.tests.test_validators", "Validator Tests"),
        
        # Run Django checks
        ("uv run python manage.py check", "Django System Checks"),
        
        # Check for missing migrations
        ("uv run python manage.py makemigrations --dry-run", "Check for Missing Migrations"),
    ]
    
    # Run all tests
    results = []
    for command, description in test_commands:
        success = run_command(command, description)
        results.append((description, success))
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    for description, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{description:<40} {status}")
    
    # Overall result
    all_passed = all(success for _, success in results)
    overall_status = "ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"
    print(f"\n{overall_status}")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
