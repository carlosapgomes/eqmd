from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from django.http import JsonResponse
from datetime import date, timedelta
from unittest.mock import patch, Mock

from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.outpatientprescriptions.forms.prescription_forms import OutpatientPrescriptionForm
from apps.sample_content.models import SampleContent
from apps.events.models import Event

User = get_user_model()


class OutpatientPrescriptionListViewTest(TestCase):
    """Test cases for OutpatientPrescriptionListView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            profession=1  # Doctor
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        # Create prescriptions
        cls.prescription1 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Prescription 1',
            instructions='Instructions 1',
            status='draft',
            prescription_date=date.today(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.prescription2 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=1),
            description='Prescription 2',
            instructions='Instructions 2',
            status='finalized',
            prescription_date=date.today() - timedelta(days=1),
            patient=cls.patient,
            created_by=cls.user2,
            updated_by=cls.user2
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='user1', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_view_url_accessible_by_name(self):
        """Test that view is accessible by name."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_list.html')

    def test_view_shows_accessible_prescriptions(self):
        """Test that view shows only accessible prescriptions."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        prescriptions = response.context['prescriptions']
        
        # Should see prescriptions accessible to user1
        self.assertIn(self.prescription1, prescriptions)
        # Access to prescription2 depends on patient access rules

    def test_view_search_functionality(self):
        """Test search functionality."""
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'search': 'Prescription 1'}
        )
        prescriptions = response.context['prescriptions']
        
        # Should find prescription1 by description
        self.assertIn(self.prescription1, prescriptions)

    def test_view_patient_filter(self):
        """Test patient filter functionality."""
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'patient': str(self.patient.id)}
        )
        prescriptions = response.context['prescriptions']
        
        # Should show prescriptions for the specific patient
        for prescription in prescriptions:
            self.assertEqual(prescription.patient, self.patient)

    def test_view_status_filter(self):
        """Test status filter functionality."""
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'status': 'draft'}
        )
        prescriptions = response.context['prescriptions']
        
        # Should show only draft prescriptions
        for prescription in prescriptions:
            self.assertEqual(prescription.status, 'draft')

    def test_view_date_range_filter(self):
        """Test date range filter functionality."""
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {
                'date_start': start_date.strftime('%Y-%m-%d'),
                'date_end': end_date.strftime('%Y-%m-%d')
            }
        )
        prescriptions = response.context['prescriptions']
        
        # Should show prescriptions within date range
        for prescription in prescriptions:
            self.assertTrue(start_date <= prescription.prescription_date <= end_date)

    def test_view_pagination(self):
        """Test pagination functionality."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        self.assertIn('is_paginated', response.context)
        self.assertIn('page_obj', response.context)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        self.assertRedirects(response, '/accounts/login/?next=/outpatientprescriptions/')

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_view_respects_patient_access_permissions(self, mock_can_access):
        """Test that view respects patient access permissions."""
        mock_can_access.return_value = False
        
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        prescriptions = response.context['prescriptions']
        
        # Should show empty queryset if no patient access
        self.assertEqual(len(prescriptions), 0)


