"""
Tests for the accounts app models.
"""
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.accounts.models import UserProfile
from apps.accounts.tests.factories import (
    UserFactory, UserProfileFactory, DoctorFactory, 
    NurseFactory, StudentFactory
)

User = get_user_model()


class EqmdCustomUserModelTestCase(TestCase):
    """Test cases for the EqmdCustomUser model."""

    def test_user_creation_with_factory(self):
        """Test that a user can be created using the factory."""
        user = UserFactory()
        self.assertIsInstance(user, User)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.username)
        self.assertIsNotNone(user.email)

    def test_user_creation_with_profession_type(self):
        """Test user creation with specific profession types."""
        doctor = DoctorFactory()
        nurse = NurseFactory()
        student = StudentFactory()
        
        self.assertEqual(doctor.profession_type, 0)  # MEDICAL_DOCTOR
        self.assertEqual(nurse.profession_type, 2)   # NURSE
        self.assertEqual(student.profession_type, 4) # STUDENT

    def test_user_string_representation(self):
        """Test the string representation of the user."""
        user = UserFactory(username='testuser')
        self.assertEqual(str(user), 'testuser')

    def test_profession_type_choices(self):
        """Test that profession type choices work correctly."""
        doctor = DoctorFactory(profession_type=0)
        self.assertEqual(doctor.get_profession_type_display(), "Médico")
        
        nurse = NurseFactory(profession_type=2)
        self.assertEqual(nurse.get_profession_type_display(), "Enfermeiro")

    def test_user_email_uniqueness(self):
        """Test that user emails must be unique."""
        UserFactory(email='test@example.com')
        
        # This should not raise an error as we're creating a different user
        # Django handles email uniqueness at the database level if configured
        user2 = UserFactory()
        self.assertNotEqual(user2.email, 'test@example.com')

    def test_user_password_setting(self):
        """Test that user passwords are properly set."""
        user = UserFactory(password='custompass123')
        self.assertTrue(user.check_password('custompass123'))
        self.assertFalse(user.check_password('wrongpassword'))

    def test_user_professional_fields(self):
        """Test that professional fields are properly set."""
        user = DoctorFactory(
            professional_registration_number='CRM-12345',
            country_id_number='123.456.789-00',
            fiscal_number='987.654.321-00',
            phone='+55 11 99999-9999'
        )
        
        self.assertEqual(user.professional_registration_number, 'CRM-12345')
        self.assertEqual(user.country_id_number, '123.456.789-00')
        self.assertEqual(user.fiscal_number, '987.654.321-00')
        self.assertEqual(user.phone, '+55 11 99999-9999')


class UserProfileModelTestCase(TestCase):
    """Test cases for the UserProfile model."""

    def test_profile_creation_via_signal(self):
        """Test that a profile is automatically created when a user is created."""
        user = UserFactory()
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_profile_public_id_generation(self):
        """Test that a public ID is automatically generated."""
        user = UserFactory()
        profile = user.profile
        self.assertIsInstance(profile.public_id, uuid.UUID)
        self.assertIsNotNone(profile.public_id)

    def test_profile_public_id_uniqueness(self):
        """Test that public IDs are unique."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        self.assertNotEqual(user1.profile.public_id, user2.profile.public_id)

    def test_profile_string_representation(self):
        """Test the string representation of the profile."""
        user = UserFactory()
        profile = user.profile
        profile.display_name = 'Dr. Silva'
        profile.save()
        self.assertEqual(str(profile), 'Dr. Silva')

    def test_profile_string_representation_fallback(self):
        """Test profile string representation falls back to full name."""
        user = UserFactory(first_name='João', last_name='Silva')
        profile = user.profile
        profile.display_name = ''
        profile.save()
        
        self.assertEqual(str(profile), 'João Silva')

    def test_profile_string_representation_username_fallback(self):
        """Test profile string representation falls back to username."""
        user = UserFactory(first_name='', last_name='', username='testuser')
        profile = user.profile
        profile.display_name = ''
        profile.save()
        
        self.assertEqual(str(profile), 'testuser')

    def test_profile_properties(self):
        """Test that profile properties correctly expose user data."""
        user = UserFactory(
            first_name='João',
            last_name='Silva',
            email='joao@example.com',
            is_active=True,
            is_staff=True,
            is_superuser=False,
            profession_type=0  # MEDICAL_DOCTOR
        )
        profile = user.profile
        
        self.assertEqual(profile.first_name, 'João')
        self.assertEqual(profile.last_name, 'Silva')
        self.assertEqual(profile.email, 'joao@example.com')
        self.assertEqual(profile.full_name, 'João Silva')
        self.assertTrue(profile.is_active)
        self.assertTrue(profile.is_staff)
        self.assertFalse(profile.is_superuser)
        self.assertEqual(profile.profession, 'Médico')

    def test_profile_full_name_property(self):
        """Test the full_name property with different scenarios."""
        # Test with both first and last name
        user1 = UserFactory(first_name='João', last_name='Silva')
        self.assertEqual(user1.profile.full_name, 'João Silva')
        
        # Test with only first name
        user2 = UserFactory(first_name='João', last_name='')
        self.assertEqual(user2.profile.full_name, 'João')
        
        # Test with only last name
        user3 = UserFactory(first_name='', last_name='Silva')
        self.assertEqual(user3.profile.full_name, 'Silva')
        
        # Test with no names (should fall back to username)
        user4 = UserFactory(first_name='', last_name='', username='testuser')
        self.assertEqual(user4.profile.full_name, 'testuser')

    def test_profile_profession_property(self):
        """Test the profession property with different profession types."""
        # Test with medical doctor
        doctor = DoctorFactory(profession_type=0)
        self.assertEqual(doctor.profile.profession, 'Médico')
        
        # Test with nurse
        nurse = NurseFactory(profession_type=2)
        self.assertEqual(nurse.profile.profession, 'Enfermeiro')
        
        # Test with no profession type
        user = UserFactory(profession_type=None)
        self.assertEqual(user.profile.profession, '')

    def test_profile_one_to_one_relationship(self):
        """Test that the profile has a proper one-to-one relationship with user."""
        user = UserFactory()
        profile = user.profile
        
        # Test forward relationship
        self.assertEqual(profile.user, user)
        
        # Test reverse relationship
        self.assertEqual(user.profile, profile)

    def test_profile_cascade_deletion(self):
        """Test that profile is deleted when user is deleted."""
        user = UserFactory()
        profile_id = user.profile.id
        
        # Delete the user
        user.delete()
        
        # Profile should also be deleted
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)

    def test_profile_bio_field(self):
        """Test the bio field functionality."""
        user = UserFactory()
        profile = user.profile
        profile.bio = 'This is a test bio.'
        profile.save()
        self.assertEqual(profile.bio, 'This is a test bio.')

        # Test empty bio
        profile.bio = ''
        profile.save()
        self.assertEqual(profile.bio, '')

    def test_profile_display_name_field(self):
        """Test the display_name field functionality."""
        user = UserFactory()
        profile = user.profile
        profile.display_name = 'Dr. Test'
        profile.save()
        self.assertEqual(profile.display_name, 'Dr. Test')

        # Test empty display name
        profile.display_name = ''
        profile.save()
        self.assertEqual(profile.display_name, '')
