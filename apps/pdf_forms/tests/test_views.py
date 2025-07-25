from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from unittest.mock import patch, MagicMock
from apps.patients.models import Patient
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, PDFFormSubmissionFactory, UserFactory, PatientFactory

User = get_user_model()


class PDFFormTemplateListViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_template_list_view_requires_login(self):
        """Test that template list view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_template_list_view_displays_active_templates(self):
        """Test that only active templates are displayed."""
        active_template = PDFFormTemplateFactory(
            name="Active Template",
            is_active=True,
            created_by=self.user
        )
        inactive_template = PDFFormTemplateFactory(
            name="Inactive Template",
            is_active=False,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, active_template.name)
        self.assertNotContains(response, inactive_template.name)

    def test_template_list_view_hospital_specific_only(self):
        """Test that only hospital-specific templates are shown."""
        hospital_template = PDFFormTemplateFactory(
            name="Hospital Template",
            hospital_specific=True,
            created_by=self.user
        )
        general_template = PDFFormTemplateFactory(
            name="General Template",
            hospital_specific=False,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, hospital_template.name)
        self.assertNotContains(response, general_template.name)

    def test_template_list_pagination(self):
        """Test pagination on template list."""
        # Create 25 templates (more than default paginate_by=20)
        templates = []
        for i in range(25):
            templates.append(PDFFormTemplateFactory(
                name=f"Template {i:02d}",
                created_by=self.user
            ))
        
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['form_templates']), 20)


class PDFFormSelectViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.client.force_login(self.user)

    def test_form_select_view_requires_login(self):
        """Test that form select view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_form_select_view_with_valid_patient(self):
        """Test form selection view with valid patient."""
        template = PDFFormTemplateFactory(created_by=self.user)
        
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.name)
        self.assertContains(response, template.name)
        self.assertEqual(response.context['patient'], self.patient)

    def test_form_select_view_with_invalid_patient(self):
        """Test form selection view with invalid patient ID."""
        import uuid
        invalid_id = uuid.uuid4()
        
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': invalid_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.pdf_forms.views.can_access_patient')
    def test_form_select_view_permission_denied(self, mock_can_access):
        """Test permission denied for form selection."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)

    def test_form_select_view_no_available_forms(self):
        """Test view when no forms are available."""
        # Deactivate all templates
        PDFFormTemplate.objects.update(is_active=False)
        
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum formulário PDF disponível")


class PDFFormFillViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.client.force_login(self.user)

    def test_form_fill_view_requires_login(self):
        """Test that form fill view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_form_fill_view_get_success(self):
        """Test successful GET request to form fill view."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form_template'], self.template)
        self.assertEqual(response.context['patient'], self.patient)
        self.assertContains(response, self.template.name)
        self.assertContains(response, self.patient.name)

    def test_form_fill_view_invalid_template(self):
        """Test form fill view with invalid template ID."""
        import uuid
        invalid_id = uuid.uuid4()
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': invalid_id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_form_fill_view_inactive_template(self):
        """Test form fill view with inactive template."""
        self.template.is_active = False
        self.template.save()
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.pdf_forms.views.can_access_patient')
    def test_form_fill_view_permission_denied(self, mock_can_access):
        """Test permission denied for form fill."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)

    @patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.fill_form')
    @patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class')
    def test_form_fill_view_post_success(self, mock_generate_form, mock_fill_form):
        """Test successful form submission."""
        # Mock form class
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.cleaned_data = {
            'patient_name': self.patient.name,
            'clinical_notes': 'Test notes'
        }
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class
        
        # Mock PDF generation
        mock_pdf_content = MagicMock()
        mock_pdf_content.read.return_value = b'fake pdf content'
        mock_fill_form.return_value = mock_pdf_content
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        # Submit form data
        form_data = {
            'patient_name': self.patient.name,
            'clinical_notes': 'Test notes'
        }
        
        response = self.client.post(url, form_data)
        
        # Should redirect to submission detail after success
        self.assertEqual(response.status_code, 302)
        
        # Check that submission was created
        submission = PDFFormSubmission.objects.filter(
            form_template=self.template,
            patient=self.patient
        ).first()
        self.assertIsNotNone(submission)


class PDFFormSubmissionDetailViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        self.client.force_login(self.user)

    def test_submission_detail_view_requires_login(self):
        """Test that submission detail view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': self.submission.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_submission_detail_view_success(self):
        """Test successful access to submission detail."""
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': self.submission.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['submission'], self.submission)
        self.assertContains(response, self.submission.form_template.name)
        self.assertContains(response, self.submission.patient.name)

    def test_submission_detail_view_invalid_id(self):
        """Test submission detail view with invalid ID."""
        import uuid
        invalid_id = uuid.uuid4()
        
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': invalid_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.pdf_forms.views.can_access_patient')
    def test_submission_detail_view_permission_denied(self, mock_can_access):
        """Test permission denied for submission detail."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': self.submission.pk})
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)


class PDFFormDownloadViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        self.client.force_login(self.user)

    def test_pdf_download_view_requires_login(self):
        """Test that PDF download view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_pdf_download_view_invalid_id(self):
        """Test PDF download view with invalid submission ID."""
        import uuid
        invalid_id = uuid.uuid4()
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': invalid_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.pdf_forms.views.can_access_patient')
    def test_pdf_download_view_permission_denied(self, mock_can_access):
        """Test permission denied for PDF download."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)

    def test_pdf_download_view_no_file(self):
        """Test PDF download when no file is attached."""
        # Create submission without generated_pdf
        submission = PDFFormSubmission.objects.create(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data={'test': 'data'},
            original_filename='test.pdf',
            file_size=1024
        )
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission.id})
        
        with self.assertRaises(Http404):
            self.client.get(url)


class PDFFormViewIntegrationTests(TestCase):
    """Integration tests for PDF form views workflow."""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(
            name="Integration Test Form",
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                    'max_length': 100
                },
                'notes': {
                    'type': 'textarea',
                    'required': False,
                    'label': 'Clinical Notes'
                }
            },
            created_by=self.user
        )
        self.client.force_login(self.user)

    def test_complete_form_workflow(self):
        """Test complete workflow from selection to submission."""
        # Step 1: Select form for patient
        select_url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        select_response = self.client.get(select_url)
        
        self.assertEqual(select_response.status_code, 200)
        self.assertContains(select_response, self.template.name)
        
        # Step 2: Fill form
        fill_url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        fill_response = self.client.get(fill_url)
        
        self.assertEqual(fill_response.status_code, 200)
        self.assertContains(fill_response, 'Patient Name')
        self.assertContains(fill_response, 'Clinical Notes')

    def test_form_navigation_links(self):
        """Test navigation links between views."""
        # Test that form select links to form fill
        select_url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        select_response = self.client.get(select_url)
        
        expected_fill_url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        self.assertContains(select_response, expected_fill_url)
        
        # Test that form fill links back to form select
        fill_response = self.client.get(expected_fill_url)
        self.assertContains(fill_response, select_url)

    def test_context_data_consistency(self):
        """Test that context data is consistent across views."""
        # All views should have consistent patient and template data
        select_url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        fill_url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        select_response = self.client.get(select_url)
        fill_response = self.client.get(fill_url)
        
        # Patient data should be consistent
        self.assertEqual(select_response.context['patient'], self.patient)
        self.assertEqual(fill_response.context['patient'], self.patient)
        
        # Template data should be accessible
        self.assertIn(self.template, select_response.context['form_templates'])
        self.assertEqual(fill_response.context['form_template'], self.template)