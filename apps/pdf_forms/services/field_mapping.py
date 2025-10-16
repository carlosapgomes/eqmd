"""
Field mapping utilities for PDF forms.
Provides helpers for converting between different field representations and patient field mappings.
"""

from django.core.exceptions import ValidationError
from django.apps import apps


class DataFieldMapper:
    """
    Utilities for mapping PDF form fields to patient and hospital data.
    """

    # Available patient fields with their types and labels
    PATIENT_FIELD_MAPPINGS = {
        'name': {'type': 'text', 'label': 'Nome do Paciente'},
        'birthday': {'type': 'date', 'label': 'Data de Nascimento'},
        'age': {'type': 'number', 'label': 'Idade'},
        'healthcard_number': {'type': 'text', 'label': 'Número do Cartão de Saúde'},
        'id_number': {'type': 'text', 'label': 'Número de Identidade'},
        'fiscal_number': {'type': 'text', 'label': 'Número Fiscal'},
        'phone': {'type': 'text', 'label': 'Telefone'},
        'address': {'type': 'text', 'label': 'Endereço'},
        'city': {'type': 'text', 'label': 'Cidade'},
        'state': {'type': 'text', 'label': 'Estado/Província'},
        'zip_code': {'type': 'text', 'label': 'Código Postal'},
        'current_record_number': {'type': 'text', 'label': 'Número do Prontuário'},
        'gender': {'type': 'choice', 'label': 'Sexo'},
        'bed': {'type': 'text', 'label': 'Leito/Cama'},
        'ward.name': {'type': 'text', 'label': 'Nome da Ala'},
        'ward.abbreviation': {'type': 'text', 'label': 'Sigla da Ala'},
        'ward.floor': {'type': 'text', 'label': 'Andar da Ala'},
        'last_admission_date': {'type': 'date', 'label': 'Data da Última Admissão'},
        'last_discharge_date': {'type': 'date', 'label': 'Data da Última Alta'},
        'status': {'type': 'choice', 'label': 'Status do Paciente'},
        'total_admissions_count': {'type': 'number', 'label': 'Total de Internações'},
        'total_inpatient_days': {'type': 'number', 'label': 'Total de Dias Internado'},
    }

    # Available hospital fields with their types and labels
    HOSPITAL_FIELD_MAPPINGS = {
        'name': {'type': 'text', 'label': 'Nome do Hospital'},
        'address': {'type': 'text', 'label': 'Endereço do Hospital'},
        'phone': {'type': 'text', 'label': 'Telefone do Hospital'},
        'email': {'type': 'text', 'label': 'Email do Hospital'},
        'website': {'type': 'text', 'label': 'Website do Hospital'},
        'cnes': {'type': 'text', 'label': 'CNES do Hospital'},
        'cnpj': {'type': 'text', 'label': 'CNPJ do Hospital'},
    }

    # Combined mappings for dropdown choices
    @classmethod
    def get_auto_fill_choices(cls):
        """
        Get choices for auto-fill dropdown formatted for template rendering.
        
        Returns:
            list: List of choice dictionaries with value, label, and optgroup
        """
        choices = [
            {'value': '', 'label': '--- Selecione uma opção ---', 'optgroup': None}
        ]
        
        # Add patient data options
        for key, mapping in cls.PATIENT_FIELD_MAPPINGS.items():
            choices.append({
                'value': f'patient.{key}',
                'label': mapping['label'],
                'type': mapping['type'],
                'optgroup': 'Dados do Paciente'
            })
        
        # Add hospital data options
        for key, mapping in cls.HOSPITAL_FIELD_MAPPINGS.items():
            choices.append({
                'value': f'hospital.{key}',
                'label': mapping['label'], 
                'type': mapping['type'],
                'optgroup': 'Dados do Hospital'
            })
        
        return choices

    @classmethod
    def get_available_patient_fields(cls):
        """
        Get list of available patient fields for mapping.
        
        Returns:
            dict: Available patient fields with types and labels
        """
        return cls.PATIENT_FIELD_MAPPINGS.copy()

    @classmethod
    def validate_auto_fill_mapping(cls, field_name, auto_fill_path):
        """
        Validate that an auto-fill field mapping is valid.
        
        Args:
            field_name (str): Name of the form field
            auto_fill_path (str): Path like 'patient.name' or 'hospital.cnes'
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not auto_fill_path:
            return True, None  # No mapping is valid
            
        # Parse the path
        if '.' not in auto_fill_path:
            return False, f"Invalid auto-fill path '{auto_fill_path}'. Must be in format 'source.field'"
            
        source, field_key = auto_fill_path.split('.', 1)
        
        if source == 'patient':
            if field_key not in cls.PATIENT_FIELD_MAPPINGS:
                available_fields = ', '.join(cls.PATIENT_FIELD_MAPPINGS.keys())
                return False, f"Invalid patient field '{field_key}'. Available fields: {available_fields}"
        elif source == 'hospital':
            if field_key not in cls.HOSPITAL_FIELD_MAPPINGS:
                available_fields = ', '.join(cls.HOSPITAL_FIELD_MAPPINGS.keys())
                return False, f"Invalid hospital field '{field_key}'. Available fields: {available_fields}"
        else:
            return False, f"Invalid auto-fill source '{source}'. Must be 'patient' or 'hospital'"
            
        return True, None

    @classmethod
    def validate_patient_field_mapping(cls, field_name, patient_field_path):
        """
        Legacy method - validate that a patient field mapping is valid.
        
        Args:
            field_name (str): Name of the form field
            patient_field_path (str): Dot-notation path to patient field
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not patient_field_path:
            return True, None  # No mapping is valid
            
        if patient_field_path not in cls.PATIENT_FIELD_MAPPINGS:
            available_fields = ', '.join(cls.PATIENT_FIELD_MAPPINGS.keys())
            return False, f"Invalid patient field '{patient_field_path}'. Available fields: {available_fields}"
            
        return True, None

    @classmethod
    def get_auto_fill_value(cls, auto_fill_path, patient=None):
        """
        Get value from auto-fill path (patient or hospital data).
        
        Args:
            auto_fill_path (str): Path like 'patient.name' or 'hospital.cnes'
            patient: Patient object (required for patient data)
            
        Returns:
            Any: Field value or None if not found
        """
        if not auto_fill_path:
            return None
            
        # Parse the path
        if '.' not in auto_fill_path:
            return None
            
        source, field_key = auto_fill_path.split('.', 1)
        
        if source == 'patient':
            return cls.get_patient_field_value(patient, field_key)
        elif source == 'hospital':
            return cls.get_hospital_field_value(field_key)
        else:
            return None

    @classmethod
    def get_patient_field_value(cls, patient, field_path):
        """
        Get value from patient object using dot notation.
        
        Args:
            patient: Patient object
            field_path (str): Dot-notation path to field (e.g., 'ward.name')
            
        Returns:
            Any: Field value or None if not found
        """
        if not patient or not field_path:
            return None
            
        try:
            # Split the path and traverse the object
            parts = field_path.split('.')
            current_obj = patient
            
            for part in parts:
                if hasattr(current_obj, part):
                    current_obj = getattr(current_obj, part)
                    if current_obj is None:
                        return None
                else:
                    return None
                    
            return current_obj
        except (AttributeError, TypeError):
            return None

    @classmethod
    def get_hospital_field_value(cls, field_key):
        """
        Get value from hospital configuration.
        
        Args:
            field_key (str): Hospital field key (e.g., 'name', 'cnes')
            
        Returns:
            Any: Field value or None if not found
        """
        from django.conf import settings
        
        if not field_key:
            return None
            
        hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
        return hospital_config.get(field_key, None)

    @classmethod
    def get_field_type_compatibility(cls, form_field_type, auto_fill_path):
        """
        Check if form field type is compatible with auto-fill field type.
        
        Args:
            form_field_type (str): Type of the form field
            auto_fill_path (str): Auto-fill path like 'patient.name' or 'hospital.cnes'
            
        Returns:
            bool: True if compatible, False otherwise
        """
        if not auto_fill_path:
            return True  # No mapping is always "compatible"
            
        # Parse the path to get field type
        if '.' not in auto_fill_path:
            return True
            
        source, field_key = auto_fill_path.split('.', 1)
        
        # Get field type from mappings
        data_field_type = None
        if source == 'patient' and field_key in cls.PATIENT_FIELD_MAPPINGS:
            data_field_type = cls.PATIENT_FIELD_MAPPINGS[field_key]['type']
        elif source == 'hospital' and field_key in cls.HOSPITAL_FIELD_MAPPINGS:
            data_field_type = cls.HOSPITAL_FIELD_MAPPINGS[field_key]['type']
        
        if not data_field_type:
            return True  # Invalid mapping is always "compatible"
        
        # Define compatibility rules
        compatibility_matrix = {
            'text': ['text', 'choice', 'number'],  # Text can accept most types as strings
            'textarea': ['text', 'choice'],
            'email': ['text'],
            'number': ['number', 'text'],
            'decimal': ['number', 'text'],
            'date': ['date', 'text'],
            'datetime': ['date', 'text'],
            'boolean': ['text', 'choice'],
            'choice': ['text', 'choice', 'number'],
            'multiple_choice': ['text', 'choice'],
        }
        
        compatible_types = compatibility_matrix.get(form_field_type, [])
        return data_field_type in compatible_types


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

            # Validate auto-fill mapping if present (new format)
            if 'auto_fill_mapping' in config:
                auto_fill_path = config['auto_fill_mapping']
                is_valid, error_msg = DataFieldMapper.validate_auto_fill_mapping(field_name, auto_fill_path)
                if not is_valid:
                    errors.append(f"Field '{field_name}' has invalid auto-fill mapping: {error_msg}")
                
                # Check field type compatibility
                if auto_fill_path and not DataFieldMapper.get_field_type_compatibility(field_type, auto_fill_path):
                    # Parse path to get field info
                    if '.' in auto_fill_path:
                        source, field_key = auto_fill_path.split('.', 1)
                        if source == 'patient' and field_key in DataFieldMapper.PATIENT_FIELD_MAPPINGS:
                            data_type = DataFieldMapper.PATIENT_FIELD_MAPPINGS[field_key]['type']
                        elif source == 'hospital' and field_key in DataFieldMapper.HOSPITAL_FIELD_MAPPINGS:
                            data_type = DataFieldMapper.HOSPITAL_FIELD_MAPPINGS[field_key]['type']
                        else:
                            data_type = 'unknown'
                        errors.append(f"Field '{field_name}' type '{field_type}' is not compatible with {source} field type '{data_type}'")

            # Validate patient field mapping if present (legacy format)
            if 'patient_field_mapping' in config:
                patient_field_path = config['patient_field_mapping']
                is_valid, error_msg = DataFieldMapper.validate_patient_field_mapping(field_name, patient_field_path)
                if not is_valid:
                    errors.append(f"Field '{field_name}' has invalid patient field mapping: {error_msg}")
                
                # Check field type compatibility
                if patient_field_path and not DataFieldMapper.get_field_type_compatibility(field_type, f'patient.{patient_field_path}'):
                    patient_info = DataFieldMapper.PATIENT_FIELD_MAPPINGS.get(patient_field_path, {})
                    patient_type = patient_info.get('type', 'unknown')
                    errors.append(f"Field '{field_name}' type '{field_type}' is not compatible with patient field type '{patient_type}'")

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