"""
Test suite for the new permission system after security refactor.

This test suite verifies that the permission system properly enforces
security boundaries between medical and administrative roles.
"""

from django.test import TestCase
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

from apps.core.permissions.permission_categories import (
    ADMIN_ONLY_PERMISSIONS,
    is_admin_permission,
    validate_role_permissions,
)

try:
    from apps.accounts.tests.factories import UserFactory
except ImportError:
    # Create minimal factory if not available
    import factory
    from factory.django import DjangoModelFactory
    
    User = get_user_model()
    
    class UserFactory(DjangoModelFactory):
        class Meta:
            model = User
            
        username = factory.Sequence(lambda n: f'user{n}')
        email = factory.Sequence(lambda n: f'user{n}@example.com')
        first_name = factory.Faker('first_name')
        last_name = factory.Faker('last_name')


class TestNewPermissionSystem(TestCase):
    """Test new permission system security boundaries."""
    
    def setUp(self):
        """Set up test groups and users."""
        # Import and run the setup_groups command to create proper permissions
        from django.core.management import call_command
        call_command('setup_groups', force=True, verbosity=0)
        
        self.medical_groups = ['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
        self.admin_groups = ['User Managers']
    
    def test_doctor_has_no_admin_access(self):
        """Test that doctors have no administrative permissions."""
        doctor = UserFactory(profession_type=0)  # Medical doctor
        medical_doctors_group = Group.objects.get(name='Medical Doctors')
        doctor.groups.add(medical_doctors_group)
        
        # Should have medical permissions
        self.assertTrue(doctor.has_perm('patients.add_patient'))
        self.assertTrue(doctor.has_perm('patients.change_patient'))
        self.assertTrue(doctor.has_perm('patients.view_patient'))
        self.assertTrue(doctor.has_perm('events.add_event'))
        self.assertTrue(doctor.has_perm('events.change_event'))
        self.assertTrue(doctor.has_perm('dailynotes.add_dailynote'))
        self.assertTrue(doctor.has_perm('outpatientprescriptions.add_outpatientprescription'))
        
        # Should NOT have admin permissions
        self.assertFalse(doctor.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(doctor.has_perm('accounts.change_eqmdcustomuser'))
        self.assertFalse(doctor.has_perm('auth.add_group'))
        self.assertFalse(doctor.has_perm('auth.change_group'))
        self.assertFalse(doctor.has_perm('admin.view_logentry'))
        self.assertFalse(doctor.has_perm('contenttypes.add_contenttype'))
        self.assertFalse(doctor.has_perm('sessions.add_session'))
        self.assertFalse(doctor.has_perm('patients.add_allowedtag'))
    
    def test_resident_has_same_permissions_as_doctor(self):
        """Test that residents have same clinical permissions as doctors."""
        resident = UserFactory(profession_type=1)  # Resident
        residents_group = Group.objects.get(name='Residents')
        resident.groups.add(residents_group)
        
        # Should have same medical permissions as doctors
        self.assertTrue(resident.has_perm('patients.add_patient'))
        self.assertTrue(resident.has_perm('patients.delete_patient'))
        self.assertTrue(resident.has_perm('events.add_event'))
        self.assertTrue(resident.has_perm('outpatientprescriptions.add_outpatientprescription'))
        
        # Should NOT have admin permissions
        self.assertFalse(resident.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(resident.has_perm('auth.add_group'))
        self.assertFalse(resident.has_perm('admin.view_logentry'))
    
    def test_nurse_has_limited_clinical_permissions(self):
        """Test that nurses have limited clinical permissions."""
        nurse = UserFactory(profession_type=2)  # Nurse
        nurses_group = Group.objects.get(name='Nurses')
        nurse.groups.add(nurses_group)
        
        # Should have limited medical permissions
        self.assertTrue(nurse.has_perm('patients.view_patient'))
        self.assertTrue(nurse.has_perm('patients.change_patient'))
        self.assertTrue(nurse.has_perm('events.add_event'))
        self.assertTrue(nurse.has_perm('dailynotes.add_dailynote'))
        
        # Should NOT have full patient management
        self.assertFalse(nurse.has_perm('patients.add_patient'))
        self.assertFalse(nurse.has_perm('patients.delete_patient'))
        
        # Should NOT have prescriptions
        self.assertFalse(nurse.has_perm('outpatientprescriptions.add_outpatientprescription'))
        
        # Should NOT have admin permissions
        self.assertFalse(nurse.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(nurse.has_perm('auth.add_group'))
    
    def test_physiotherapist_has_clinical_permissions_no_prescriptions(self):
        """Test that physiotherapists have clinical permissions but no prescriptions."""
        physio = UserFactory(profession_type=3)  # Physiotherapist
        physio_group = Group.objects.get(name='Physiotherapists')
        physio.groups.add(physio_group)
        
        # Should have full patient management for therapy
        self.assertTrue(physio.has_perm('patients.add_patient'))
        self.assertTrue(physio.has_perm('patients.change_patient'))
        self.assertTrue(physio.has_perm('patients.delete_patient'))
        self.assertTrue(physio.has_perm('events.add_event'))
        self.assertTrue(physio.has_perm('dailynotes.add_dailynote'))
        
        # Should NOT have prescriptions (not in scope)
        self.assertFalse(physio.has_perm('outpatientprescriptions.add_outpatientprescription'))
        
        # Should NOT have admin permissions
        self.assertFalse(physio.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(physio.has_perm('auth.add_group'))
    
    def test_student_has_read_only_permissions(self):
        """Test that students have read-only clinical permissions."""
        student = UserFactory(profession_type=4)  # Student
        students_group = Group.objects.get(name='Students')
        student.groups.add(students_group)
        
        # Should have view permissions
        self.assertTrue(student.has_perm('patients.view_patient'))
        self.assertTrue(student.has_perm('events.view_event'))
        
        # Should be able to create learning notes
        self.assertTrue(student.has_perm('dailynotes.add_dailynote'))
        self.assertTrue(student.has_perm('simplenotes.add_simplenote'))
        
        # Should NOT have patient management
        self.assertFalse(student.has_perm('patients.add_patient'))
        self.assertFalse(student.has_perm('patients.change_patient'))
        self.assertFalse(student.has_perm('patients.delete_patient'))
        
        # Should NOT have prescriptions
        self.assertFalse(student.has_perm('outpatientprescriptions.add_outpatientprescription'))
        
        # Should NOT have admin permissions
        self.assertFalse(student.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(student.has_perm('auth.add_group'))
    
    def test_user_manager_has_limited_admin_access(self):
        """Test that user managers have limited admin access."""
        user_manager = UserFactory(is_superuser=False, is_staff=False, profession_type=None)
        user_managers_group = Group.objects.get(name='User Managers')
        user_manager.groups.clear()  # Remove any automatically assigned groups
        user_manager.groups.add(user_managers_group)
        
        # Should have user management permissions
        self.assertTrue(user_manager.has_perm('accounts.add_eqmdcustomuser'))
        self.assertTrue(user_manager.has_perm('accounts.change_eqmdcustomuser'))
        self.assertTrue(user_manager.has_perm('accounts.view_eqmdcustomuser'))
        self.assertTrue(user_manager.has_perm('accounts.view_userprofile'))
        self.assertTrue(user_manager.has_perm('auth.view_group'))
        
        # Should NOT have medical data access
        self.assertFalse(user_manager.has_perm('patients.view_patient'))
        self.assertFalse(user_manager.has_perm('events.view_event'))
        self.assertFalse(user_manager.has_perm('dailynotes.view_dailynote'))
        
        # Should NOT have full admin access
        self.assertFalse(user_manager.has_perm('auth.add_group'))
        self.assertFalse(user_manager.has_perm('auth.change_group'))
        self.assertFalse(user_manager.has_perm('admin.view_logentry'))
    
    def test_no_medical_role_has_admin_permissions(self):
        """Test that no medical role has administrative permissions."""
        for group_name in self.medical_groups:
            with self.subTest(group=group_name):
                group = Group.objects.get(name=group_name)
                admin_perms = []
                
                for perm in group.permissions.all():
                    perm_codename = f'{perm.content_type.app_label}.{perm.codename}'
                    if is_admin_permission(perm_codename):
                        admin_perms.append(perm_codename)
                
                self.assertEqual(
                    admin_perms, [], 
                    f'Medical role "{group_name}" has admin permissions: {admin_perms}'
                )
    
    def test_permission_validation_functions(self):
        """Test permission validation helper functions."""
        # Test admin permission detection
        self.assertTrue(is_admin_permission('accounts.add_eqmdcustomuser'))
        self.assertTrue(is_admin_permission('auth.add_group'))
        self.assertTrue(is_admin_permission('admin.view_logentry'))
        self.assertTrue(is_admin_permission('patients.add_allowedtag'))
        
        # Test medical permission detection
        self.assertFalse(is_admin_permission('patients.add_patient'))
        self.assertFalse(is_admin_permission('events.add_event'))
        self.assertFalse(is_admin_permission('dailynotes.add_dailynote'))
        
    def test_role_validation_functions(self):
        """Test role permission validation functions."""
        # Test medical role validation
        medical_perms = ['patients.add_patient', 'events.add_event']
        is_valid, message = validate_role_permissions('Medical Doctors', medical_perms)
        self.assertTrue(is_valid)
        
        # Test invalid medical role permissions
        invalid_perms = ['patients.add_patient', 'accounts.add_eqmdcustomuser']
        is_valid, message = validate_role_permissions('Medical Doctors', invalid_perms)
        self.assertFalse(is_valid)
        self.assertIn('admin permissions', message)
    
    def test_all_groups_exist(self):
        """Test that all expected groups exist."""
        expected_groups = self.medical_groups + self.admin_groups
        existing_groups = set(Group.objects.filter(name__in=expected_groups).values_list('name', flat=True))
        expected_groups_set = set(expected_groups)
        
        self.assertEqual(
            existing_groups, expected_groups_set,
            f'Missing groups: {expected_groups_set - existing_groups}'
        )
    
    def test_group_permission_counts(self):
        """Test that groups have reasonable permission counts."""
        expected_counts = {
            'Medical Doctors': (50, 70),     # Full clinical permissions
            'Residents': (50, 70),           # Same as doctors
            'Nurses': (20, 35),              # Limited clinical permissions  
            'Physiotherapists': (40, 60),    # Clinical permissions, no prescriptions
            'Students': (10, 25),            # Read-only + learning notes
            'User Managers': (5, 10),        # Limited admin permissions
        }
        
        for group_name, (min_count, max_count) in expected_counts.items():
            with self.subTest(group=group_name):
                group = Group.objects.get(name=group_name)
                perm_count = group.permissions.count()
                self.assertGreaterEqual(
                    perm_count, min_count,
                    f'{group_name} has too few permissions: {perm_count} < {min_count}'
                )
                self.assertLessEqual(
                    perm_count, max_count,
                    f'{group_name} has too many permissions: {perm_count} > {max_count}'
                )


class TestSecurityBoundaries(TestCase):
    """Test security boundary enforcement."""
    
    def setUp(self):
        """Set up test groups."""
        from django.core.management import call_command
        call_command('setup_groups', force=True, verbosity=0)
    
    def test_admin_permissions_cannot_be_assigned_to_medical_roles(self):
        """Test that admin permissions cannot be assigned to medical roles."""
        medical_doctor = UserFactory(profession_type=0)
        
        # Even if we try to give admin permissions directly, they should be restricted
        # by business logic (this is tested through the validation functions)
        
        # Test the validation would catch this
        admin_perms = ['accounts.add_eqmdcustomuser', 'auth.add_group']
        is_valid, message = validate_role_permissions('Medical Doctors', admin_perms)
        self.assertFalse(is_valid)
        self.assertIn('admin permissions', message)
    
    def test_user_manager_cannot_access_medical_data(self):
        """Test that user managers cannot access medical data."""
        user_manager = UserFactory(is_superuser=False, is_staff=False, profession_type=None)
        user_managers_group = Group.objects.get(name='User Managers')
        user_manager.groups.clear()  # Remove any automatically assigned groups
        user_manager.groups.add(user_managers_group)
        
        # Should not have any medical permissions
        medical_perms = [
            'patients.view_patient',
            'events.view_event', 
            'dailynotes.view_dailynote',
            'mediafiles.view_photo',
            'outpatientprescriptions.view_outpatientprescription'
        ]
        
        for perm in medical_perms:
            with self.subTest(permission=perm):
                self.assertFalse(
                    user_manager.has_perm(perm),
                    f'User Manager should not have medical permission: {perm}'
                )


class TestPermissionSystemIntegrity(TestCase):
    """Test overall permission system integrity."""
    
    def setUp(self):
        """Set up test groups."""
        from django.core.management import call_command
        call_command('setup_groups', force=True, verbosity=0)
    
    def test_no_permission_overlap_between_medical_and_admin(self):
        """Test that there's no permission overlap between medical and admin roles."""
        # Get all medical group permissions
        medical_groups = Group.objects.filter(
            name__in=['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
        )
        medical_perms = set()
        for group in medical_groups:
            for perm in group.permissions.all():
                medical_perms.add(f'{perm.content_type.app_label}.{perm.codename}')
        
        # Get all admin group permissions  
        admin_groups = Group.objects.filter(name__in=['User Managers'])
        admin_perms = set()
        for group in admin_groups:
            for perm in group.permissions.all():
                admin_perms.add(f'{perm.content_type.app_label}.{perm.codename}')
        
        # Check for overlap
        overlap = medical_perms & admin_perms
        
        # Only acceptable overlap is view permissions for non-sensitive data
        acceptable_overlap = {
            'auth.view_group',  # User managers need to see groups for assignment
        }
        
        unexpected_overlap = overlap - acceptable_overlap
        self.assertEqual(
            unexpected_overlap, set(),
            f'Unexpected permission overlap between medical and admin roles: {unexpected_overlap}'
        )
    
    def test_all_admin_permissions_restricted(self):
        """Test that all admin permissions are properly restricted from medical roles."""
        medical_groups = Group.objects.filter(
            name__in=['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
        )
        
        violations = []
        for group in medical_groups:
            for perm in group.permissions.all():
                perm_codename = f'{perm.content_type.app_label}.{perm.codename}'
                if is_admin_permission(perm_codename):
                    violations.append(f'{group.name}: {perm_codename}')
        
        self.assertEqual(
            violations, [],
            f'Medical roles have admin permissions: {violations}'
        )