# Security utilities in apps/pdf_forms/security.py
import os
import uuid
from pathlib import Path
from django.core.exceptions import ValidationError
from django.conf import settings


class PDFFormSecurity:
    """Security utilities for PDF form handling."""

    ALLOWED_EXTENSIONS = ['.pdf']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_pdf_file(uploaded_file):
        """Validate uploaded PDF file."""
        # Check file extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in PDFFormSecurity.ALLOWED_EXTENSIONS:
            raise ValidationError(f"Only PDF files are allowed. Got: {file_extension}")

        # Check file size
        if uploaded_file.size > PDFFormSecurity.MAX_FILE_SIZE:
            raise ValidationError(f"File too large. Maximum size: {PDFFormSecurity.MAX_FILE_SIZE} bytes")

        # Check MIME type (skip for test files that may not have content_type)
        if hasattr(uploaded_file, 'content_type') and uploaded_file.content_type:
            if uploaded_file.content_type != 'application/pdf':
                raise ValidationError(f"Invalid file type. Expected PDF, got: {uploaded_file.content_type}")

        return True

    @staticmethod
    def generate_secure_filename(original_filename, prefix=''):
        """Generate secure filename with UUID."""
        file_extension = os.path.splitext(original_filename)[1].lower()
        secure_name = f"{prefix}{uuid.uuid4()}{file_extension}"
        return secure_name

    @staticmethod
    def validate_file_path(file_path):
        """Validate file path for security."""
        # Resolve path and check it's within allowed directories
        resolved_path = Path(file_path).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()

        if not str(resolved_path).startswith(str(media_root)):
            raise ValidationError("Invalid file path")

        return True

    @staticmethod
    def sanitize_form_data(form_data):
        """Sanitize form data to prevent XSS and injection attacks."""
        if not isinstance(form_data, dict):
            return form_data

        sanitized_data = {}
        for key, value in form_data.items():
            # Sanitize key
            if not isinstance(key, str) or not key.replace('_', '').isalnum():
                continue  # Skip invalid keys

            # Sanitize value based on type
            if isinstance(value, str):
                # Remove potential script tags and dangerous HTML
                import re
                value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
                value = re.sub(r'<[^>]+>', '', value)  # Remove all HTML tags
                value = value.strip()
            elif isinstance(value, (int, float, bool)):
                pass  # These types are safe
            elif isinstance(value, list):
                # Sanitize list items
                value = [PDFFormSecurity.sanitize_form_data(item) for item in value if item is not None]
            else:
                # Convert other types to string and sanitize
                value = str(value) if value is not None else ''

            sanitized_data[key] = value

        return sanitized_data

    @staticmethod
    def validate_field_configuration(field_config):
        """Validate PDF form field configuration for security."""
        if not isinstance(field_config, dict):
            raise ValidationError("Field configuration must be a dictionary")

        # Allow empty dict for templates without fields configured yet
        if not field_config:
            return True

        for field_name, config in field_config.items():
            # Validate field name
            if not isinstance(field_name, str) or not field_name.replace('_', '').isalnum():
                raise ValidationError(f"Invalid field name: {field_name}")

            # Validate configuration structure
            if not isinstance(config, dict):
                raise ValidationError(f"Field configuration for '{field_name}' must be a dictionary")

            # Required fields
            required_fields = ['type', 'label']
            for required_field in required_fields:
                if required_field not in config:
                    raise ValidationError(f"Field '{field_name}' missing required property: {required_field}")

            # Validate field type
            allowed_types = ['text', 'textarea', 'email', 'number', 'decimal', 'date', 'datetime', 'boolean', 'choice', 'multiple_choice']
            if config['type'] not in allowed_types:
                raise ValidationError(f"Invalid field type '{config['type']}' for field '{field_name}'")

            # Validate coordinates
            for coord in ['x', 'y', 'width', 'height']:
                if coord in config:
                    try:
                        float(config[coord])
                        if float(config[coord]) < 0:
                            raise ValidationError(f"Coordinate '{coord}' cannot be negative for field '{field_name}'")
                    except (ValueError, TypeError):
                        raise ValidationError(f"Invalid coordinate '{coord}' for field '{field_name}'")

            # Validate choices for choice fields
            if config['type'] in ['choice', 'multiple_choice']:
                if 'choices' not in config or not isinstance(config['choices'], list):
                    raise ValidationError(f"Choice field '{field_name}' must have a 'choices' list")

        return True

    @staticmethod
    def validate_pdf_content(file_path):
        """Basic validation that file is actually a PDF."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValidationError("File does not appear to be a valid PDF")
        except IOError:
            raise ValidationError("Cannot read PDF file")

        return True