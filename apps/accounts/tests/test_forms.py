"""
Tests for the accounts app forms.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.forms import EqmdCustomUserCreationForm, EqmdCustomUserChangeForm
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


class EqmdCustomUserCreationFormTestCase(TestCase):
    """Test cases for the EqmdCustomUserCreationForm."""

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'profession_type': 0,  # MEDICAL_DOCTOR
            'professional_registration_number': 'CRM-12345',
            'country_id_number': '123.456.789-00',
            'fiscal_number': '987.654.321-00',
            'phone': '+55 11 99999-9999'
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_save(self):
        """Test that form saves user correctly."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'profession_type': 0,
            'professional_registration_number': 'CRM-12345',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.profession_type, 0)
        self.assertEqual(user.professional_registration_number, 'CRM-12345')
        self.assertTrue(user.check_password('complexpassword123'))

    def test_form_password_mismatch(self):
        """Test form with mismatched passwords."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'differentpassword123',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_form_duplicate_username(self):
        """Test form with duplicate username."""
        # Create existing user
        UserFactory(username='existinguser')
        
        form_data = {
            'username': 'existinguser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_form_invalid_email(self):
        """Test form with invalid email."""
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_weak_password(self):
        """Test form with weak password."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': '123',
            'password2': '123',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_form_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)

    def test_form_optional_fields(self):
        """Test form with only required fields."""
        form_data = {
            'username': 'testuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_profession_type_choices(self):
        """Test form with different profession type choices."""
        # Test valid profession type
        form_data = {
            'username': 'testuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'profession_type': 2,  # NURSE
        }
        
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test invalid profession type
        form_data['profession_type'] = 999
        form = EqmdCustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('profession_type', form.errors)


class EqmdCustomUserChangeFormTestCase(TestCase):
    """Test cases for the EqmdCustomUserChangeForm."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            profession_type=0
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User',
            'profession_type': 1,  # RESIDENT
            'professional_registration_number': 'CRM-54321',
            'country_id_number': '987.654.321-00',
            'fiscal_number': '123.456.789-00',
            'phone': '+55 11 88888-8888'
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_save(self):
        """Test that form saves user changes correctly."""
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User',
            'profession_type': 1,
            'professional_registration_number': 'CRM-54321',
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        updated_user = form.save()
        self.assertEqual(updated_user.username, 'updateduser')
        self.assertEqual(updated_user.email, 'updated@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.profession_type, 1)
        self.assertEqual(updated_user.professional_registration_number, 'CRM-54321')

    def test_form_partial_update(self):
        """Test form with partial data update."""
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'first_name': 'Updated First Name',
            # Other fields should remain unchanged
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        updated_user = form.save()
        self.assertEqual(updated_user.first_name, 'Updated First Name')
        self.assertEqual(updated_user.last_name, self.user.last_name)  # Unchanged

    def test_form_duplicate_username_different_user(self):
        """Test form with username that belongs to another user."""
        other_user = UserFactory(username='otheruser')
        
        form_data = {
            'username': 'otheruser',
            'email': self.user.email,
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_form_same_username(self):
        """Test form with same username (should be valid)."""
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_invalid_email_format(self):
        """Test form with invalid email format."""
        form_data = {
            'username': self.user.username,
            'email': 'invalid-email-format',
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_empty_optional_fields(self):
        """Test form with empty optional fields."""
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'first_name': '',
            'last_name': '',
            'professional_registration_number': '',
            'country_id_number': '',
            'fiscal_number': '',
            'phone': '',
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_profession_type_update(self):
        """Test updating profession type."""
        original_profession = self.user.profession_type
        
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'profession_type': 2,  # NURSE
        }
        
        form = EqmdCustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())
        
        updated_user = form.save()
        self.assertNotEqual(updated_user.profession_type, original_profession)
        self.assertEqual(updated_user.profession_type, 2)

    def test_form_without_instance(self):
        """Test form behavior without instance (should still work)."""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
        }
        
        form = EqmdCustomUserChangeForm(data=form_data)
        # Form should be valid but won't save properly without instance
        # This tests the form validation logic
        self.assertTrue(form.is_valid())
