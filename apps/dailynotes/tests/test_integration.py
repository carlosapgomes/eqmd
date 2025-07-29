"""
Integration tests for DailyNote Slice 5 features.
Tests patient integration, search/filtering, dashboard widgets, and print features.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from apps.patients.models import Patient
# Note: Hospital model removed after single-hospital refactor, Ward
from apps.dailynotes.models import DailyNote
from apps.dailynotes.templatetags.dailynote_tags import recent_dailynotes_widget, dailynotes_count_today, dailynotes_count_week


User = get_user_model()


class DailyNoteIntegrationTestCase(TestCase):
    """Base test case with common setup for integration tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create hospital and ward
        self.ward = Ward.objects.create(
            name="Test Ward",
            hospital=self.hospital,
            capacity=10
        )
        
        # Create users
        self.doctor = User.objects.create_user(
            username="doctor",
            email="doctor@test.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            first_name="Dr.",
            last_name="Test"
        )
        self.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@test.com",
            password="testpass123",
            profession_type=User.NURSE
        )
        
        # Set hospital context (simulating middleware behavior)
        self.doctor.current_hospital = self.hospital
        self.doctor.has_hospital_context = True
        self.nurse.current_hospital = self.hospital
        self.nurse.has_hospital_context = True
        
        # Create patients
        self.patient1 = Patient.objects.create(
            name="Patient One",
            fiscal_number="12345678901",
            healthcard_number="123456789012345",
            birthday="1980-01-01",
            status=Patient.Status.INPATIENT,
            
            bed="101",
            created_by=self.doctor,
            updated_by=self.doctor
        )
        self.patient2 = Patient.objects.create(
            name="Patient Two",
            fiscal_number="98765432109",
            healthcard_number="987654321098765",
            birthday="1975-06-15",
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create daily notes
        self.dailynote1 = DailyNote.objects.create(
            patient=self.patient1,
            description="First evolution",
            content="Patient is stable. No major changes.",
            event_datetime=timezone.now() - timedelta(hours=2),
            created_by=self.doctor,
            updated_by=self.doctor
        )
        self.dailynote2 = DailyNote.objects.create(
            patient=self.patient2,
            description="Second evolution",
            content="Patient improving. Continue treatment.",
            event_datetime=timezone.now() - timedelta(hours=1),
            created_by=self.nurse,
            updated_by=self.nurse
        )
        self.dailynote3 = DailyNote.objects.create(
            patient=self.patient1,
            description="Follow-up evolution",
            content="Patient condition worsened. Adjust medication.",
            event_datetime=timezone.now() - timedelta(days=1),
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.client = Client()


class PatientIntegrationTests(DailyNoteIntegrationTestCase):
    """Test patient-specific daily note views and integration."""
    
    def test_patient_dailynote_list_view(self):
        """Test patient-specific daily notes list view."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:patient_dailynote_list', kwargs={'patient_pk': self.patient1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.name)
        self.assertContains(response, "First evolution")
        self.assertContains(response, "Follow-up evolution")
        # Should not contain notes from other patients
        self.assertNotContains(response, "Second evolution")
    
    def test_patient_dailynote_list_with_date_filter(self):
        """Test patient daily notes list with date filtering."""
        self.client.login(username="doctor", password="testpass123")
        
        # Filter by today only
        today = timezone.now().date()
        url = reverse('dailynotes:patient_dailynote_list', kwargs={'patient_pk': self.patient1.pk})
        response = self.client.get(url, {
            'date_from': today.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First evolution")  # Today
        self.assertNotContains(response, "Follow-up evolution")  # Yesterday
    
    def test_patient_dailynote_create_view(self):
        """Test creating daily note for specific patient."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:patient_dailynote_create', kwargs={'patient_pk': self.patient1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.name)
        
        # Test creating a daily note
        response = self.client.post(url, {
            'patient': self.patient1.pk,
            'description': 'New evolution for patient',
            'content': 'Patient is doing well today.',
            'event_datetime': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(DailyNote.objects.filter(
            patient=self.patient1,
            description="New evolution for patient"
        ).exists())
    
    def test_patient_access_permissions(self):
        """Test that users can only access patients they have permission for."""
        # Create patient in different hospital
        other_patient = Patient.objects.create(
            name="Other Patient",
            fiscal_number="55555555555",
            healthcard_number="555555555555555",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.client.login(username="doctor", password="testpass123")
        
        # Should not be able to access patient from different hospital
        url = reverse('dailynotes:patient_dailynote_list', kwargs={'patient_pk': other_patient.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)  # Permission denied


class SearchFilteringTests(DailyNoteIntegrationTestCase):
    """Test search and filtering functionality."""
    
    def test_daily_note_search_functionality(self):
        """Test searching daily notes by content and patient name."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_list')
        
        # Search by content
        response = self.client.get(url, {'search': 'stable'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First evolution")
        self.assertNotContains(response, "Second evolution")
        
        # Search by patient name
        response = self.client.get(url, {'search': 'Patient Two'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Second evolution")
        self.assertNotContains(response, "First evolution")
    
    def test_daily_note_date_filtering(self):
        """Test date range filtering."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_list')
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Filter by today only
        response = self.client.get(url, {
            'date_from': today.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        
        self.assertEqual(response.status_code, 200)
        # Should contain today's notes
        self.assertContains(response, "First evolution")
        self.assertContains(response, "Second evolution")
        # Should not contain yesterday's note
        self.assertNotContains(response, "Follow-up evolution")
    
    def test_daily_note_creator_filtering(self):
        """Test filtering by creator."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_list')
        
        # Filter by doctor
        response = self.client.get(url, {'creator': self.doctor.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First evolution")
        self.assertContains(response, "Follow-up evolution")
        self.assertNotContains(response, "Second evolution")  # Created by nurse


class DashboardIntegrationTests(DailyNoteIntegrationTestCase):
    """Test dashboard widget integration."""
    
    def test_recent_dailynotes_widget(self):
        """Test recent daily notes widget template tag."""
        # Mock request context
        request = type('Request', (), {})()
        request.user = self.doctor
        
        context = {'request': request}
        
        # Test widget renders recent notes
        result = recent_dailynotes_widget(context, limit=5)
        
        self.assertIn('recent_dailynotes', result)
        self.assertEqual(len(result['recent_dailynotes']), 3)  # All 3 notes should be accessible
        
        # Check that most recent note is first
        self.assertEqual(result['recent_dailynotes'][0], self.dailynote2)
    
    def test_dailynotes_count_today_tag(self):
        """Test daily notes count today template tag."""
        request = type('Request', (), {})()
        request.user = self.doctor
        
        context = {'request': request}
        
        count = dailynotes_count_today(context)
        
        # Should count today's notes only (2 notes created today)
        self.assertEqual(count, 2)
    
    def test_dailynotes_count_week_tag(self):
        """Test daily notes count week template tag."""
        request = type('Request', (), {})()
        request.user = self.doctor
        
        context = {'request': request}
        
        count = dailynotes_count_week(context)
        
        # Should count all notes in the last 7 days (all 3 notes)
        self.assertEqual(count, 3)


class ExportPrintTests(DailyNoteIntegrationTestCase):
    """Test export and print functionality."""
    
    def test_dailynote_print_view(self):
        """Test individual daily note print view."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_print', kwargs={'pk': self.dailynote1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dailynote1.patient.name)
        self.assertContains(response, self.dailynote1.description)
        self.assertContains(response, self.dailynote1.content)
        self.assertContains(response, "EVOLUÇÃO MÉDICA")
    
    
    def test_print_permissions(self):
        """Test that print respects patient access permissions."""
        # Create patient in different hospital
        other_patient = Patient.objects.create(
            name="Other Patient",
            fiscal_number="55555555555",
            healthcard_number="555555555555555",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            
            created_by=self.doctor,
            updated_by=self.doctor
        )
        other_dailynote = DailyNote.objects.create(
            patient=other_patient,
            description="Other evolution",
            content="Content for other patient",
            event_datetime=timezone.now(),
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.client.login(username="doctor", password="testpass123")
        
        # Should not be able to print note for patient from different hospital
        url = reverse('dailynotes:dailynote_print', kwargs={'pk': other_dailynote.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class TemplateIntegrationTests(DailyNoteIntegrationTestCase):
    """Test template integration and UI elements."""
    
    def test_main_dailynote_list_has_filter_options(self):
        """Test that main daily note list includes filter options."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for filter form elements
        self.assertContains(response, 'name="search"')
        self.assertContains(response, 'name="date_from"')
        self.assertContains(response, 'name="date_to"')
        self.assertContains(response, 'name="patient"')
        self.assertContains(response, 'Filtros Avançados')
    
    
    def test_dailynote_detail_has_print_button(self):
        """Test that daily note detail view includes print button."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Imprimir')
        print_url = reverse('dailynotes:dailynote_print', kwargs={'pk': self.dailynote1.pk})
        self.assertContains(response, print_url)


class PerformanceTests(DailyNoteIntegrationTestCase):
    """Test performance aspects of Slice 5 features."""
    
    def test_patient_list_query_optimization(self):
        """Test that patient daily note list view uses optimized queries."""
        self.client.login(username="doctor", password="testpass123")
        
        url = reverse('dailynotes:patient_dailynote_list', kwargs={'patient_pk': self.patient1.pk})
        
        # Use Django's database query counting to ensure we're not making excessive queries
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            connection.queries_log.clear()
            response = self.client.get(url)
            query_count = len(connection.queries)
            
            self.assertEqual(response.status_code, 200)
            # Should not exceed reasonable query count (allowing for auth, session, etc.)
            self.assertLess(query_count, 10)
    
    def test_dashboard_widget_performance(self):
        """Test that dashboard widgets don't cause excessive queries."""
        request = type('Request', (), {})()
        request.user = self.doctor
        
        context = {'request': request}
        
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            connection.queries_log.clear()
            result = recent_dailynotes_widget(context, limit=5)
            query_count = len(connection.queries)
            
            self.assertIn('recent_dailynotes', result)
            # Widget should be efficient - no more than 2-3 queries
            self.assertLess(query_count, 4)