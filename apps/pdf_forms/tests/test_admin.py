from django.test import TestCase, Client
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from unittest.mock import patch, MagicMock, mock_open
import json
from apps.pdf_forms.admin import PDFFormTemplateAdmin, PDFFormSubmissionAdmin
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.pdf_forms.tests.factories import (
    UserFactory, SuperUserFactory, PatientFactory, 
    PDFFormTemplateFactory, PDFFormSubmissionFactory
)

User = get_user_model()


class PDFFormTemplateAdminTests(TestCase):
    """Test PDFFormTemplateAdmin functionality."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = PDFFormTemplateAdmin(PDFFormTemplate, self.site)
        self.user = SuperUserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_admin_list_display(self):
        """Test admin list display configuration."""
        expected_list_display = [
            'name', 'configuration_status_display', 'hospital_specific', 
            'is_active', 'created_at', 'pdf_preview', 'configure_fields'
        ]
        self.assertEqual(self.admin.list_display, expected_list_display)

    def test_admin_list_filter(self):
        """Test admin list filter configuration."""
        expected_list_filter = ['hospital_specific', 'is_active', 'created_at']
        self.assertEqual(self.admin.list_filter, expected_list_filter)

    def test_admin_search_fields(self):
        """Test admin search fields configuration."""
        expected_search_fields = ['name', 'description']
        self.assertEqual(self.admin.search_fields, expected_search_fields)

    def test_admin_readonly_fields(self):
        """Test admin readonly fields configuration."""
        expected_readonly = ['created_at', 'updated_at', 'created_by', 'updated_by']
        self.assertEqual(self.admin.readonly_fields, expected_readonly)

    def test_admin_fieldsets(self):
        """Test admin fieldsets configuration."""
        fieldsets = self.admin.fieldsets
        
        # Should have 4 fieldsets
        self.assertEqual(len(fieldsets), 4)
        
        # Check fieldset titles
        fieldset_titles = [fs[0] for fs in fieldsets]
        self.assertIn('Basic Information', fieldset_titles)
        self.assertIn('Field Configuration', fieldset_titles)
        self.assertIn('Settings', fieldset_titles)
        self.assertIn('Audit', fieldset_titles)

    def test_pdf_preview_method_with_file(self):
        """Test pdf_preview method with PDF file."""
        result = self.admin.pdf_preview(self.template)
        
        # Should return HTML with link
        self.assertIn('href', result)
        self.assertIn('target="_blank"', result)
        self.assertIn('View PDF', result)

    def test_pdf_preview_method_without_file(self):
        """Test pdf_preview method without PDF file."""
        template = PDFFormTemplateFactory()
        template.pdf_file = None
        result = self.admin.pdf_preview(template)
        
        # Should return "No PDF"
        self.assertEqual(result, "No PDF")

    def test_configuration_status_display_methods(self):
        """Test configuration_status_display method."""
        # Test with no PDF - create template and manually set pdf_file to None
        template1 = PDFFormTemplateFactory()
        template1.pdf_file = None
        result1 = self.admin.configuration_status_display(template1)
        self.assertIn('Sem PDF', result1)
        self.assertIn('style="color: red;"', result1)
        
        # Test with PDF but no configuration
        template2 = PDFFormTemplateFactory(form_fields={})
        result2 = self.admin.configuration_status_display(template2)
        self.assertIn('Não configurado', result2)
        self.assertIn('style="color: orange;"', result2)
        
        # Test with configured template
        template3 = PDFFormTemplateFactory(form_fields={'field1': {'type': 'text', 'label': 'Field 1'}})
        result3 = self.admin.configuration_status_display(template3)
        self.assertIn('Configurado', result3)
        self.assertIn('style="color: green;"', result3)

    def test_configure_fields_method_with_file(self):
        """Test configure_fields method with PDF file."""
        result = self.admin.configure_fields(self.template)
        
        # Should return HTML with link
        self.assertIn('href', result)
        self.assertIn('class="button"', result)
        self.assertIn('Editar Campos', result)  # Since it's configured

    def test_configure_fields_method_without_file(self):
        """Test configure_fields method without PDF file."""
        template = PDFFormTemplateFactory()
        template.pdf_file = None
        result = self.admin.configure_fields(template)
        
        # Should return "Upload PDF first"
        self.assertEqual(result, "Upload PDF first")

    def test_configure_fields_method_unconfigured(self):
        """Test configure_fields method with unconfigured template."""
        template = PDFFormTemplateFactory(form_fields={})
        result = self.admin.configure_fields(template)
        
        # Should return HTML with warning style
        self.assertIn('href', result)
        self.assertIn('style="background-color: #ffc107; color: #000;"', result)
        self.assertIn('Configurar Campos', result)

    def test_save_model_new_template(self):
        """Test save_model for new template."""
        template = PDFFormTemplate(name="New Template")
        
        # Mock request
        request = MagicMock()
        request.user = self.user
        
        self.admin.save_model(request, template, None, change=False)
        
        # Should set created_by and updated_by
        self.assertEqual(template.created_by, self.user)
        self.assertEqual(template.updated_by, self.user)

    def test_save_model_existing_template(self):
        """Test save_model for existing template."""
        # Mock request
        request = MagicMock()
        request.user = self.user
        
        self.admin.save_model(request, self.template, None, change=True)
        
        # Should only set updated_by
        self.assertEqual(self.template.updated_by, self.user)

    def test_get_urls_custom_urls(self):
        """Test that custom URLs are added."""
        urls = self.admin.get_urls()
        
        # Should have more URLs than default
        url_patterns = [pattern.pattern for pattern in urls]
        
        # Check for custom URL patterns
        self.assertIn('<path:object_id>/configure-fields/', url_patterns)
        self.assertIn('<path:object_id>/api/pdf-preview/', url_patterns)
        self.assertIn('<path:object_id>/api/save-fields/', url_patterns)

    def test_configure_fields_view_permission_denied(self):
        """Test configure_fields_view with permission denied."""
        # Create regular user (not superuser)
        regular_user = UserFactory()
        self.client.force_login(regular_user)
        
        url = reverse('admin:pdf_forms_pdfformtemplate_configure_fields', args=[self.template.id])
        response = self.client.get(url)
        
        # Should be denied
        self.assertEqual(response.status_code, 403)

    def test_configure_fields_view_success(self):
        """Test successful configure_fields_view."""
        url = reverse('admin:pdf_forms_pdfformtemplate_configure_fields', args=[self.template.id])
        response = self.client.get(url)
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        
        # Check context
        self.assertEqual(response.context['template'], self.template)
        self.assertIn('field_types', response.context)
        self.assertIn('patient_field_options', response.context)

    def test_pdf_preview_api_no_pdf(self):
        """Test pdf_preview_api with no PDF file."""
        template = PDFFormTemplateFactory()
        template.pdf_file = None
        
        url = reverse('admin:pdf_forms_pdfformtemplate_pdf_preview_api', args=[template.id])
        response = self.client.get(url)
        
        # Should return error
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('No PDF file uploaded', data['error'])

    def test_pdf_preview_api_import_error(self):
        """Test pdf_preview_api with pdf2image import error."""
        url = reverse('admin:pdf_forms_pdfformtemplate_pdf_preview_api', args=[self.template.id])
        
        with patch('apps.pdf_forms.admin.convert_from_path', side_effect=ImportError("No module named 'pdf2image'")):
            response = self.client.get(url)
            
            # Should return error with solution
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertIn('pdf2image library', data['error'])
            self.assertIn('solution', data)

    def test_pdf_preview_api_poppler_error(self):
        """Test pdf_preview_api with Poppler error."""
        url = reverse('admin:pdf_forms_pdfformtemplate_pdf_preview_api', args=[self.template.id])
        
        with patch('apps.pdf_forms.admin.convert_from_path', side_effect=Exception("poppler not found")):
            response = self.client.get(url)
            
            # Should return error with poppler solution
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertIn('Poppler', data['error'])
            self.assertIn('alternative', data)

    def test_pdf_preview_api_general_error(self):
        """Test pdf_preview_api with general error."""
        url = reverse('admin:pdf_forms_pdfformtemplate_pdf_preview_api', args=[self.template.id])
        
        with patch('apps.pdf_forms.admin.convert_from_path', side_effect=Exception("General error")):
            response = self.client.get(url)
            
            # Should return error with alternative
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertIn('alternative', data)

    def test_save_fields_api_post_required(self):
        """Test save_fields_api requires POST."""
        url = reverse('admin:pdf_forms_pdfformtemplate_save_fields_api', args=[self.template.id])
        response = self.client.get(url)
        
        # Should return method not allowed
        self.assertEqual(response.status_code, 405)

    def test_save_fields_api_invalid_json(self):
        """Test save_fields_api with invalid JSON."""
        url = reverse('admin:pdf_forms_pdfformtemplate_save_fields_api', args=[self.template.id])
        response = self.client.post(url, data='invalid json', content_type='application/json')
        
        # Should return JSON error
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Invalid JSON data', data['error'])

    def test_save_fields_api_permission_denied(self):
        """Test save_fields_api with permission denied."""
        # Create regular user
        regular_user = UserFactory()
        self.client.force_login(regular_user)
        
        url = reverse('admin:pdf_forms_pdfformtemplate_save_fields_api', args=[self.template.id])
        response = self.client.post(url, data='{}', content_type='application/json')
        
        # Should return permission denied
        self.assertEqual(response.status_code, 403)

    def test_save_fields_api_success(self):
        """Test successful save_fields_api."""
        url = reverse('admin:pdf_forms_pdfformtemplate_save_fields_api', args=[self.template.id])
        
        fields_data = {
            'fields': {
                'patient_name': {
                    'type': 'text',
                    'label': 'Patient Name',
                    'x': 5.0,
                    'y': 10.0
                }
            }
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(fields_data), 
            content_type='application/json'
        )
        
        # Should return success
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check that template was updated
        self.template.refresh_from_db()
        self.assertEqual(self.template.form_fields, fields_data['fields'])

    def test_validate_fields_config_invalid(self):
        """Test validate_fields_config with invalid configuration."""
        invalid_config = {
            'field1': {
                'type': 'invalid_type',
                'label': 'Field 1'
            }
        }
        
        with self.assertRaises(Exception):  # Should raise ValidationError
            self.admin.validate_fields_config(invalid_config)


class PDFFormSubmissionAdminTests(TestCase):
    """Test PDFFormSubmissionAdmin functionality."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = PDFFormSubmissionAdmin(PDFFormSubmission, self.site)
        self.user = SuperUserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )

    def test_admin_list_display(self):
        """Test admin list display configuration."""
        expected_list_display = [
            'form_template', 'patient', 'created_by', 
            'event_datetime', 'form_data_preview'
        ]
        self.assertEqual(self.admin.list_display, expected_list_display)

    def test_admin_list_filter(self):
        """Test admin list filter configuration."""
        expected_list_filter = ['form_template', 'event_datetime', 'created_by']
        self.assertEqual(self.admin.list_filter, expected_list_filter)

    def test_admin_search_fields(self):
        """Test admin search fields configuration."""
        expected_search_fields = ['form_template__name', 'patient__name', 'description']
        self.assertEqual(self.admin.search_fields, expected_search_fields)

    def test_admin_readonly_fields(self):
        """Test admin readonly fields configuration."""
        expected_readonly = ['created_at', 'updated_at', 'event_type']
        self.assertEqual(self.admin.readonly_fields, expected_readonly)

    def test_admin_fieldsets(self):
        """Test admin fieldsets configuration."""
        fieldsets = self.admin.fieldsets
        
        # Should have 3 fieldsets
        self.assertEqual(len(fieldsets), 3)
        
        # Check fieldset titles
        fieldset_titles = [fs[0] for fs in fieldsets]
        self.assertIn('Event Information', fieldset_titles)
        self.assertIn('Form Data', fieldset_titles)
        self.assertIn('Audit', fieldset_titles)

    def test_form_data_preview_method_with_data(self):
        """Test form_data_preview method with form data."""
        self.submission.form_data = {
            'patient_name': 'John Doe',
            'age': 30,
            'notes': 'Test notes'
        }
        self.submission.save()
        
        result = self.admin.form_data_preview(self.submission)
        
        # Should return HTML with field count and preview
        self.assertIn('3 fields:', result)
        self.assertIn('patient_name', result)
        self.assertIn('title=', result)  # Should have title attribute with all field names

    def test_form_data_preview_method_empty_data(self):
        """Test form_data_preview method with empty form data."""
        self.submission.form_data = {}
        self.submission.save()
        
        result = self.admin.form_data_preview(self.submission)
        
        # Should return "Empty"
        self.assertIn('Empty', result)
        self.assertIn('color: #666;', result)

    def test_form_data_preview_method_no_data(self):
        """Test form_data_preview method with no form data."""
        self.submission.form_data = None
        self.submission.save()
        
        result = self.admin.form_data_preview(self.submission)
        
        # Should return "No data"
        self.assertIn('No data', result)
        self.assertIn('color: #666;', result)

    def test_form_data_preview_method_many_fields(self):
        """Test form_data_preview method with many fields."""
        # Create submission with many fields
        many_fields = {f'field_{i}': f'value_{i}' for i in range(10)}
        self.submission.form_data = many_fields
        self.submission.save()
        
        result = self.admin.form_data_preview(self.submission)
        
        # Should show first 3 fields and "+7 more"
        self.assertIn('10 fields:', result)
        self.assertIn('field_0', result)
        self.assertIn('field_1', result)
        self.assertIn('field_2', result)
        self.assertIn('+7 more', result)

    def test_get_queryset_optimization(self):
        """Test that get_queryset optimizes with select_related."""
        queryset = self.admin.get_queryset(None)
        
        # Check that related objects are selected
        self.assertIn('patient', str(queryset.query))
        self.assertIn('created_by', str(queryset.query))
        self.assertIn('form_template', str(queryset.query))