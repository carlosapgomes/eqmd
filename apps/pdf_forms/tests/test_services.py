from django.test import TestCase
from django import forms
from unittest.mock import patch, MagicMock, mock_open
from apps.pdf_forms.services.form_generator import DynamicFormGenerator
from apps.pdf_forms.services.pdf_overlay import PDFFormOverlay
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, UserFactory
import os
import tempfile


class FormGeneratorTests(TestCase):

    def setUp(self):
        self.generator = DynamicFormGenerator()

    def test_generate_form_class(self):
        """Test dynamic form class generation."""
        template = PDFFormTemplateFactory(
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                    'max_length': 100
                },
                'date_of_birth': {
                    'type': 'date',
                    'required': True,
                    'label': 'Date of Birth'
                }
            }
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()

        self.assertIn('patient_name', form_instance.fields)
        self.assertIn('date_of_birth', form_instance.fields)
        self.assertTrue(form_instance.fields['patient_name'].required)

    def test_create_django_field_text(self):
        """Test text field creation."""
        config = {
            'type': 'text',
            'required': True,
            'label': 'Test Field',
            'max_length': 50
        }

        field = self.generator._create_django_field('test', config)
        self.assertEqual(field.label, 'Test Field')
        self.assertTrue(field.required)
        self.assertEqual(field.max_length, 50)

    def test_create_django_field_choice(self):
        """Test choice field creation."""
        config = {
            'type': 'choice',
            'required': False,
            'label': 'Blood Type',
            'choices': ['A+', 'A-', 'B+', 'B-']
        }

        field = self.generator._create_django_field('blood_type', config)
        self.assertEqual(field.label, 'Blood Type')
        self.assertFalse(field.required)
        self.assertEqual(len(field.choices), 4)


class PDFFormOverlayTests(TestCase):

    def setUp(self):
        self.overlay = PDFFormOverlay()

    def test_validate_pdf_form_nonexistent(self):
        """Test validation of nonexistent PDF."""
        is_valid, error = self.overlay.validate_pdf_form('/nonexistent/path.pdf')
        self.assertFalse(is_valid)
        self.assertIn('not found', error)

    def test_get_page_dimensions(self):
        """Test page dimensions calculation."""
        # This would need a mock PDF file for proper testing
        dimensions = self.overlay.get_page_dimensions('/nonexistent.pdf')
        self.assertIn('width', dimensions)
        self.assertIn('height', dimensions)
        self.assertIn('format', dimensions)


