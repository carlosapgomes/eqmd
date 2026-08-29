"""
Tests for management commands.
"""

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from io import StringIO


class SetupGroupsCommandTestCase(TestCase):
    def test_setup_groups_command_creates_groups(self):
        """Test that setup_groups command creates all required groups"""
        # Ensure no groups exist initially
        Group.objects.all().delete()
        
        # Run the command
        out = StringIO()
        call_command('setup_groups', stdout=out)
        
        # Check that all groups were created
        expected_groups = [
            'Medical Doctors',
            'Residents',
            'Nurses',
            'Physiotherapists',
            'Students',
        ]
        
        for group_name in expected_groups:
            self.assertTrue(
                Group.objects.filter(name=group_name).exists(),
                f"Group '{group_name}' was not created"
            )
        
        # Check output
        output = out.getvalue()
        self.assertIn('Successfully set up all permission groups', output)

    def test_setup_groups_command_idempotent(self):
        """Test that setup_groups command can be run multiple times safely"""
        # Run the command twice
        call_command('setup_groups', verbosity=0)
        initial_group_count = Group.objects.count()
        
        call_command('setup_groups', verbosity=0)
        final_group_count = Group.objects.count()
        
        # Group count should remain the same
        self.assertEqual(initial_group_count, final_group_count)

    def test_setup_groups_command_with_force(self):
        """Test that setup_groups command with --force removes and recreates groups"""
        # Create a group first
        test_group = Group.objects.create(name='Medical Doctors')
        test_group.permissions.add(Permission.objects.first())
        initial_permission_count = test_group.permissions.count()
        
        # Run command with force
        out = StringIO()
        call_command('setup_groups', '--force', stdout=out)
        
        # Check that group was recreated (permissions should be reset)
        recreated_group = Group.objects.get(name='Medical Doctors')
        self.assertNotEqual(recreated_group.id, test_group.id)
        
        # Check output
        output = out.getvalue()
        self.assertIn('Removing existing groups', output)
        self.assertIn('Removed group: Medical Doctors', output)

    def test_setup_groups_assigns_permissions_to_medical_doctors(self):
        """Test that Medical Doctors group gets clinical permissions only.

        Since the security refactor, medical staff receive ONLY the curated
        clinical permission set: key clinical permissions are granted and no
        ADMIN_ONLY_PERMISSIONS entry leaks into the group.
        """
        from apps.core.permissions.permission_categories import is_admin_permission

        call_command('setup_groups', verbosity=0)
        
        medical_doctors_group = Group.objects.get(name='Medical Doctors')
        
        # Medical doctors should have full clinical permissions
        clinical_codenames = {
            'patients.add_patient',
            'patients.change_patient',
            'patients.delete_patient',
            'events.add_event',
            'events.change_event',
            'dailynotes.add_dailynote',
            'historyandphysicals.add_historyandphysical',
            'outpatientprescriptions.add_outpatientprescription',
            'mediafiles.add_photo',
            'pdf_forms.add_pdfformsubmission',
        }
        group_codenames = {
            f'{perm.content_type.app_label}.{perm.codename}'
            for perm in medical_doctors_group.permissions.all()
        }
        self.assertTrue(
            clinical_codenames.issubset(group_codenames),
            f'Missing clinical permissions: {clinical_codenames - group_codenames}'
        )

        # No administrative permission may be assigned to medical staff
        for perm in medical_doctors_group.permissions.all():
            perm_codename = f'{perm.content_type.app_label}.{perm.codename}'
            self.assertFalse(
                is_admin_permission(perm_codename),
                f'Medical Doctors has admin permission: {perm_codename}'
            )

    def test_setup_groups_assigns_limited_permissions_to_students(self):
        """Test that Students group gets only view permissions"""
        call_command('setup_groups', verbosity=0)
        
        students_group = Group.objects.get(name='Students')
        
        # Students should have fewer permissions than medical doctors
        medical_doctors_group = Group.objects.get(name='Medical Doctors')
        
        self.assertLess(
            students_group.permissions.count(),
            medical_doctors_group.permissions.count()
        )
        
        # All student permissions should be view permissions, except the
        # documented supervised-learning additions (simple notes and wound/
        # surgery media documentation) granted by setup_groups.
        allowed_non_view = {
            'add_simplenote',
            'change_simplenote',
            'add_photo',
            'add_photoseries',
        }
        student_permissions = students_group.permissions.all()
        for permission in student_permissions:
            codename = permission.codename
            if codename in allowed_non_view:
                continue
            self.assertTrue(
                codename.startswith('view_'),
                f"Student has non-view permission: {codename}"
            )

    def test_setup_groups_handles_missing_apps(self):
        """Test that setup_groups handles missing apps gracefully"""
        # This test ensures the command doesn't fail if some apps are not available
        out = StringIO()
        call_command('setup_groups', stdout=out)
        
        # Command should complete successfully
        output = out.getvalue()
        self.assertIn('Successfully set up all permission groups', output)

    def test_setup_groups_creates_correct_group_structure(self):
        """Test that all expected groups are created with correct structure"""
        call_command('setup_groups', verbosity=0)
        
        # Check that all expected groups exist
        expected_groups = {
            'Medical Doctors': 'Full permissions',
            'Residents': 'Patient and event permissions',
            'Nurses': 'Limited patient permissions',
            'Physiotherapists': 'Patient and event permissions',
            'Students': 'View-only permissions',
        }
        
        for group_name in expected_groups.keys():
            self.assertTrue(
                Group.objects.filter(name=group_name).exists(),
                f"Group '{group_name}' was not created"
            )
        
        # Verify permission hierarchy
        medical_doctors = Group.objects.get(name='Medical Doctors')
        residents = Group.objects.get(name='Residents')
        nurses = Group.objects.get(name='Nurses')
        physiotherapists = Group.objects.get(name='Physiotherapists')
        students = Group.objects.get(name='Students')
        
        # Medical doctors should have the most permissions
        self.assertGreaterEqual(
            medical_doctors.permissions.count(),
            residents.permissions.count()
        )
        self.assertGreaterEqual(
            residents.permissions.count(),
            nurses.permissions.count()
        )
        self.assertGreaterEqual(
            nurses.permissions.count(),
            students.permissions.count()
        )
