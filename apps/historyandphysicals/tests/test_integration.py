from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from ..models import HistoryAndPhysical

User = get_user_model()


class HistoryAndPhysicalIntegrationTest(TestCase):
    """Integration tests for HistoryAndPhysical functionality."""

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            address='123 Test St',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,  # inpatient
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create test history and physical
        self.historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Test History and Physical',
            content='This is a test history and physical content.',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Log in the user
        self.client.login(username='testuser', password='testpass123')

    def test_historyandphysical_detail_view(self):
        """Test the history and physical detail view."""
        url = reverse('apps.historyandphysicals:historyandphysical_detail', 
                     kwargs={'pk': self.historyandphysical.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.historyandphysical.content)
        self.assertContains(response, self.patient.name)

    def test_patient_historyandphysical_create_view(self):
        """Test creating a new history and physical for a patient."""
        url = reverse('apps.historyandphysicals:historyandphysical_create',
                     kwargs={'patient_pk': self.patient.pk})
        
        # GET request to display form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.name)
        
        # POST request to create history and physical
        form_data = {
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'content': 'This is a new test history and physical content with enough characters.'
        }
        
        response = self.client.post(url, data=form_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify the history and physical was created
        new_historyandphysical = HistoryAndPhysical.objects.filter(
            patient=self.patient,
            content__icontains='new test history and physical'
        ).first()
        
        self.assertIsNotNone(new_historyandphysical)
        self.assertEqual(new_historyandphysical.patient, self.patient)
        self.assertEqual(new_historyandphysical.created_by, self.user)

    def test_historyandphysical_update_view(self):
        """Test updating an existing history and physical."""
        url = reverse('apps.historyandphysicals:historyandphysical_update',
                     kwargs={'pk': self.historyandphysical.pk})
        
        # GET request to display form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.historyandphysical.content)
        
        # POST request to update history and physical
        updated_content = 'This is updated history and physical content with enough characters.'
        form_data = {
            'event_datetime': self.historyandphysical.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'content': updated_content
        }
        
        response = self.client.post(url, data=form_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Verify the history and physical was updated
        updated_historyandphysical = HistoryAndPhysical.objects.get(pk=self.historyandphysical.pk)
        self.assertEqual(updated_historyandphysical.content, updated_content)
        self.assertEqual(updated_historyandphysical.updated_by, self.user)

    def test_historyandphysical_duplicate_view(self):
        """Test duplicating an existing history and physical."""
        url = reverse('apps.historyandphysicals:historyandphysical_duplicate',
                     kwargs={'pk': self.historyandphysical.pk})
        
        # GET request to display form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.historyandphysical.content)
        
        # POST request to duplicate history and physical
        form_data = {
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'content': self.historyandphysical.content  # Content should be pre-populated
        }
        
        response = self.client.post(url, data=form_data)
        
        # Should redirect after successful duplication
        self.assertEqual(response.status_code, 302)
        
        # Verify a new history and physical was created
        historyandphysicals_count = HistoryAndPhysical.objects.filter(
            patient=self.patient,
            content=self.historyandphysical.content
        ).count()
        
        self.assertEqual(historyandphysicals_count, 2)  # Original + duplicate

    def test_historyandphysical_delete_view(self):
        """Test deleting a history and physical."""
        url = reverse('apps.historyandphysicals:historyandphysical_delete',
                     kwargs={'pk': self.historyandphysical.pk})
        
        # GET request to display confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Exclusão')
        
        # POST request to delete history and physical
        response = self.client.post(url)
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Verify the history and physical was deleted
        with self.assertRaises(HistoryAndPhysical.DoesNotExist):
            HistoryAndPhysical.objects.get(pk=self.historyandphysical.pk)

    def test_historyandphysical_print_view(self):
        """Test the print view for history and physical."""
        url = reverse('apps.historyandphysicals:historyandphysical_print',
                     kwargs={'pk': self.historyandphysical.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.historyandphysical.content)
        self.assertContains(response, self.patient.name)


    def test_historyandphysical_access_permissions(self):
        """Test that users can only access history and physicals they have permission for."""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create another hospital
        other_hospital = Hospital.objects.create(
            name='Other Hospital',
            address='456 Other St',
            created_by=other_user,
            updated_by=other_user
        )
        
        # Create patient in other hospital
        other_patient = Patient.objects.create(
            name='Other Patient',
            birthday='1985-01-01',
            status=1,
            current_hospital=other_hospital,
            created_by=other_user,
            updated_by=other_user
        )
        
        # Create history and physical for other patient
        other_historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Other History and Physical',
            content='This is another history and physical.',
            patient=other_patient,
            created_by=other_user,
            updated_by=other_user
        )
        
        # Try to access other user's history and physical
        url = reverse('apps.historyandphysicals:historyandphysical_detail',
                     kwargs={'pk': other_historyandphysical.pk})
        
        response = self.client.get(url)
        
        # Should be denied access (403) or redirected
        self.assertIn(response.status_code, [403, 302])

    def test_historyandphysical_timeline_integration(self):
        """Test that history and physicals appear correctly in patient timeline."""
        # This would test integration with the patient timeline view
        # For now, we'll test that the URLs are properly constructed
        
        detail_url = self.historyandphysical.get_absolute_url()
        self.assertTrue(detail_url.startswith('/historyandphysicals/'))
        
        edit_url = self.historyandphysical.get_edit_url()
        self.assertTrue(edit_url.endswith('/update/'))