class OutpatientPrescriptionDetailViewTest(TestCase):
    """Test cases for OutpatientPrescriptionDetailView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            profession=1  # Doctor
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        # Add prescription items
        PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name='Drug A',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily',
            quantity='30',
            order=1
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='user1', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_view_accessible_with_patient_access(self, mock_can_access):
        """Test that view is accessible when user has patient access."""
        mock_can_access.return_value = True
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['outpatientprescription'], self.prescription)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_view_not_accessible_without_patient_access(self, mock_can_access):
        """Test that view is not accessible without patient access."""
        mock_can_access.return_value = False
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail', 
                       kwargs={'pk': self.prescription.pk})
            )
            self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_detail.html')

    def test_view_shows_prescription_items(self):
        """Test that view shows prescription items."""
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail', 
                       kwargs={'pk': self.prescription.pk})
            )
            prescription = response.context['outpatientprescription']
            self.assertEqual(prescription.items.count(), 1)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertRedirects(
            response, 
            f'/accounts/login/?next=/outpatientprescriptions/{self.prescription.pk}/'
        )


class OutpatientPrescriptionCreateViewTest(TestCase):
    """Test cases for OutpatientPrescriptionCreateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create sample content
        cls.sample_content = SampleContent.objects.create(
            title='Sample Prescription Content',
            content='Sample prescription instructions',
            event_type=Event.OUTPT_PRESCRIPTION_EVENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_view_accessible_to_authenticated_users(self):
        """Test that view is accessible to authenticated users."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_create.html')

    def test_view_uses_correct_form(self):
        """Test that view uses correct form class."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertIsInstance(response.context['form'], OutpatientPrescriptionForm)

    def test_view_provides_formset_context(self):
        """Test that view provides formset in context."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertIn('formset', response.context)
        self.assertIn('formset_helper', response.context)

    def test_view_provides_sample_content(self):
        """Test that view provides sample content in context."""
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        sample_contents = response.context['sample_contents']
        self.assertIn(self.sample_content, sample_contents)

    def test_post_creates_prescription_with_items(self):
        """Test that POST request creates prescription with items."""
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription creation',
            'instructions': 'Take all medications as prescribed',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Formset data
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Paracetamol',
            'form-0-presentation': '500mg comprimidos',
            'form-0-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas',
            'form-0-quantity': '21 comprimidos',
            'form-0-order': '1',
            
            'form-1-drug_name': 'Ibuprofeno',
            'form-1-presentation': '400mg comprimidos',
            'form-1-usage_instructions': 'Tomar 1 comprimido se dor',
            'form-1-quantity': '10 comprimidos',
            'form-1-order': '2',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            form_data
        )
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that prescription was created
        prescription = OutpatientPrescription.objects.get(
            description='Test prescription creation'
        )
        self.assertEqual(prescription.created_by, self.user)
        self.assertEqual(prescription.items.count(), 2)

    def test_post_invalid_form_shows_errors(self):
        """Test that POST with invalid data shows form errors."""
        form_data = {
            'patient': '',  # Missing required field
            'description': 'Test prescription',
            'instructions': 'Test instructions',
            
            # Valid formset data
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Paracetamol',
            'form-0-presentation': '500mg comprimidos',
            'form-0-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas',
            'form-0-quantity': '21 comprimidos',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            form_data
        )
        
        # Should stay on form page
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'patient', 'This field is required.')

    def test_post_invalid_formset_shows_errors(self):
        """Test that POST with invalid formset shows errors."""
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription',
            'instructions': 'Test instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Invalid formset data - missing required fields
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': '',  # Missing required field
            'form-0-presentation': '',  # Missing required field
            'form-0-usage_instructions': '',  # Missing required field
            'form-0-quantity': '',  # Missing required field
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            form_data
        )
        
        # Should stay on form page
        self.assertEqual(response.status_code, 200)
        
        # Check that formset has errors
        formset = response.context['formset']
        self.assertFalse(formset.is_valid())

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertRedirects(
            response, 
            '/accounts/login/?next=/outpatientprescriptions/create/'
        )


class OutpatientPrescriptionUpdateViewTest(TestCase):
    """Test cases for OutpatientPrescriptionUpdateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            profession=1  # Doctor
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1
        )

        # Add prescription item
        cls.item = PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name='Drug A',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily',
            quantity='30',
            order=1
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='user1', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_view_accessible_with_edit_permission(self, mock_can_edit):
        """Test that view is accessible when user has edit permission."""
        mock_can_edit.return_value = True
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_view_not_accessible_without_edit_permission(self, mock_can_edit):
        """Test that view is not accessible without edit permission."""
        mock_can_edit.return_value = False
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch('apps.core.permissions.utils.can_edit_event', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update', 
                       kwargs={'pk': self.prescription.pk})
            )
            self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_update.html')

    @patch('apps.core.permissions.utils.can_edit_event')
    def test_post_updates_prescription(self, mock_can_edit):
        """Test that POST request updates prescription."""
        mock_can_edit.return_value = True
        
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Updated prescription description',
            'instructions': 'Updated instructions',
            'status': 'finalized',
            'prescription_date': date.today(),
            
            # Formset data for existing item
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-id': str(self.item.pk),
            'form-0-drug_name': 'Updated Drug A',
            'form-0-presentation': '20mg tablet',
            'form-0-usage_instructions': 'Take 2 daily',
            'form-0-quantity': '60',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_update', 
                   kwargs={'pk': self.prescription.pk}),
            form_data
        )
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Check that prescription was updated
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.description, 'Updated prescription description')
        self.assertEqual(self.prescription.status, 'finalized')
        
        # Check that item was updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.drug_name, 'Updated Drug A')

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_update', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertRedirects(
            response, 
            f'/accounts/login/?next=/outpatientprescriptions/{self.prescription.pk}/update/'
        )


