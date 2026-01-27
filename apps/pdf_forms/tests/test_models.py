from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.patients.models import Patient
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.events.models import Event
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, PDFFormSubmissionFactory, UserFactory, PatientFactory
from apps.pdf_forms.security import PDFFormSecurity
from unittest.mock import patch, mock_open
import tempfile
import os

User = get_user_model()


class PDFFormTemplateTests(TestCase):
    
    def setUp(self):
        self.user = UserFactory()

    def test_create_pdf_form_template(self):
        """Test creating a PDF form template."""
        template = PDFFormTemplateFactory(created_by=self.user)
        self.assertTrue(template.is_active)
        self.assertEqual(template.created_by, self.user)
        self.assertTrue(template.hospital_specific)
        self.assertIsInstance(template.form_fields, dict)

    def test_pdf_form_template_str_representation(self):
        """Test string representation of PDF form template."""
        template = PDFFormTemplateFactory(name="Test Form", created_by=self.user)
        self.assertEqual(str(template), "Test Form")

    def test_pdf_form_template_ordering(self):
        """Test templates are ordered by name."""
        template_b = PDFFormTemplateFactory(name="B Form", created_by=self.user)
        template_a = PDFFormTemplateFactory(name="A Form", created_by=self.user)
        
        templates = PDFFormTemplate.objects.all()
        self.assertEqual(templates[0], template_a)
        self.assertEqual(templates[1], template_b)

    def test_pdf_form_template_form_fields_default(self):
        """Test that form_fields defaults to empty dict."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            created_by=self.user,
            form_fields={}
        )
        self.assertEqual(template.form_fields, {})

    def test_pdf_form_template_json_field_validation(self):
        """Test that form_fields accepts valid JSON."""
        valid_config = {
            'patient_name': {
                'type': 'text',
                'required': True,
                'label': 'Patient Name',
                'x': 5.0,
                'y': 10.0,
                'width': 8.0,
                'height': 0.7
            }
        }
        
        template = PDFFormTemplateFactory(
            form_fields=valid_config,
            created_by=self.user
        )
        self.assertEqual(template.form_fields, valid_config)


class PDFFormSubmissionTests(TestCase):
    
    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_create_pdf_form_submission(self):
        """Test creating a PDF form submission."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        self.assertEqual(submission.form_template, self.template)
        self.assertEqual(submission.patient, self.patient)
        self.assertEqual(submission.created_by, self.user)
        self.assertEqual(submission.event_type, Event.PDF_FORM_EVENT)

    def test_pdf_form_submission_str_representation(self):
        """Test string representation of PDF form submission."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        expected_str = f"{self.template.name} - {self.patient.name}"
        self.assertEqual(str(submission), expected_str)

    def test_pdf_form_submission_get_absolute_url(self):
        """Test get_absolute_url method."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        expected_url = f"/pdf-forms/submission/{submission.pk}/"
        self.assertEqual(submission.get_absolute_url(), expected_url)

    def test_pdf_form_submission_form_data_storage(self):
        """Test that form data is properly stored as JSON."""
        form_data = {
            'patient_name': 'John Doe',
            'date_of_birth': '1990-01-01',
            'clinical_notes': 'Test notes'
        }
        
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=form_data
        )
        
        self.assertEqual(submission.form_data, form_data)

    def test_pdf_form_submission_inherits_event_fields(self):
        """Test that PDFFormSubmission inherits Event model fields."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test Event model inherited fields
        self.assertIsNotNone(submission.id)  # UUID field
        self.assertIsNotNone(submission.event_datetime)
        self.assertIsNotNone(submission.description)
        self.assertIsNotNone(submission.created_at)
        self.assertIsNotNone(submission.updated_at)

    def test_pdf_form_submission_form_data_validation(self):
        """Test form data validation and sanitization."""
        form_data = {
            'patient_name': 'John Doe',
            'date_of_birth': '1990-01-01',
            'clinical_notes': 'Test notes with special chars: <script>alert("test")</script>'
        }
        
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=form_data
        )
        
        # Form data should be sanitized due to model clean method
        self.assertIn('clinical_notes', submission.form_data)
        # Scripts should be removed by sanitization
        self.assertNotIn('<script>', submission.form_data['clinical_notes'])


class PDFFormModelIntegrationTests(TestCase):
    """Test integration between PDF form models and other app models."""
    
    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_template_patient_relationship(self):
        """Test that templates can be used with multiple patients."""
        template = PDFFormTemplateFactory(created_by=self.user)
        patient2 = PatientFactory(created_by=self.user)
        
        submission1 = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        submission2 = PDFFormSubmissionFactory(
            form_template=template,
            patient=patient2,
            created_by=self.user
        )
        
        # Same template used for different patients
        self.assertEqual(submission1.form_template, template)
        self.assertEqual(submission2.form_template, template)
        self.assertNotEqual(submission1.patient, submission2.patient)

    def test_patient_multiple_submissions(self):
        """Test that a patient can have multiple PDF form submissions."""
        template1 = PDFFormTemplateFactory(name="Form 1", created_by=self.user)
        template2 = PDFFormTemplateFactory(name="Form 2", created_by=self.user)
        
        submission1 = PDFFormSubmissionFactory(
            form_template=template1,
            patient=self.patient,
            created_by=self.user
        )
        
        submission2 = PDFFormSubmissionFactory(
            form_template=template2,
            patient=self.patient,
            created_by=self.user
        )
        
        # Same patient, different forms
        self.assertEqual(submission1.patient, self.patient)
        self.assertEqual(submission2.patient, self.patient)
        self.assertNotEqual(submission1.form_template, submission2.form_template)

    def test_user_permissions_integration(self):
        """Test integration with user permissions."""
        template = PDFFormTemplateFactory(created_by=self.user)
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test that created_by is properly set
        self.assertEqual(template.created_by, self.user)
        self.assertEqual(submission.created_by, self.user)
        
        # Test that patient creator and submission creator can be different
        other_user = UserFactory()
        submission2 = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=other_user
        )
        
        self.assertNotEqual(submission2.created_by, self.patient.created_by)

    def test_template_deactivation_effect(self):
        """Test that deactivating a template doesn't affect existing submissions."""
        template = PDFFormTemplateFactory(created_by=self.user, is_active=True)
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Deactivate template
        template.is_active = False
        template.save()
        
        # Submission should still exist and reference the template
        submission.refresh_from_db()
        self.assertEqual(submission.form_template, template)
        self.assertFalse(submission.form_template.is_active)

    def test_pdf_form_template_properties(self):
        """Test template property methods."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            form_fields={'field1': {'type': 'text', 'label': 'Field 1'}},
            created_by=self.user
        )
        
        # Test is_configured property
        self.assertTrue(template.is_configured)
        
        # Test with empty form_fields
        template.form_fields = {}
        self.assertFalse(template.is_configured)
        
        # Test with no form_fields
        template.form_fields = None
        self.assertFalse(template.is_configured)

    def test_pdf_form_template_configuration_status(self):
        """Test configuration_status property."""
        # Test with no PDF file
        template1 = PDFFormTemplateFactory(created_by=self.user)
        template1.pdf_file = None
        self.assertEqual(template1.configuration_status, "Sem PDF")
        
        # Test with PDF but no configuration
        template2 = PDFFormTemplateFactory(
            form_fields={},
            created_by=self.user
        )
        self.assertEqual(template2.configuration_status, "Não configurado")
        
        # Test with PDF and configuration
        template3 = PDFFormTemplateFactory(
            form_fields={'field1': {'type': 'text', 'label': 'Field 1'}},
            created_by=self.user
        )
        self.assertEqual(template3.configuration_status, "Configurado (1 campo)")
        
        # Test with multiple fields
        template4 = PDFFormTemplateFactory(
            form_fields={'field1': {'type': 'text', 'label': 'Field 1'}, 'field2': {'type': 'text', 'label': 'Field 2'}},
            created_by=self.user
        )
        self.assertEqual(template4.configuration_status, "Configurado (2 campos)")

    def test_pdf_form_template_clean_validation(self):
        """Test model clean method validation."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            created_by=self.user
        )
        
        # Test with valid form fields
        template.form_fields = {'field1': {'type': 'text', 'label': 'Field 1'}}
        template.full_clean()  # Should not raise
        
        # Test with invalid form fields
        template.form_fields = {'field1': {'type': 'invalid_type', 'label': 'Field 1'}}
        with self.assertRaises(ValidationError):
            template.full_clean()

    def test_pdf_form_template_save_with_validation(self):
        """Test save method with validation."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            created_by=self.user
        )
        
        # Test normal save
        template.save()
        
        # Test save with skip validation flag
        template._skip_validation = True
        template.form_fields = {'field1': {'type': 'invalid_type', 'label': 'Field 1'}}
        template.save()  # Should not raise due to skip validation

    def test_pdf_form_submission_get_edit_url(self):
        """Test get_edit_url method."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        edit_url = submission.get_edit_url()
        expected_url = f"/pdf-forms/submission/{submission.pk}/"
        self.assertEqual(edit_url, expected_url)

    def test_pdf_form_submission_form_data_sanitization(self):
        """Test form data sanitization in clean method."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test with malicious HTML/script content
        malicious_data = {
            'patient_name': '<script>alert("xss")</script>Test',
            'notes': 'Test <b>bold</b> <i>italic</i>',
            'safe_field': 'Normal text'
        }
        
        submission.form_data = malicious_data
        submission.clean()  # Should sanitize the data
        
        # Check that scripts are removed
        self.assertNotIn('<script>', submission.form_data['patient_name'])
        self.assertEqual(submission.form_data['patient_name'], 'Test')
        
        # Check that HTML tags are removed
        self.assertNotIn('<b>', submission.form_data['notes'])
        self.assertNotIn('<i>', submission.form_data['notes'])
        
        # Check that safe data is preserved
        self.assertEqual(submission.form_data['safe_field'], 'Normal text')

    def test_pdf_form_submission_auto_event_type(self):
        """Test that event type is automatically set."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            event_type=None  # Explicitly set to None
        )
        
        # Should automatically set to PDF_FORM_EVENT
        self.assertEqual(submission.event_type, Event.PDF_FORM_EVENT)

    def test_pdf_form_submission_indexes(self):
        """Test that model indexes are properly defined."""
        # Check that indexes exist in Meta
        indexes = PDFFormSubmission._meta.indexes
        self.assertEqual(len(indexes), 1)
        self.assertEqual(indexes[0].fields[0], 'form_template')

    def test_pdf_form_template_indexes(self):
        """Test that template model indexes are properly defined."""
        indexes = PDFFormTemplate._meta.indexes
        self.assertEqual(len(indexes), 2)
        index_names = [idx.name for idx in indexes]
        self.assertIn('pdf_form_template_active_idx', index_names)
        self.assertIn('pdf_form_template_hospital_idx', index_names)

    def test_pdf_form_submission_form_data_edge_cases(self):
        """Test form data handling edge cases."""
        # Test with None form_data
        submission1 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=None
        )
        self.assertIsNone(submission1.form_data)
        
        # Test with empty dict form_data
        submission2 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data={}
        )
        self.assertEqual(submission2.form_data, {})
        
        # Test with nested form_data
        nested_data = {
            'patient': {'name': 'John', 'age': 30},
            'medical': {'conditions': ['diabetes'], 'medications': []}
        }
        submission3 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=nested_data
        )
        self.assertEqual(submission3.form_data, nested_data)
        
        # Test with list form_data
        list_data = {'symptoms': ['fever', 'cough', 'headache']}
        submission4 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=list_data
        )
        self.assertEqual(submission4.form_data, list_data)

    def test_pdf_form_submission_form_data_sanitization_edge_cases(self):
        """Test form data sanitization edge cases."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test with None values
        data_with_none = {'field1': None, 'field2': 'value'}
        submission.form_data = data_with_none
        submission.clean()
        self.assertIsNone(submission.form_data['field1'])
        
        # Test with numeric values
        numeric_data = {'age': 25, 'weight': 70.5, 'height': 180}
        submission.form_data = numeric_data
        submission.clean()
        self.assertEqual(submission.form_data['age'], 25)
        self.assertEqual(submission.form_data['weight'], 70.5)
        self.assertEqual(submission.form_data['height'], 180)
        
        # Test with boolean values
        boolean_data = {'is_active': True, 'has_allergies': False}
        submission.form_data = boolean_data
        submission.clean()
        self.assertEqual(submission.form_data['is_active'], True)
        self.assertEqual(submission.form_data['has_allergies'], False)

    def test_pdf_form_template_configuration_status_edge_cases(self):
        """Test configuration_status property edge cases."""
        # Test with very large number of fields
        many_fields = {f'field_{i}': {'type': 'text', 'label': f'Field {i}'} for i in range(100)}
        template = PDFFormTemplateFactory(
            form_fields=many_fields,
            created_by=self.user
        )
        self.assertEqual(template.configuration_status, "Configurado (100 campos)")
        
        # Test with single character field names
        single_char_fields = {'a': {'type': 'text', 'label': 'A'}, 'b': {'type': 'text', 'label': 'B'}}
        template2 = PDFFormTemplateFactory(
            form_fields=single_char_fields,
            created_by=self.user
        )
        self.assertEqual(template2.configuration_status, "Configurado (2 campos)")
        
        # Test with special characters in field names
        special_char_fields = {'field_name': {'type': 'text', 'label': 'Field Name'}}
        template3 = PDFFormTemplateFactory(
            form_fields=special_char_fields,
            created_by=self.user
        )
        self.assertEqual(template3.configuration_status, "Configurado (1 campo)")

    def test_pdf_form_template_clean_method_edge_cases(self):
        """Test model clean method edge cases."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            created_by=self.user
        )
        
        # Test with empty dict form_fields
        template.form_fields = {}
        template.full_clean()  # Should not raise
        
        # Test with None form_fields
        template.form_fields = None
        template.full_clean()  # Should not raise
        
        # Test with valid field types
        valid_types = ['text', 'textarea', 'choice', 'boolean', 'date', 'datetime', 'time', 'number', 'email']
        for field_type in valid_types:
            template.form_fields = {'test_field': {'type': field_type, 'label': 'Test'}}
            template.full_clean()  # Should not raise
        
        # Test with invalid field types
        invalid_types = ['invalid', 'wrong', '', 123, None]
        for field_type in invalid_types:
            template.form_fields = {'test_field': {'type': field_type, 'label': 'Test'}}
            with self.assertRaises(ValidationError):
                template.full_clean()

    def test_pdf_form_template_is_configured_edge_cases(self):
        """Test is_configured property edge cases."""
        # Test with empty dict
        template1 = PDFFormTemplateFactory(
            form_fields={},
            created_by=self.user
        )
        self.assertFalse(template1.is_configured)
        
        # Test with None value
        template2 = PDFFormTemplateFactory(created_by=self.user)
        template2.form_fields = None
        self.assertFalse(template2.is_configured)
        
        # Test with valid configuration but empty dict
        template3 = PDFFormTemplateFactory(
            form_fields={},
            created_by=self.user
        )
        self.assertFalse(template3.is_configured)
        
        # Test with minimal valid configuration
        template4 = PDFFormTemplateFactory(
            form_fields={'test': {'type': 'text', 'label': 'Test'}},
            created_by=self.user
        )
        self.assertTrue(template4.is_configured)

    def test_pdf_form_submission_auto_event_type_edge_cases(self):
        """Test auto event type setting edge cases."""
        # Test with explicit event_type
        submission1 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            event_type=Event.DAILY_NOTE_EVENT  # Different event type
        )
        # Should respect the explicitly set event_type
        self.assertEqual(submission1.event_type, Event.DAILY_NOTE_EVENT)
        
        # Test with None event_type (should auto-set)
        submission2 = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            event_type=None
        )
        self.assertEqual(submission2.event_type, Event.PDF_FORM_EVENT)
        
        # Test with save() method after creation
        submission3 = PDFFormSubmission(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            event_type=None
        )
        submission3.save()
        self.assertEqual(submission3.event_type, Event.PDF_FORM_EVENT)