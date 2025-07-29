from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.pdf_forms.security import PDFFormSecurity
from unittest.mock import patch, mock_open, MagicMock
import tempfile
import os


class PDFFormSecurityTests(TestCase):
    """Test PDFFormSecurity utility functions."""

    def setUp(self):
        self.security = PDFFormSecurity()

    def test_validate_pdf_file_valid(self):
        """Test validation of valid PDF file."""
        # Create a mock PDF file
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        pdf_file = SimpleUploadedFile(
            name="test.pdf",
            content=pdf_content,
            content_type="application/pdf"
        )
        
        # Should not raise any exception
        result = PDFFormSecurity.validate_pdf_file(pdf_file)
        self.assertTrue(result)

    def test_validate_pdf_file_invalid_extension(self):
        """Test validation of file with invalid extension."""
        txt_file = SimpleUploadedFile(
            name="test.txt",
            content=b"Not a PDF",
            content_type="text/plain"
        )
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_pdf_file(txt_file)
        
        self.assertIn("Only PDF files are allowed", str(context.exception))

    def test_validate_pdf_file_invalid_mime_type(self):
        """Test validation of file with invalid MIME type."""
        # Create a file with .pdf extension but wrong content type
        pdf_file = SimpleUploadedFile(
            name="test.pdf",
            content=b"Not actually PDF content",
            content_type="text/plain"
        )
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_pdf_file(pdf_file)
        
        self.assertIn("Invalid file type", str(context.exception))

    def test_validate_pdf_file_too_large(self):
        """Test validation of file that is too large."""
        # Create a large file (larger than 10MB)
        large_content = b'0' * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            name="large.pdf",
            content=large_content,
            content_type="application/pdf"
        )
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_pdf_file(large_file)
        
        self.assertIn("File too large", str(context.exception))

    def test_validate_pdf_file_no_content_type(self):
        """Test validation of file without content_type attribute."""
        # Create a mock file without content_type
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        mock_file.size = 1024
        # Don't set content_type to simulate some test scenarios
        del mock_file.content_type
        
        # Should not raise exception for missing content_type
        result = PDFFormSecurity.validate_pdf_file(mock_file)
        self.assertTrue(result)

    def test_generate_secure_filename(self):
        """Test generation of secure filenames."""
        original_filename = "test.pdf"
        secure_name = PDFFormSecurity.generate_secure_filename(original_filename)
        
        # Should contain UUID and preserve extension
        self.assertTrue(secure_name.endswith('.pdf'))
        self.assertNotEqual(secure_name, original_filename)
        self.assertIn('-', secure_name)  # UUID format

    def test_generate_secure_filename_with_prefix(self):
        """Test generation of secure filenames with prefix."""
        original_filename = "document.pdf"
        prefix = "pdf_form_"
        secure_name = PDFFormSecurity.generate_secure_filename(original_filename, prefix)
        
        # Should contain prefix and UUID
        self.assertTrue(secure_name.startswith(prefix))
        self.assertTrue(secure_name.endswith('.pdf'))
        self.assertIn('-', secure_name)  # UUID format

    def test_validate_file_path_valid(self):
        """Test validation of valid file path."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
            try:
                # Mock settings.MEDIA_ROOT to include the temp directory
                with patch.object(settings, 'MEDIA_ROOT', os.path.dirname(tmp_path)):
                    result = PDFFormSecurity.validate_file_path(tmp_path)
                    self.assertTrue(result)
            finally:
                os.unlink(tmp_path)

    def test_validate_file_path_invalid(self):
        """Test validation of invalid file path (path traversal)."""
        invalid_path = "/etc/passwd"
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_file_path(invalid_path)
        
        self.assertIn("Invalid file path", str(context.exception))

    def test_sanitize_form_data_dict(self):
        """Test sanitization of dictionary form data."""
        input_data = {
            'patient_name': '<script>alert("xss")</script>John Doe',
            'notes': 'Test <b>bold</b> and <i>italic</i> text',
            'age': 30,
            'is_active': True,
            'normal_text': 'Just normal text'
        }
        
        sanitized = PDFFormSecurity.sanitize_form_data(input_data)
        
        # Check that scripts are removed
        self.assertNotIn('<script>', sanitized['patient_name'])
        self.assertEqual(sanitized['patient_name'], 'John Doe')
        
        # Check that HTML tags are removed
        self.assertNotIn('<b>', sanitized['notes'])
        self.assertNotIn('<i>', sanitized['notes'])
        self.assertEqual(sanitized['notes'], 'Test bold and italic text')
        
        # Check that safe types are preserved
        self.assertEqual(sanitized['age'], 30)
        self.assertEqual(sanitized['is_active'], True)
        self.assertEqual(sanitized['normal_text'], 'Just normal text')

    def test_sanitize_form_data_list(self):
        """Test sanitization of list form data."""
        input_data = {
            'symptoms': ['<script>alert(1)</script>Fever', 'Headache', '<b>Nausea</b>'],
            'test_field': 'normal text'
        }
        
        sanitized = PDFFormSecurity.sanitize_form_data(input_data)
        
        # Check that list items are sanitized
        self.assertNotIn('<script>', sanitized['symptoms'][0])
        self.assertEqual(sanitized['symptoms'][0], 'Fever')
        self.assertEqual(sanitized['symptoms'][1], 'Headache')
        self.assertNotIn('<b>', sanitized['symptoms'][2])
        self.assertEqual(sanitized['symptoms'][2], 'Nausea')

    def test_sanitize_form_data_invalid_keys(self):
        """Test sanitization with invalid keys."""
        input_data = {
            'valid_key': 'value',
            'invalid-key-with-dashes': 'value2',
            'invalid key with spaces': 'value3',
            '123_invalid_start': 'value4',
            'valid_key_2': 'value5'
        }
        
        sanitized = PDFFormSecurity.sanitize_form_data(input_data)
        
        # Should only include valid keys
        self.assertIn('valid_key', sanitized)
        self.assertIn('valid_key_2', sanitized)
        self.assertNotIn('invalid-key-with-dashes', sanitized)
        self.assertNotIn('invalid key with spaces', sanitized)
        self.assertNotIn('123_invalid_start', sanitized)

    def test_sanitize_form_data_non_dict_input(self):
        """Test sanitization of non-dictionary input."""
        # Should return input as-is for non-dict input
        input_string = "not a dictionary"
        result = PDFFormSecurity.sanitize_form_data(input_string)
        self.assertEqual(result, input_string)

    def test_sanitize_form_data_none_values(self):
        """Test sanitization with None values."""
        input_data = {
            'field1': None,
            'field2': 'normal value',
            'field3': '',
            'field4': 0
        }
        
        sanitized = PDFFormSecurity.sanitize_form_data(input_data)
        
        self.assertIsNone(sanitized['field1'])
        self.assertEqual(sanitized['field2'], 'normal value')
        self.assertEqual(sanitized['field3'], '')
        self.assertEqual(sanitized['field4'], 0)

    def test_validate_field_configuration_valid(self):
        """Test validation of valid field configuration."""
        valid_config = {
            'patient_name': {
                'type': 'text',
                'label': 'Patient Name',
                'x': 5.0,
                'y': 10.0,
                'width': 8.0,
                'height': 0.7
            },
            'blood_type': {
                'type': 'choice',
                'label': 'Blood Type',
                'choices': ['A+', 'A-', 'B+', 'B-']
            }
        }
        
        result = PDFFormSecurity.validate_field_configuration(valid_config)
        self.assertTrue(result)

    def test_validate_field_configuration_empty(self):
        """Test validation of empty field configuration."""
        # Empty dict should be valid
        result = PDFFormSecurity.validate_field_configuration({})
        self.assertTrue(result)
        
        # None should be valid
        result = PDFFormSecurity.validate_field_configuration(None)
        self.assertTrue(result)

    def test_validate_field_configuration_invalid_structure(self):
        """Test validation with invalid structure."""
        # Non-dict input
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration("not a dict")
        
        self.assertIn("must be a dictionary", str(context.exception))

    def test_validate_field_configuration_invalid_field_name(self):
        """Test validation with invalid field names."""
        invalid_config = {
            'invalid-field-name': {
                'type': 'text',
                'label': 'Invalid Field'
            },
            'another invalid name': {
                'type': 'text',
                'label': 'Another Invalid Field'
            }
        }
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration(invalid_config)
        
        self.assertIn("Invalid field name", str(context.exception))

    def test_validate_field_configuration_missing_required_properties(self):
        """Test validation with missing required properties."""
        invalid_config = {
            'field1': {
                'type': 'text'
                # Missing 'label'
            }
        }
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration(invalid_config)
        
        self.assertIn("missing required property", str(context.exception))

    def test_validate_field_configuration_invalid_type(self):
        """Test validation with invalid field type."""
        invalid_config = {
            'field1': {
                'type': 'invalid_type',
                'label': 'Invalid Field'
            }
        }
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration(invalid_config)
        
        self.assertIn("Invalid field type", str(context.exception))

    def test_validate_field_configuration_invalid_coordinates(self):
        """Test validation with invalid coordinates."""
        invalid_config = {
            'field1': {
                'type': 'text',
                'label': 'Field 1',
                'x': 'invalid',
                'y': -5.0
            }
        }
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration(invalid_config)
        
        self.assertIn("Invalid coordinate", str(context.exception))

    def test_validate_field_configuration_invalid_choice_field(self):
        """Test validation of invalid choice field configuration."""
        invalid_config = {
            'field1': {
                'type': 'choice',
                'label': 'Choice Field',
                'choices': 'not_a_list'
            }
        }
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_field_configuration(invalid_config)
        
        self.assertIn("must have a 'choices' list", str(context.exception))

    def test_validate_pdf_content_valid(self):
        """Test validation of valid PDF content."""
        # Create a temporary PDF file
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name
            
            try:
                result = PDFFormSecurity.validate_pdf_content(tmp_path)
                self.assertTrue(result)
            finally:
                os.unlink(tmp_path)

    def test_validate_pdf_content_invalid(self):
        """Test validation of invalid PDF content."""
        # Create a temporary file with non-PDF content
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"This is not a PDF file")
            tmp_path = tmp_file.name
            
            try:
                with self.assertRaises(ValidationError) as context:
                    PDFFormSecurity.validate_pdf_content(tmp_path)
                
                self.assertIn("does not appear to be a valid PDF", str(context.exception))
            finally:
                os.unlink(tmp_path)

    def test_validate_pdf_content_file_not_found(self):
        """Test validation when PDF file doesn't exist."""
        non_existent_path = "/path/that/does/not/exist.pdf"
        
        with self.assertRaises(ValidationError) as context:
            PDFFormSecurity.validate_pdf_content(non_existent_path)
        
        self.assertIn("Cannot read PDF file", str(context.exception))

    def test_constants(self):
        """Test security constants."""
        self.assertEqual(PDFFormSecurity.ALLOWED_EXTENSIONS, ['.pdf'])
        self.assertEqual(PDFFormSecurity.MAX_FILE_SIZE, 10 * 1024 * 1024)  # 10MB