"""
Tests for signal handlers in the accounts app.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import UserProfile

User = get_user_model()


class UserSignalTestCase(TestCase):
    def setUp(self):
        # Create profession-based groups
        self.medical_doctors_group = Group.objects.create(name='Medical Doctors')
        self.residents_group = Group.objects.create(name='Residents')
        self.nurses_group = Group.objects.create(name='Nurses')
        self.physiotherapists_group = Group.objects.create(name='Physiotherapists')
        self.students_group = Group.objects.create(name='Students')

    def test_user_profile_created_on_user_creation(self):
        """Test that UserProfile is automatically created when user is created"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Profile should be created automatically
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_user_assigned_to_medical_doctor_group(self):
        """Test that user is assigned to Medical Doctors group when profession is set"""
        user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # User should be in Medical Doctors group
        self.assertTrue(user.groups.filter(name='Medical Doctors').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_assigned_to_resident_group(self):
        """Test that user is assigned to Residents group when profession is set"""
        user = User.objects.create_user(
            username='resident',
            email='resident@example.com',
            password='testpass123',
            profession_type=User.RESIDENT
        )
        
        # User should be in Residents group
        self.assertTrue(user.groups.filter(name='Residents').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_assigned_to_nurse_group(self):
        """Test that user is assigned to Nurses group when profession is set"""
        user = User.objects.create_user(
            username='nurse',
            email='nurse@example.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        
        # User should be in Nurses group
        self.assertTrue(user.groups.filter(name='Nurses').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_assigned_to_physiotherapist_group(self):
        """Test that user is assigned to Physiotherapists group when profession is set"""
        user = User.objects.create_user(
            username='physio',
            email='physio@example.com',
            password='testpass123',
            profession_type=User.PHYSIOTERAPIST
        )
        
        # User should be in Physiotherapists group
        self.assertTrue(user.groups.filter(name='Physiotherapists').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_assigned_to_student_group(self):
        """Test that user is assigned to Students group when profession is set"""
        user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
            profession_type=User.STUDENT
        )
        
        # User should be in Students group
        self.assertTrue(user.groups.filter(name='Students').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_no_group_when_no_profession(self):
        """Test that user is not assigned to any profession group when profession is None"""
        user = User.objects.create_user(
            username='noprof',
            email='noprof@example.com',
            password='testpass123'
            # profession_type is None by default
        )
        
        # User should not be in any profession groups
        profession_groups = Group.objects.filter(name__in=[
            'Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students'
        ])
        
        for group in profession_groups:
            self.assertFalse(user.groups.filter(name=group.name).exists())

    def test_user_group_changed_when_profession_changed(self):
        """Test that user group is updated when profession type is changed"""
        # Create user as doctor
        user = User.objects.create_user(
            username='changinguser',
            email='changing@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # Should be in Medical Doctors group
        self.assertTrue(user.groups.filter(name='Medical Doctors').exists())
        self.assertFalse(user.groups.filter(name='Nurses').exists())
        
        # Change profession to nurse
        user.profession_type = User.NURSE
        user.save()
        
        # Should now be in Nurses group and not in Medical Doctors group
        self.assertFalse(user.groups.filter(name='Medical Doctors').exists())
        self.assertTrue(user.groups.filter(name='Nurses').exists())
        self.assertEqual(user.groups.count(), 1)

    def test_user_removed_from_profession_groups_when_profession_cleared(self):
        """Test that user is removed from profession groups when profession is set to None"""
        # Create user as doctor
        user = User.objects.create_user(
            username='clearinguser',
            email='clearing@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # Should be in Medical Doctors group
        self.assertTrue(user.groups.filter(name='Medical Doctors').exists())
        
        # Clear profession
        user.profession_type = None
        user.save()
        
        # Should not be in any profession groups
        profession_groups = Group.objects.filter(name__in=[
            'Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students'
        ])
        
        for group in profession_groups:
            self.assertFalse(user.groups.filter(name=group.name).exists())

    def test_signal_handles_missing_groups_gracefully(self):
        """Test that signal handler doesn't fail when groups don't exist"""
        # Delete all groups
        Group.objects.all().delete()
        
        # Creating user should not raise an exception
        try:
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                profession_type=User.MEDICAL_DOCTOR
            )
            # Should succeed without error
            self.assertIsNotNone(user)
        except Exception as e:
            self.fail(f"Signal handler failed when groups don't exist: {e}")

    def test_user_can_be_in_multiple_groups(self):
        """Test that user can be in profession group plus other groups"""
        # Create a non-profession group
        other_group = Group.objects.create(name='Special Users')
        
        # Create user
        user = User.objects.create_user(
            username='multigroup',
            email='multi@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # Add to other group manually
        user.groups.add(other_group)
        
        # Should be in both groups
        self.assertTrue(user.groups.filter(name='Medical Doctors').exists())
        self.assertTrue(user.groups.filter(name='Special Users').exists())
        self.assertEqual(user.groups.count(), 2)
        
        # Change profession - should keep other group but change profession group
        user.profession_type = User.NURSE
        user.save()
        
        # Should be in Nurses and Special Users groups
        self.assertFalse(user.groups.filter(name='Medical Doctors').exists())
        self.assertTrue(user.groups.filter(name='Nurses').exists())
        self.assertTrue(user.groups.filter(name='Special Users').exists())
        self.assertEqual(user.groups.count(), 2)