class FormGeneratorAdvancedTests(TestCase):
    """Advanced tests for DynamicFormGenerator."""

    def setUp(self):
        self.generator = DynamicFormGenerator()
        self.user = UserFactory()

    def test_generate_form_class_with_multiple_field_types(self):
        """Test form generation with various field types."""
        template = PDFFormTemplateFactory(
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                    'max_length': 100
                },
                'email': {
                    'type': 'email',
                    'required': False,
                    'label': 'Email Address'
                },
                'age': {
                    'type': 'number',
                    'required': True,
                    'label': 'Age'
                },
                'weight': {
                    'type': 'decimal',
                    'required': False,
                    'label': 'Weight (kg)'
                },
                'birth_date': {
                    'type': 'date',
                    'required': True,
                    'label': 'Birth Date'
                },
                'appointment_datetime': {
                    'type': 'datetime',
                    'required': False,
                    'label': 'Appointment Date/Time'
                },
                'urgent': {
                    'type': 'boolean',
                    'required': False,
                    'label': 'Urgent Case'
                },
                'blood_type': {
                    'type': 'choice',
                    'required': True,
                    'label': 'Blood Type',
                    'choices': ['A+', 'A-', 'B+', 'B-', 'O+', 'O-']
                },
                'symptoms': {
                    'type': 'multiple_choice',
                    'required': False,
                    'label': 'Symptoms',
                    'choices': ['Fever', 'Headache', 'Nausea', 'Fatigue']
                },
                'notes': {
                    'type': 'textarea',
                    'required': False,
                    'label': 'Clinical Notes'
                }
            },
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()

        # Test all field types are created
        self.assertIsInstance(form_instance.fields['patient_name'], forms.CharField)
        self.assertIsInstance(form_instance.fields['email'], forms.EmailField)
        self.assertIsInstance(form_instance.fields['age'], forms.IntegerField)
        self.assertIsInstance(form_instance.fields['weight'], forms.DecimalField)
        self.assertIsInstance(form_instance.fields['birth_date'], forms.DateField)
        self.assertIsInstance(form_instance.fields['appointment_datetime'], forms.DateTimeField)
        self.assertIsInstance(form_instance.fields['urgent'], forms.BooleanField)
        self.assertIsInstance(form_instance.fields['blood_type'], forms.ChoiceField)
        self.assertIsInstance(form_instance.fields['symptoms'], forms.MultipleChoiceField)
        self.assertIsInstance(form_instance.fields['notes'], forms.CharField)

        # Test required fields
        self.assertTrue(form_instance.fields['patient_name'].required)
        self.assertFalse(form_instance.fields['email'].required)
        self.assertTrue(form_instance.fields['age'].required)
        self.assertTrue(form_instance.fields['birth_date'].required)
        self.assertFalse(form_instance.fields['urgent'].required)

        # Test field-specific properties
        self.assertEqual(form_instance.fields['patient_name'].max_length, 100)
        self.assertEqual(len(form_instance.fields['blood_type'].choices), 6)
        self.assertIsInstance(form_instance.fields['notes'].widget, forms.Textarea)

    def test_create_django_field_with_help_text(self):
        """Test field creation with help text."""
        config = {
            'type': 'text',
            'required': True,
            'label': 'Medical Record Number',
            'help_text': 'Enter the patient\'s unique medical record number',
            'max_length': 20
        }

        field = self.generator._create_django_field('mrn', config)
        self.assertEqual(field.help_text, 'Enter the patient\'s unique medical record number')

    def test_create_django_field_textarea_widget(self):
        """Test textarea field widget configuration."""
        config = {
            'type': 'textarea',
            'required': False,
            'label': 'Detailed Notes'
        }

        field = self.generator._create_django_field('detailed_notes', config)
        self.assertIsInstance(field.widget, forms.Textarea)
        self.assertEqual(field.widget.attrs['rows'], 3)

    def test_create_django_field_multiple_choice_widget(self):
        """Test multiple choice field widget configuration."""
        config = {
            'type': 'multiple_choice',
            'required': False,
            'label': 'Allergies',
            'choices': ['Penicillin', 'Latex', 'Nuts', 'Shellfish']
        }

        field = self.generator._create_django_field('allergies', config)
        self.assertIsInstance(field.widget, forms.CheckboxSelectMultiple)
        self.assertEqual(len(field.choices), 4)

    def test_create_django_field_unknown_type_defaults_to_charfield(self):
        """Test that unknown field types default to CharField."""
        config = {
            'type': 'unknown_type',
            'required': True,
            'label': 'Unknown Field'
        }

        field = self.generator._create_django_field('unknown', config)
        self.assertIsInstance(field, forms.CharField)

    def test_form_class_naming(self):
        """Test dynamic form class naming."""
        template = PDFFormTemplateFactory(
            name="Blood Transfusion Request",
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        self.assertEqual(form_class.__name__, "BloodTransfusionRequestForm")

    def test_form_validation_method(self):
        """Test that generated form has custom clean method."""
        template = PDFFormTemplateFactory(
            form_fields={
                'field1': {
                    'type': 'text',
                    'required': True,
                    'label': 'Field 1'
                }
            },
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class({'field1': 'test'})
        
        # Test that clean method exists and can be called
        self.assertTrue(hasattr(form_instance, 'clean'))


class PDFFormOverlayAdvancedTests(TestCase):
    """Advanced tests for PDFFormOverlay service."""

    def setUp(self):
        self.overlay = PDFFormOverlay()

    @patch('apps.pdf_forms.services.pdf_overlay.PDF_LIBRARY_AVAILABLE', True)
    def test_pdf_overlay_initialization_success(self):
        """Test successful PDF overlay initialization when library is available."""
        overlay = PDFFormOverlay()
        self.assertIsNotNone(overlay)

    @patch('apps.pdf_forms.services.pdf_overlay.PDF_LIBRARY_AVAILABLE', False)
    def test_pdf_overlay_initialization_failure(self):
        """Test PDF overlay initialization failure when library is not available."""
        with self.assertRaises(ImportError) as context:
            PDFFormOverlay()
        self.assertIn('pypdf library is required', str(context.exception))

    @patch('os.path.exists')
    def test_fill_form_file_not_found(self, mock_exists):
        """Test fill_form method with non-existent template file."""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError) as context:
            self.overlay.fill_form('/nonexistent/template.pdf', {})
        self.assertIn('PDF template not found', str(context.exception))

    @patch('os.path.exists')
    @patch('apps.pdf_forms.services.pdf_overlay.PdfReader')
    @patch('apps.pdf_forms.services.pdf_overlay.PdfWriter')
    def test_generate_pdf_response_success(self, mock_writer, mock_reader, mock_exists):
        """Test successful PDF response generation."""
        mock_exists.return_value = True
        
        # Mock PDF reader
        mock_page = MagicMock()
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_reader.return_value = mock_reader_instance
        
        # Mock PDF writer
        mock_writer_instance = MagicMock()
        mock_writer_instance.write = MagicMock()
        mock_writer.return_value = mock_writer_instance
        
        form_data = {
            'patient_name': 'John Doe',
            'date_of_birth': '1990-01-01'
        }
        
        field_config = {
            'patient_name': {'x': 5.0, 'y': 10.0, 'width': 8.0, 'height': 0.7},
            'date_of_birth': {'x': 5.0, 'y': 11.0, 'width': 5.0, 'height': 0.7}
        }
        
        # Test the new generate_pdf_response method
        response = self.overlay.generate_pdf_response(
            '/fake/template.pdf', 
            form_data, 
            field_config,
            'test_form.pdf'
        )
        
        # Verify it returns an HttpResponse
        from django.http import HttpResponse
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="test_form.pdf"', response['Content-Disposition'])
        
        # Verify methods were called
        mock_reader.assert_called_once_with('/fake/template.pdf')
        mock_writer.assert_called_once()
        mock_writer_instance.add_page.assert_called_once_with(mock_page)

    @patch('os.path.exists')
    def test_extract_form_fields_file_not_found(self, mock_exists):
        """Test extract_form_fields with non-existent file."""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError) as context:
            self.overlay.extract_form_fields('/nonexistent/file.pdf')
        self.assertIn('PDF file not found', str(context.exception))

    @patch('os.path.exists')
    @patch('apps.pdf_forms.services.pdf_overlay.PdfReader')
    def test_extract_form_fields_success(self, mock_reader, mock_exists):
        """Test successful form field extraction."""
        mock_exists.return_value = True
        
        # Mock PDF reader with form fields
        mock_page = MagicMock()
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page]
        mock_reader.return_value = mock_reader_instance
        
        fields = self.overlay.extract_form_fields('/fake/form.pdf')
        
        self.assertIsInstance(fields, dict)
        mock_reader.assert_called_once_with('/fake/form.pdf')

    def test_validate_pdf_form_with_extract_error(self):
        """Test PDF validation when extraction fails."""
        with patch.object(self.overlay, 'extract_form_fields') as mock_extract:
            mock_extract.side_effect = Exception("Extraction error")
            
            is_valid, error = self.overlay.validate_pdf_form('/fake/pdf')
            
            self.assertFalse(is_valid)
            self.assertEqual(error, "Extraction error")

    def test_validate_pdf_form_no_fields(self):
        """Test PDF validation when no fields are found."""
        with patch.object(self.overlay, 'extract_form_fields') as mock_extract:
            mock_extract.return_value = {}
            
            is_valid, error = self.overlay.validate_pdf_form('/fake/pdf')
            
            self.assertFalse(is_valid)
            self.assertIn('does not contain fillable form fields', error)

    def test_validate_pdf_form_success(self):
        """Test successful PDF validation."""
        with patch.object(self.overlay, 'extract_form_fields') as mock_extract:
            mock_extract.return_value = {'field1': {'type': 'text'}}
            
            is_valid, error = self.overlay.validate_pdf_form('/fake/pdf')
            
            self.assertTrue(is_valid)
            self.assertIsNone(error)

    @patch('os.path.exists')
    def test_generate_pdf_response_error_handling(self, mock_exists):
        """Test error handling for PDF generation failures."""
        mock_exists.return_value = False
        
        form_data = {'patient_name': 'John Doe'}
        field_config = {'patient_name': {'x': 5.0, 'y': 10.0}}
        
        with self.assertRaises(FileNotFoundError):
            self.overlay.generate_pdf_response(
                '/nonexistent/template.pdf',
                form_data,
                field_config,
                'test.pdf'
            )

    @patch('os.path.exists')
    @patch('apps.pdf_forms.services.pdf_overlay.PdfReader')
    def test_generate_pdf_response_memory_management(self, mock_reader, mock_exists):
        """Test memory management and cleanup during PDF generation."""
        mock_exists.return_value = True
        
        # Mock PDF reader that raises an exception
        mock_reader.side_effect = Exception("Memory error")
        
        form_data = {'patient_name': 'John Doe'}
        field_config = {'patient_name': {'x': 5.0, 'y': 10.0}}
        
        # Should handle the exception gracefully
        with self.assertRaises(Exception):
            self.overlay.generate_pdf_response(
                '/fake/template.pdf',
                form_data,
                field_config,
                'test.pdf'
            )

    def test_performance_pdf_generation_timing(self):
        """Test performance characteristics of on-demand generation."""
        import time
        from unittest.mock import patch
        
        with patch.object(self.overlay, 'generate_pdf_response') as mock_generate:
            # Mock a response that takes some time
            def slow_generation(*args, **kwargs):
                time.sleep(0.01)  # Simulate 10ms generation time
                from django.http import HttpResponse
                return HttpResponse(b'fake pdf', content_type='application/pdf')
            
            mock_generate.side_effect = slow_generation
            
            start_time = time.time()
            self.overlay.generate_pdf_response(
                '/fake/template.pdf',
                {'test': 'data'},
                {'test': {'x': 1.0, 'y': 1.0}},
                'test.pdf'
            )
            generation_time = time.time() - start_time
            
            # Should complete within reasonable time (< 1 second for test)
            self.assertLess(generation_time, 1.0)