class OutpatientPrescriptionDeleteViewTest(TestCase):
    """Test cases for OutpatientPrescriptionDeleteView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()
        
        # Create fresh prescription for each test
        self.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_view_accessible_with_delete_permission(self, mock_can_delete):
        """Test that view is accessible when user has delete permission."""
        mock_can_delete.return_value = True
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_view_not_accessible_without_delete_permission(self, mock_can_delete):
        """Test that view is not accessible without delete permission."""
        mock_can_delete.return_value = False
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch('apps.core.permissions.utils.can_delete_event', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_delete', 
                       kwargs={'pk': self.prescription.pk})
            )
            self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_confirm_delete.html')

    @patch('apps.core.permissions.utils.can_delete_event')
    def test_post_deletes_prescription(self, mock_can_delete):
        """Test that POST request deletes prescription."""
        mock_can_delete.return_value = True
        prescription_id = self.prescription.id
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_delete', 
                   kwargs={'pk': self.prescription.pk})
        )
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Check that prescription was deleted
        self.assertFalse(OutpatientPrescription.objects.filter(id=prescription_id).exists())

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_delete', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertRedirects(
            response, 
            f'/accounts/login/?next=/outpatientprescriptions/{self.prescription.pk}/delete/'
        )


class OutpatientPrescriptionPrintViewTest(TestCase):
    """Test cases for OutpatientPrescriptionPrintView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription for Print',
            instructions='Print test instructions',
            status='finalized',
            prescription_date=date.today(),
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

        # Add prescription items
        PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name='Print Drug A',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily for print test',
            quantity='30',
            order=1
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_view_accessible_with_patient_access(self, mock_can_access):
        """Test that view is accessible when user has patient access."""
        mock_can_access.return_value = True
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_print', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_view_not_accessible_without_patient_access(self, mock_can_access):
        """Test that view is not accessible without patient access."""
        mock_can_access.return_value = False
        
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_print', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_print', 
                       kwargs={'pk': self.prescription.pk})
            )
            self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_print.html')

    def test_view_shows_prescription_data(self):
        """Test that view shows prescription data for printing."""
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_print', 
                       kwargs={'pk': self.prescription.pk})
            )
            
            prescription = response.context['outpatientprescription']
            self.assertEqual(prescription, self.prescription)
            self.assertEqual(prescription.items.count(), 1)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_print', 
                   kwargs={'pk': self.prescription.pk})
        )
        self.assertRedirects(
            response, 
            f'/accounts/login/?next=/outpatientprescriptions/{self.prescription.pk}/print/'
        )


class ViewIntegrationTest(TestCase):
    """Integration tests for view workflows."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Set up hospital context in session
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_complete_prescription_crud_workflow(self):
        """Test complete CRUD workflow for prescriptions."""
        # Create
        create_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Workflow Test Prescription',
            'instructions': 'Complete workflow test instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Formset data
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Workflow Drug',
            'form-0-presentation': '10mg tablet',
            'form-0-usage_instructions': 'Take 1 daily for workflow test',
            'form-0-quantity': '30',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            create_data
        )
        self.assertEqual(response.status_code, 302)
        
        # Get the created prescription
        prescription = OutpatientPrescription.objects.get(
            description='Workflow Test Prescription'
        )
        
        # Read (Detail view)
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail', 
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['outpatientprescription'], prescription)
        
        # Update
        update_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Updated Workflow Test Prescription',
            'instructions': 'Updated workflow test instructions',
            'status': 'finalized',
            'prescription_date': date.today(),
            
            # Formset data for existing item
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-id': str(prescription.items.first().pk),
            'form-0-drug_name': 'Updated Workflow Drug',
            'form-0-presentation': '20mg tablet',
            'form-0-usage_instructions': 'Take 2 daily for updated workflow test',
            'form-0-quantity': '60',
            'form-0-order': '1',
        }
        
        with patch('apps.core.permissions.utils.can_edit_event', return_value=True):
            response = self.client.post(
                reverse('outpatientprescriptions:outpatientprescription_update', 
                       kwargs={'pk': prescription.pk}),
                update_data
            )
            self.assertEqual(response.status_code, 302)
        
        # Verify update
        prescription.refresh_from_db()
        self.assertEqual(prescription.description, 'Updated Workflow Test Prescription')
        self.assertEqual(prescription.status, 'finalized')
        
        # Print view
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_print', 
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)
        
        # Delete
        with patch('apps.core.permissions.utils.can_delete_event', return_value=True):
            response = self.client.post(
                reverse('outpatientprescriptions:outpatientprescription_delete', 
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 302)
        
        # Verify deletion
        self.assertFalse(OutpatientPrescription.objects.filter(id=prescription.id).exists())

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_prescription_list_to_detail_workflow(self, mock_can_access):
        """Test workflow from list view to detail view."""
        mock_can_access.return_value = True
        
        # Create prescription
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='List to Detail Test',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test list view
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(prescription, response.context['prescriptions'])
        
        # Test detail view
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_detail', 
                   kwargs={'pk': prescription.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['outpatientprescription'], prescription)