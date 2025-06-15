from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.events.models import Event
from .models import SampleContent

User = get_user_model()


class SampleContentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )

    def test_sample_content_creation(self):
        """Test creating a sample content instance."""
        sample_content = SampleContent.objects.create(
            title='Test Sample',
            content='This is test content',
            event_type=Event.DAILY_NOTE_EVENT,
            created_by=self.superuser,
            updated_by=self.superuser
        )
        
        self.assertEqual(sample_content.title, 'Test Sample')
        self.assertEqual(sample_content.event_type, Event.DAILY_NOTE_EVENT)
        self.assertEqual(str(sample_content), 'Test Sample')

    def test_sample_content_str_method(self):
        """Test string representation of sample content."""
        sample_content = SampleContent.objects.create(
            title='Daily Note Template',
            content='Template content',
            event_type=Event.DAILY_NOTE_EVENT,
            created_by=self.superuser,
            updated_by=self.superuser
        )
        
        self.assertEqual(str(sample_content), 'Daily Note Template')


class SampleContentViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser2',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.superuser = User.objects.create_superuser(
            username='admin2',
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        
        self.sample_content = SampleContent.objects.create(
            title='Test Sample',
            content='Test content',
            event_type=Event.DAILY_NOTE_EVENT,
            created_by=self.superuser,
            updated_by=self.superuser
        )

    def test_sample_content_list_requires_login(self):
        """Test that sample content list requires authentication."""
        url = reverse('sample_content:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_sample_content_list_authenticated(self):
        """Test sample content list view for authenticated users."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('sample_content:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_api_endpoint_requires_login(self):
        """Test that API endpoint requires authentication."""
        url = reverse('sample_content:api_by_event_type', kwargs={'event_type': '1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_api_endpoint_authenticated(self):
        """Test API endpoint for authenticated users."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('sample_content:api_by_event_type', kwargs={'event_type': '1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sample_contents')