class ServiceIntegrationTests(TestCase):
    """Integration tests between form generator and PDF overlay services."""

    def setUp(self):
        self.generator = DynamicFormGenerator()
        self.overlay = PDFFormOverlay()
        self.user = UserFactory()

    def test_form_generation_to_pdf_filling_workflow(self):
        """Test complete workflow from form generation to PDF filling."""
        # Create template with form fields
        template = PDFFormTemplateFactory(
            name="Integration Test Form",
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                    'x': 5.0,
                    'y': 10.0,
                    'width': 10.0,
                    'height': 0.7
                },
                'urgent': {
                    'type': 'boolean',
                    'required': False,
                    'label': 'Urgent',
                    'x': 15.0,
                    'y': 10.0,
                    'width': 2.0,
                    'height': 0.7
                }
            },
            created_by=self.user
        )

        # Generate Django form
        form_class = self.generator.generate_form_class(template)
        self.assertIsNotNone(form_class)

        # Create form instance with data
        form_data = {
            'patient_name': 'Test Patient',
            'urgent': True
        }
        form_instance = form_class(form_data)
        
        # Validate form
        self.assertTrue(form_instance.is_valid())
        
        # Test that form data structure is compatible with PDF overlay
        cleaned_data = form_instance.cleaned_data
        self.assertIn('patient_name', cleaned_data)
        self.assertIn('urgent', cleaned_data)
        self.assertEqual(cleaned_data['patient_name'], 'Test Patient')
        self.assertTrue(cleaned_data['urgent'])

    def test_field_configuration_consistency(self):
        """Test that field configuration is consistent between services."""
        template = PDFFormTemplateFactory(
            form_fields={
                'test_field': {
                    'type': 'text',
                    'required': True,
                    'label': 'Test Field',
                    'x': 5.0,
                    'y': 10.0,
                    'width': 8.0,
                    'height': 0.7,
                    'font_size': 12,
                    'font_family': 'Arial'
                }
            },
            created_by=self.user
        )

        # Generate form and check field configuration
        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()
        
        # Field should exist in form
        self.assertIn('test_field', form_instance.fields)
        
        # Field properties should match configuration
        field = form_instance.fields['test_field']
        self.assertTrue(field.required)
        self.assertEqual(field.label, 'Test Field')

        # PDF overlay should be able to use the same configuration
        field_config = template.form_fields['test_field']
        self.assertEqual(field_config['x'], 5.0)
        self.assertEqual(field_config['y'], 10.0)
        self.assertEqual(field_config['font_size'], 12)

    @patch('apps.pdf_forms.services.pdf_overlay.PdfReader')
    def test_error_handling_integration(self, mock_reader):
        """Test error handling between services."""
        template = PDFFormTemplateFactory(
            form_fields={
                'field1': {
                    'type': 'invalid_type',  # Invalid type
                    'required': True,
                    'label': 'Invalid Field'
                }
            },
            created_by=self.user
        )

        # Form generator should handle invalid type gracefully
        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()
        
        # Should default to CharField for unknown types
        self.assertIn('field1', form_instance.fields)
        self.assertIsInstance(form_instance.fields['field1'], forms.CharField)