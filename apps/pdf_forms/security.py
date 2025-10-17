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
                # Use proper HTML sanitization instead of regex
                from django.utils.html import escape
                # Escape HTML entities to prevent XSS
                value = escape(value).strip()
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

        # Handle new sectioned format
        if 'sections' in field_config and 'fields' in field_config:
            # Validate sections configuration
            PDFFormSecurity.validate_section_configuration(field_config.get('sections', {}))
            # Validate fields configuration
            fields_config = field_config.get('fields', {})
            # NEW: Validate data sources if present
            data_sources = field_config.get('data_sources', {})
            if data_sources:
                PDFFormSecurity.validate_data_sources(data_sources)
        else:
            # Backward compatibility: treat entire config as fields
            # But first extract data_sources if present in legacy format
            data_sources = field_config.get('data_sources', {})
            if data_sources:
                PDFFormSecurity.validate_data_sources(data_sources)
                # Remove data_sources from fields config to avoid treating it as a field
                fields_config = {k: v for k, v in field_config.items() if k != 'data_sources'}
            else:
                fields_config = field_config

        for field_name, config in fields_config.items():
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

            # Validate choices for choice fields (unless using data source)
            if config['type'] in ['choice', 'multiple_choice']:
                # Data source fields don't need explicit choices
                if 'data_source' not in config:
                    if 'choices' not in config or not isinstance(config['choices'], list):
                        raise ValidationError(f"Choice field '{field_name}' must have a 'choices' list")

            # Validate section reference if present
            if 'section' in config:
                section_key = config['section']
                if not isinstance(section_key, str) or not section_key.replace('_', '').isalnum():
                    raise ValidationError(f"Invalid section key '{section_key}' for field '{field_name}'")

            # Validate field order if present
            if 'field_order' in config:
                try:
                    field_order = int(config['field_order'])
                    if field_order < 1:
                        raise ValidationError(f"Field order must be positive for field '{field_name}'")
                except (ValueError, TypeError):
                    raise ValidationError(f"Invalid field order for field '{field_name}'")

            # NEW: Validate field data source references
            if isinstance(config, dict) and 'data_source' in config:
                PDFFormSecurity.validate_field_data_source_reference(
                    field_name, config, data_sources
                )

        return True

    @staticmethod
    def validate_section_configuration(sections_config):
        """Validate sections configuration structure."""
        if not isinstance(sections_config, dict):
            raise ValidationError("Sections configuration must be a dictionary")

        # Allow empty sections
        if not sections_config:
            return True

        section_orders = []
        for section_key, section_config in sections_config.items():
            # Validate section key
            if not isinstance(section_key, str) or not section_key.replace('_', '').isalnum():
                raise ValidationError(f"Invalid section key: {section_key}")

            # Validate section configuration structure
            if not isinstance(section_config, dict):
                raise ValidationError(f"Section configuration for '{section_key}' must be a dictionary")

            # Required fields
            required_fields = ['label', 'order']
            for required_field in required_fields:
                if required_field not in section_config:
                    raise ValidationError(f"Section '{section_key}' missing required property: {required_field}")

            # Validate label
            label = section_config['label']
            if not isinstance(label, str) or not label.strip():
                raise ValidationError(f"Section '{section_key}' must have a non-empty label")

            # Validate order
            try:
                order = int(section_config['order'])
                if order < 1:
                    raise ValidationError(f"Section order must be positive for section '{section_key}'")
                section_orders.append(order)
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid order for section '{section_key}'")

            # Validate optional fields
            if 'description' in section_config:
                if not isinstance(section_config['description'], str):
                    raise ValidationError(f"Section description must be a string for section '{section_key}'")

            if 'collapsed' in section_config:
                if not isinstance(section_config['collapsed'], bool):
                    raise ValidationError(f"Section collapsed property must be boolean for section '{section_key}'")

            if 'icon' in section_config:
                icon = section_config['icon']
                if not isinstance(icon, str):
                    raise ValidationError(f"Section icon must be a string for section '{section_key}'")
                # Basic validation for Bootstrap icons
                if icon and not icon.startswith('bi-'):
                    raise ValidationError(f"Invalid icon format for section '{section_key}'. Must start with 'bi-'")

        # Check for duplicate orders
        if len(section_orders) != len(set(section_orders)):
            raise ValidationError("Section orders must be unique")

        return True

    @staticmethod
    def validate_data_sources(data_sources):
        """
        Validate data sources configuration.

        Args:
            data_sources (dict): Data sources configuration

        Raises:
            ValidationError: If configuration is invalid
        """
        if not isinstance(data_sources, dict):
            raise ValidationError("data_sources must be a dictionary")

        for source_name, source_data in data_sources.items():
            # Validate source name
            if not isinstance(source_name, str) or not source_name:
                raise ValidationError(f"Invalid data source name: {source_name}")

            # Validate source data is a list
            if not isinstance(source_data, list):
                raise ValidationError(f"Data source '{source_name}' must be a list")

            # Validate each item is a dictionary
            for idx, item in enumerate(source_data):
                if not isinstance(item, dict):
                    raise ValidationError(
                        f"Item {idx} in data source '{source_name}' must be a dictionary"
                    )

                # Validate item has at least one key
                if not item:
                    raise ValidationError(
                        f"Item {idx} in data source '{source_name}' cannot be empty"
                    )

    @staticmethod
    def validate_field_data_source_reference(field_name, field_config, available_sources):
        """
        Validate that field's data source reference is valid.

        Args:
            field_name (str): Name of the field
            field_config (dict): Field configuration
            available_sources (dict): Available data sources

        Raises:
            ValidationError: If reference is invalid
        """
        data_source = field_config.get('data_source')
        data_source_key = field_config.get('data_source_key')

        # Both or neither must be present
        if bool(data_source) != bool(data_source_key):
            raise ValidationError(
                f"Field '{field_name}': both 'data_source' and 'data_source_key' "
                f"must be specified together"
            )

        # If present, validate
        if data_source:
            # Check source exists
            if data_source not in available_sources:
                raise ValidationError(
                    f"Field '{field_name}': data source '{data_source}' not found. "
                    f"Available: {list(available_sources.keys())}"
                )

            # Check key exists in at least one item
            source_items = available_sources[data_source]
            if source_items:
                first_item = source_items[0]
                if data_source_key not in first_item:
                    raise ValidationError(
                        f"Field '{field_name}': key '{data_source_key}' not found in "
                        f"data source '{data_source}'. Available keys: {list(first_item.keys())}"
                    )

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