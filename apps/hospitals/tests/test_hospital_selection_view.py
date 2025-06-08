"""
Tests for hospital selection view.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from apps.hospitals.models import Hospital

User = get_user_model()


class HospitalSelectionViewTest(TestCase):
    """Test cases for hospital selection view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
        
        # Create test hospitals
        self.hospital1 = Hospital.objects.create(
            name='First Hospital',
            short_name='FH',
            phone='1234567890',
            address='First Address',
            city='First City',
            state='FC',
            zip_code='12345000',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.hospital2 = Hospital.objects.create(
            name='Second Hospital',
            short_name='SH',
            phone='9876543210',
            address='Second Address',
            city='Second City',
            state='SC',
            zip_code='98765000',
            created_by=self.user,
            updated_by=self.user
        )

    def test_hospital_selection_view_requires_login(self):
        """Test that hospital selection view requires login."""
        url = reverse('hospitals:select_hospital')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/account/login/', response.url)

    def test_hospital_selection_view_get(self):
        """Test GET request to hospital selection view."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('hospitals:select_hospital')
        
        response = self.client.get(url)
        
        # Should render template successfully
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecionar Hospital')
        self.assertContains(response, self.hospital1.name)
        self.assertContains(response, self.hospital2.name)

    def test_hospital_selection_with_current_hospital(self):
        """Test view when user has current hospital in session."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Set hospital in session
        session = self.client.session
        session['current_hospital_id'] = str(self.hospital1.pk)
        session.save()
        
        url = reverse('hospitals:select_hospital')
        response = self.client.get(url)
        
        # Should show current hospital info
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital Atual')
        self.assertContains(response, self.hospital1.name)

    def test_hospital_selection_post_valid_hospital(self):
        """Test POST request with valid hospital ID."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('hospitals:select_hospital')
        
        response = self.client.post(url, {
            'hospital_id': str(self.hospital1.pk),
            'next': '/dashboard/'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        
        # Should set hospital in session
        self.assertEqual(
            self.client.session['current_hospital_id'], 
            str(self.hospital1.pk)
        )
        
        # Should show success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('selecionado como contexto atual', str(messages[0]))

    def test_hospital_selection_post_invalid_hospital(self):
        """Test POST request with invalid hospital ID."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('hospitals:select_hospital')
        
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(url, {
            'hospital_id': invalid_uuid,
            'next': '/dashboard/'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        
        # Should not set hospital in session
        self.assertNotIn('current_hospital_id', self.client.session)
        
        # Should show error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('não encontrado', str(messages[0]))

    def test_hospital_selection_post_clear_context(self):
        """Test POST request to clear hospital context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Set hospital in session first
        session = self.client.session
        session['current_hospital_id'] = str(self.hospital1.pk)
        session.save()
        
        url = reverse('hospitals:select_hospital')
        response = self.client.post(url, {
            'hospital_id': '',  # Empty value to clear
            'next': '/dashboard/'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        
        # Should clear hospital from session
        self.assertNotIn('current_hospital_id', self.client.session)
        
        # Should show info message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('removido', str(messages[0]))

    def test_hospital_selection_with_next_parameter(self):
        """Test hospital selection with custom next URL."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('hospitals:select_hospital')
        
        response = self.client.post(url + '?next=/patients/', {
            'hospital_id': str(self.hospital1.pk),
        })
        
        # Should redirect to custom next URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/patients/')

    def test_hospital_selection_view_context(self):
        """Test that view provides correct context data."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('hospitals:select_hospital')
        
        response = self.client.get(url + '?next=/patients/')
        
        # Should include hospitals and next URL in context
        self.assertIn('hospitals', response.context)
        self.assertIn('next_url', response.context)
        self.assertEqual(response.context['next_url'], '/patients/')
        
        # Should include all hospitals
        hospitals = response.context['hospitals']
        self.assertEqual(hospitals.count(), 2)
        self.assertIn(self.hospital1, hospitals)
        self.assertIn(self.hospital2, hospitals)