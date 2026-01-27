from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from unittest.mock import patch, MagicMock
from apps.patients.models import Patient
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, PDFFormSubmissionFactory, UserFactory, PatientFactory, SuperUserFactory

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

    def test_form_fill_view_includes_procedure_search(self):
        """Test procedure search assets render when naming convention is used."""
        template = PDFFormTemplateFactory(
            created_by=self.user,
            form_fields={
                'procedure_code': {
                    'type': 'text',
                    'required': True,
                    'label': 'Procedure Code'
                },
                'procedure_description': {
                    'type': 'text',
                    'required': True,
                    'label': 'Procedure Description'
                }
            }
        )

        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': template.id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pdf_forms_procedure_search.js")
        self.assertContains(response, "/api/procedures/search/")
        self.assertContains(response, "procedure-search-input")

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

    @patch('apps.pdf_forms.permissions.can_access_patient')
    def test_form_fill_view_permission_denied(self, mock_can_access):
        """Test permission denied for form fill."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Permission denied

    @patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class')
    def test_form_fill_view_post_success(self, mock_generate_form):
        """Test successful form submission with data-only approach."""
        # Mock form class
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'patient_name': self.patient.name,
            'clinical_notes': 'Test notes'
        }
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class
        
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
        
        # Check that submission was created with form_data only
        submission = PDFFormSubmission.objects.filter(
            form_template=self.template,
            patient=self.patient
        ).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.form_data, mock_form_instance.cleaned_data)
        # Only form data should be stored (no generated PDF file)
        self.assertTrue(hasattr(submission, 'form_data'))
        self.assertEqual(len(submission.form_data), len(mock_form_instance.cleaned_data))

    @patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class')
    def test_form_fill_view_post_validation_error(self, mock_generate_form):
        """Test form submission with validation error."""
        # Mock form class with validation error
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {'field_name': ['This field is required']}
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        form_data = {'patient_name': ''}  # Invalid data
        
        response = self.client.post(url, form_data)
        
        # Should re-render form with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_form_instance.is_valid.called)

    @patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class')
    def test_form_fill_view_post_exception_handling(self, mock_generate_form):
        """Test form submission with exception handling."""
        # Mock form class that raises exception
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.side_effect = Exception("Unexpected error")
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        form_data = {'patient_name': 'Test Patient'}
        
        response = self.client.post(url, form_data)
        
        # Should handle exception and show error message
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('Erro ao processar formulário' in str(msg) for msg in messages))

    def test_form_fill_view_get_initial_patient_values(self):
        """Test that patient initial values are properly set via get_initial()."""
        # Use a template with proper form fields that will work with the real form generator
        template = PDFFormTemplateFactory(
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'label': 'Patient Name',
                    'required': True,
                    'max_length': 100,
                    'patient_field_mapping': 'name'  # Map to patient.name
                }
            },
            created_by=self.user
        )
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': template.id,
            'patient_id': self.patient.id
        })
        
        response = self.client.get(url)
        
        # Verify the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Verify that the form has the initial values from patient data
        form = response.context['form']
        # The initial value should be set from the patient's name via get_initial()
        self.assertEqual(form.initial.get('patient_name'), self.patient.name)

    def test_form_fill_view_template_without_fields(self):
        """Test form fill view with template that has no fields configured."""
        template = PDFFormTemplateFactory(
            form_fields={},  # Empty fields
            created_by=self.user
        )
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': template.id,
            'patient_id': self.patient.id
        })
        
        # Should still work, even with empty fields
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_form_fill_view_template_with_null_fields(self):
        """Test form fill view with template that has empty form_fields."""
        template = PDFFormTemplateFactory(
            form_fields={},  # Empty fields
            created_by=self.user
        )
        
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': template.id,
            'patient_id': self.patient.id
        })
        
        # Should still work, even with null fields
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


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

    @patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response')
    def test_pdf_download_view_generates_pdf_on_demand(self, mock_generate_pdf):
        """Test PDF download generates PDF on-demand from form data."""
        from django.http import HttpResponse
        
        # Mock PDF generation response
        mock_response = HttpResponse(
            b'fake pdf content',
            content_type='application/pdf'
        )
        mock_response['Content-Disposition'] = 'attachment; filename="test_form.pdf"'
        mock_generate_pdf.return_value = mock_response
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        response = self.client.get(url)
        
        # Should return the generated PDF response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Verify PDF generation was called with correct parameters
        mock_generate_pdf.assert_called_once()
        call_args = mock_generate_pdf.call_args
        self.assertEqual(call_args[1]['form_data'], self.submission.form_data)
        self.assertEqual(call_args[1]['field_config'], self.submission.form_template.form_fields)

    @patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response')
    def test_pdf_download_view_generation_error(self, mock_generate_pdf):
        """Test PDF download when generation fails."""
        # Mock PDF generation failure
        mock_generate_pdf.side_effect = Exception("PDF generation failed")
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        
        # Should handle the error gracefully (404 or 500 depending on implementation)
        response = self.client.get(url)
        self.assertIn(response.status_code, [404, 500])

    @patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response')
    def test_pdf_download_view_corrupted_form_data(self, mock_generate_pdf):
        """Test PDF download with corrupted form data."""
        # Create submission with invalid form data
        self.submission.form_data = {'invalid': None, 'corrupted': {'nested': {'too': 'deep'}}}
        self.submission.save()
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        
        # Should attempt generation even with corrupted data
        mock_generate_pdf.return_value = HttpResponse(b'pdf', content_type='application/pdf')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        mock_generate_pdf.assert_called_once()

    @patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response')
    def test_pdf_download_view_streaming_headers(self, mock_generate_pdf):
        """Test that proper streaming headers are set for PDF download."""
        from django.http import HttpResponse
        
        mock_response = HttpResponse(
            b'fake pdf content streaming',
            content_type='application/pdf'
        )
        mock_response['Content-Disposition'] = 'attachment; filename="streamed_form.pdf"'
        mock_response['Content-Length'] = str(len(b'fake pdf content streaming'))
        mock_generate_pdf.return_value = mock_response
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': self.submission.id})
        response = self.client.get(url)
        
        # Verify streaming response headers
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Content-Length', response)
        self.assertEqual(response.status_code, 200)


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


class PDFFormViewErrorHandlingTests(TestCase):
    """Tests for error handling in PDF form views."""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.client.force_login(self.user)

    def test_template_list_view_no_templates(self):
        """Test template list view when no templates are available."""
        # Delete all templates
        PDFFormTemplate.objects.all().delete()
        
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form_templates']), 0)

    def test_form_select_view_permission_check_exception(self):
        """Test form select view when permission check raises exception."""
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        
        with patch('apps.pdf_forms.views.check_pdf_form_access') as mock_check:
            mock_check.side_effect = Exception("Permission check failed")
            
            with self.assertRaises(Exception):
                self.client.get(url)

    def test_form_fill_view_get_form_class_exception(self):
        """Test form fill view when form generation fails."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        with patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class') as mock_generate:
            mock_generate.side_effect = Exception("Form generation failed")
            
            with self.assertRaises(Exception):
                self.client.get(url)

    def test_submission_detail_view_can_delete_permission_error(self):
        """Test submission detail view when can_delete permission check fails."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': submission.pk})
        
        with patch('apps.pdf_forms.views.can_delete_event') as mock_can_delete:
            mock_can_delete.side_effect = Exception("Permission check failed")
            
            # Should still work, just without can_delete in context
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('can_delete_submission', response.context)

    def test_pdf_download_view_form_data_validation(self):
        """Test PDF download view with various form data states."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission.id})
        
        # Test with empty form_data
        submission.form_data = {}
        submission.save()
        
        with patch('apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response') as mock_generate:
            mock_generate.return_value = HttpResponse(b'pdf', content_type='application/pdf')
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            
            # Should still attempt generation even with empty data
            mock_generate.assert_called_once()

    def test_pdf_download_view_template_file_validation(self):
        """Test PDF download view template file validation."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission.id})
        
        # Test with template that has no PDF file
        original_file = submission.form_template.pdf_file
        submission.form_template.pdf_file = None
        submission.form_template.save()
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        
        # Restore file
        submission.form_template.pdf_file = original_file
        submission.form_template.save()

    def test_pdf_download_view_security_validation_error(self):
        """Test PDF download view security validation error."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission.id})
        
        with patch('apps.pdf_forms.security.PDFFormSecurity.validate_file_path') as mock_validate:
            mock_validate.side_effect = ValidationError("Security validation failed")
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_delete_view_get_object_permission_denied(self):
        """Test delete view when get_object raises PermissionDenied."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': submission.pk})
        
        with patch('apps.pdf_forms.views.can_access_patient') as mock_can_access:
            mock_can_access.return_value = False
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_view_context_data_missing_keys(self):
        """Test views handle missing context keys gracefully."""
        # Test template list view
        url = reverse('pdf_forms:template_list')
        response = self.client.get(url)
        
        # Should have expected context keys
        self.assertIn('form_templates', response.context)
        self.assertIn('is_paginated', response.context)
        
        # Test form select view
        select_url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        select_response = self.client.get(select_url)
        
        self.assertIn('patient', select_response.context)
        self.assertIn('form_templates', select_response.context)

    def test_view_dispatch_method_exceptions(self):
        """Test view dispatch method exception handling."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        # Test when get_object raises Http404
        with patch.object(PDFFormFillView, 'get_object') as mock_get_object:
            mock_get_object.side_effect = Http404("Template not found")
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_form_valid_method_exception_handling(self):
        """Test form_valid method exception handling."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        
        with patch('apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class') as mock_generate:
            mock_form_class = MagicMock()
            mock_form_instance = MagicMock()
            mock_form_instance.is_valid.return_value = True
            mock_form_instance.cleaned_data = {'test': 'data'}
            mock_form_class.return_value = mock_form_instance
            mock_generate.return_value = mock_form_class
            
            # Mock PDFFormSubmission.save to raise exception
            with patch.object(PDFFormSubmission, 'save') as mock_save:
                mock_save.side_effect = Exception("Database error")
                
                response = self.client.post(url, {'test': 'data'})
                
                # Should handle exception and show error message
                self.assertEqual(response.status_code, 200)
                messages = list(response.context['messages'])
                self.assertTrue(any('Erro ao processar formulário' in str(msg) for msg in messages))


class PDFFormSubmissionDeleteViewTests(TestCase):
    """Tests for PDFFormSubmissionDeleteView."""
    
    def setUp(self):
        self.client = Client()
        self.user = SuperUserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        self.client.force_login(self.user)

    def test_delete_view_requires_login(self):
        """Test that delete view requires authentication."""
        self.client.logout()
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_delete_view_get_success(self):
        """Test successful GET request to delete confirmation page."""
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['submission'], self.submission)
        self.assertContains(response, self.submission.form_template.name)
        self.assertContains(response, self.submission.patient.name)

    def test_delete_view_post_success(self):
        """Test successful POST request to delete submission."""
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        
        # Ensure submission exists before deletion
        self.assertTrue(PDFFormSubmission.objects.filter(pk=self.submission.pk).exists())
        
        response = self.client.post(url)
        
        # Should redirect to patient timeline
        self.assertEqual(response.status_code, 302)
        expected_redirect = reverse('apps.patients:patient_events_timeline', kwargs={'patient_id': self.patient.pk})
        self.assertEqual(response.url, expected_redirect)
        
        # Verify submission was deleted
        self.assertFalse(PDFFormSubmission.objects.filter(pk=self.submission.pk).exists())

    def test_delete_view_invalid_id(self):
        """Test delete view with invalid submission ID."""
        import uuid
        invalid_id = uuid.uuid4()
        
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': invalid_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.pdf_forms.views.can_access_patient')
    def test_delete_view_permission_denied_patient_access(self, mock_can_access):
        """Test permission denied when user cannot access patient."""
        mock_can_access.return_value = False
        
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)

    @patch('apps.pdf_forms.views.can_delete_event')
    def test_delete_view_permission_denied_delete_permission(self, mock_can_delete):
        """Test permission denied when user cannot delete event."""
        mock_can_delete.return_value = False
        
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        
        with self.assertRaises(PermissionDenied):
            self.client.get(url)

    def test_delete_view_success_message(self):
        """Test that success message is displayed after deletion."""
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        
        response = self.client.post(url, follow=False)
        
        # Should redirect to patient timeline
        self.assertEqual(response.status_code, 302)
        
        # Follow redirect to check messages
        redirect_response = self.client.get(response.url, follow=True)
        messages = list(redirect_response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('excluído com sucesso', str(messages[0]))
        self.assertEqual(messages[0].level_tag, 'success')

    def test_delete_view_queryset_optimization(self):
        """Test that queryset is optimized with select_related."""
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        
        with self.assertNumQueries(1):  # Should be optimized with select_related
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Verify related objects are loaded
        submission = response.context['submission']
        self.assertTrue(hasattr(submission, '_patient_cache'))
        self.assertTrue(hasattr(submission, '_created_by_cache'))
        self.assertTrue(hasattr(submission, '_form_template_cache'))

    def test_delete_view_context_object_name(self):
        """Test that context object name is correctly set."""
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': self.submission.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('submission', response.context)
        self.assertEqual(response.context['submission'], self.submission)
