"""
Field mapping utilities for PDF forms.
Provides helpers for converting between different field representations.
"""

from django.core.exceptions import ValidationError


class FieldMappingUtils:
    """
    Utilities for handling PDF form field mappings and conversions.
    """

    @staticmethod
    def validate_field_config(field_config):
        """
        Validate field configuration structure.

        Args:
            field_config (dict): Field configuration to validate

        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(field_config, dict):
            return False, ["Field configuration must be a dictionary"]

        for field_name, config in field_config.items():
            if not isinstance(config, dict):
                errors.append(f"Configuration for field '{field_name}' must be a dictionary")
                continue

            # Required fields
            required_fields = ['type', 'label']
            for required_field in required_fields:
                if required_field not in config:
                    errors.append(f"Field '{field_name}' missing required '{required_field}'")

            # Validate field type
            valid_types = ['text', 'textarea', 'email', 'number', 'decimal', 'date', 'datetime', 'boolean', 'choice', 'multiple_choice']
            field_type = config.get('type')
            if field_type not in valid_types:
                errors.append(f"Field '{field_name}' has invalid type '{field_type}'. Valid types: {valid_types}")

            # Validate coordinates
            for coord in ['x', 'y']:
                if coord in config:
                    try:
                        float(config[coord])
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field_name}' has invalid {coord} coordinate: must be a number")

            # Validate dimensions
            for dim in ['width', 'height']:
                if dim in config:
                    try:
                        value = float(config[dim])
                        if value <= 0:
                            errors.append(f"Field '{field_name}' has invalid {dim}: must be greater than 0")
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field_name}' has invalid {dim}: must be a number")

            # Validate font size
            if 'font_size' in config:
                try:
                    font_size = int(config['font_size'])
                    if font_size < 6 or font_size > 72:
                        errors.append(f"Field '{field_name}' has invalid font_size: must be between 6 and 72")
                except (ValueError, TypeError):
                    errors.append(f"Field '{field_name}' has invalid font_size: must be an integer")

            # Validate choices for choice fields
            if field_type in ['choice', 'multiple_choice']:
                if 'choices' not in config:
                    errors.append(f"Field '{field_name}' of type '{field_type}' must have 'choices'")
                elif not isinstance(config['choices'], list):
                    errors.append(f"Field '{field_name}' choices must be a list")
                elif not config['choices']:
                    errors.append(f"Field '{field_name}' choices cannot be empty")

        return len(errors) == 0, errors

    @staticmethod
    def get_default_field_config():
        """
        Get default field configuration template.

        Returns:
            dict: Default field configuration structure
        """
        return {
            "patient_name": {
                "type": "text",
                "label": "Nome do Paciente",
                "x": 5.2,
                "y": 10.5,
                "width": 8.0,
                "height": 0.7,
                "font_size": 12,
                "font_family": "Helvetica",
                "required": True,
                "max_length": 100
            },
            "date": {
                "type": "date",
                "label": "Data",
                "x": 15.0,
                "y": 10.5,
                "width": 4.0,
                "height": 0.7,
                "font_size": 12,
                "font_family": "Helvetica",
                "required": True
            },
            "signature": {
                "type": "text",
                "label": "Assinatura",
                "x": 5.2,
                "y": 25.0,
                "width": 8.0,
                "height": 0.7,
                "font_size": 12,
                "font_family": "Helvetica",
                "required": False,
                "max_length": 100
            }
        }

    @staticmethod
    def convert_coordinates(x_cm, y_cm, page_width_pt, page_height_pt):
        """
        Convert centimeter coordinates to PDF points.

        Args:
            x_cm (float): X coordinate in centimeters
            y_cm (float): Y coordinate in centimeters
            page_width_pt (float): Page width in points
            page_height_pt (float): Page height in points

        Returns:
            tuple: (x_points, y_points)
        """
        # 1 cm = 28.35 points (72 points per inch, 2.54 cm per inch)
        cm_to_points = 28.35
        
        x_points = x_cm * cm_to_points
        # Convert y coordinate (PDF origin is bottom-left, config uses top-left)
        y_points = page_height_pt - (y_cm * cm_to_points)
        
        return x_points, y_points

    @staticmethod
    def generate_sample_config(form_type="generic"):
        """
        Generate sample field configuration for different form types.

        Args:
            form_type (str): Type of form ("generic", "transfusion", "icu_transfer")

        Returns:
            dict: Sample field configuration
        """
        if form_type == "transfusion":
            return {
                "patient_name": {
                    "type": "text",
                    "label": "Nome do Paciente",
                    "x": 5.2,
                    "y": 3.0,
                    "width": 8.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True,
                    "max_length": 100
                },
                "blood_type": {
                    "type": "choice",
                    "label": "Tipo Sanguíneo",
                    "x": 15.0,
                    "y": 3.0,
                    "width": 3.0,
                    "height": 0.7,
                    "font_size": 12,
                    "choices": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                    "required": True
                },
                "units_requested": {
                    "type": "number",
                    "label": "Unidades Solicitadas",
                    "x": 5.2,
                    "y": 5.0,
                    "width": 3.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True
                },
                "urgency": {
                    "type": "choice",
                    "label": "Urgência",
                    "x": 10.0,
                    "y": 5.0,
                    "width": 4.0,
                    "height": 0.7,
                    "font_size": 12,
                    "choices": ["Rotina", "Urgente", "Emergência"],
                    "required": True
                },
                "clinical_indication": {
                    "type": "textarea",
                    "label": "Indicação Clínica",
                    "x": 5.2,
                    "y": 7.0,
                    "width": 12.0,
                    "height": 3.0,
                    "font_size": 11,
                    "required": True
                },
                "requesting_doctor": {
                    "type": "text",
                    "label": "Médico Solicitante",
                    "x": 5.2,
                    "y": 22.0,
                    "width": 8.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True,
                    "max_length": 100
                },
                "request_date": {
                    "type": "date",
                    "label": "Data da Solicitação",
                    "x": 15.0,
                    "y": 22.0,
                    "width": 4.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True
                }
            }
        elif form_type == "icu_transfer":
            return {
                "patient_name": {
                    "type": "text",
                    "label": "Nome do Paciente",
                    "x": 5.2,
                    "y": 3.0,
                    "width": 8.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True,
                    "max_length": 100
                },
                "current_location": {
                    "type": "text",
                    "label": "Localização Atual",
                    "x": 15.0,
                    "y": 3.0,
                    "width": 4.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True,
                    "max_length": 50
                },
                "requested_icu": {
                    "type": "choice",
                    "label": "UTI Solicitada",
                    "x": 5.2,
                    "y": 5.0,
                    "width": 6.0,
                    "height": 0.7,
                    "font_size": 12,
                    "choices": ["UTI Geral", "UTI Cardiológica", "UTI Neurológica", "UTI Pediátrica"],
                    "required": True
                },
                "clinical_condition": {
                    "type": "textarea",
                    "label": "Condição Clínica",
                    "x": 5.2,
                    "y": 7.0,
                    "width": 12.0,
                    "height": 4.0,
                    "font_size": 11,
                    "required": True
                },
                "life_support": {
                    "type": "boolean",
                    "label": "Necessita Suporte à Vida",
                    "x": 5.2,
                    "y": 13.0,
                    "width": 0.5,
                    "height": 0.5,
                    "required": False
                },
                "requesting_doctor": {
                    "type": "text",
                    "label": "Médico Solicitante",
                    "x": 5.2,
                    "y": 22.0,
                    "width": 8.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True,
                    "max_length": 100
                },
                "request_date": {
                    "type": "date",
                    "label": "Data da Solicitação",
                    "x": 15.0,
                    "y": 22.0,
                    "width": 4.0,
                    "height": 0.7,
                    "font_size": 12,
                    "required": True
                }
            }
        else:
            # Generic form
            return FieldMappingUtils.get_default_field_config()