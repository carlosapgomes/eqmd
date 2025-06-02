"""
Tests for the accounts app views.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import Http404
from apps.accounts.models import UserProfile
from apps.accounts.tests.factories import UserFactory, DoctorFactory

User = get_user_model()


class ProfileViewTestCase(TestCase):
    """Test cases for profile views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='test@example.com'
        )
        self.other_user = UserFactory(
            username='otheruser',
            first_name='Other',
            last_name='User'
        )

    def test_profile_view_with_valid_uuid(self):
        """Test profile view with valid public UUID."""
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.first_name)
        self.assertContains(response, self.user.last_name)
        self.assertContains(response, 'Profile')

    def test_profile_view_with_invalid_uuid(self):
        """Test profile view with invalid UUID."""
        import uuid
        invalid_uuid = uuid.uuid4()
        url = reverse('apps.accounts:profile', kwargs={'public_id': invalid_uuid})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_profile_view_context_data(self):
        """Test that profile view provides correct context data."""
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile', response.context)
        self.assertEqual(response.context['profile'], self.user.profile)

    def test_profile_detail_view(self):
        """Test profile detail view."""
        url = reverse('apps.accounts:profile_detail', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)
        self.assertContains(response, 'Profile Details')

    def test_profile_detail_view_with_profession(self):
        """Test profile detail view shows profession information."""
        doctor = DoctorFactory(profession_type=0)  # MEDICAL_DOCTOR
        url = reverse('apps.accounts:profile_detail', kwargs={'public_id': doctor.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Médico')

    def test_profile_update_view_requires_login(self):
        """Test that profile update view requires authentication."""
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_profile_update_view_authenticated_user(self):
        """Test profile update view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Profile')

    def test_profile_update_view_wrong_user(self):
        """Test that users can only update their own profiles."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.other_user.profile.public_id})
        response = self.client.get(url)
        
        # Should return 403 Forbidden or redirect
        self.assertIn(response.status_code, [403, 302])

    def test_profile_update_post_valid_data(self):
        """Test profile update with valid POST data."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.user.profile.public_id})
        
        post_data = {
            'display_name': 'Updated Display Name',
            'bio': 'Updated bio information',
        }
        
        response = self.client.post(url, data=post_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Check that profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'Updated Display Name')
        self.assertEqual(self.user.profile.bio, 'Updated bio information')

    def test_profile_update_post_invalid_data(self):
        """Test profile update with invalid POST data."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.user.profile.public_id})
        
        # Assuming display_name has a max length limit
        post_data = {
            'display_name': 'x' * 200,  # Too long
            'bio': 'Valid bio',
        }
        
        response = self.client.post(url, data=post_data)
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')

    def test_profile_redirect_view_authenticated(self):
        """Test profile redirect view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_redirect')
        response = self.client.get(url)
        
        # Should redirect to user's profile
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        self.assertEqual(response.url, expected_url)

    def test_profile_redirect_view_unauthenticated(self):
        """Test profile redirect view for unauthenticated user."""
        url = reverse('apps.accounts:profile_redirect')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_profile_view_template_used(self):
        """Test that correct templates are used."""
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'accounts/profile.html')

    def test_profile_detail_template_used(self):
        """Test that correct template is used for detail view."""
        url = reverse('apps.accounts:profile_detail', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'accounts/profile_detail.html')

    def test_profile_update_template_used(self):
        """Test that correct template is used for update view."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.accounts:profile_update', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'accounts/profile_update.html')

    def test_profile_view_with_display_name(self):
        """Test profile view when user has a display name."""
        self.user.profile.display_name = 'Dr. Test User'
        self.user.profile.save()
        
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dr. Test User')

    def test_profile_view_with_bio(self):
        """Test profile view when user has a bio."""
        self.user.profile.bio = 'This is a test bio for the user.'
        self.user.profile.save()
        
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This is a test bio for the user.')

    def test_profile_view_inactive_user(self):
        """Test profile view for inactive user."""
        self.user.is_active = False
        self.user.save()
        
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        response = self.client.get(url)
        
        # Profile should still be viewable even if user is inactive
        # (This depends on business requirements)
        self.assertEqual(response.status_code, 200)

    def test_profile_view_staff_user(self):
        """Test profile view for staff user."""
        staff_user = UserFactory(is_staff=True)
        url = reverse('apps.accounts:profile', kwargs={'public_id': staff_user.profile.public_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Could check for staff-specific content if any

    def test_multiple_profile_views_same_user(self):
        """Test multiple requests to same profile view."""
        url = reverse('apps.accounts:profile', kwargs={'public_id': self.user.profile.public_id})
        
        response1 = self.client.get(url)
        response2 = self.client.get(url)
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        # Both should return the same content
        self.assertEqual(response1.content, response2.content)
