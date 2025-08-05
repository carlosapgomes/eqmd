"""
Section utilities for PDF form handling.
"""
from django.core.exceptions import ValidationError


class SectionUtils:
    """Utilities for handling form sections."""
    
    # Default section icons available for use
    DEFAULT_SECTION_ICONS = {
        'patient_info': 'bi-person',
        'contact_info': 'bi-telephone',
        'medical_history': 'bi-journal-medical',
        'procedure_details': 'bi-clipboard-pulse',
        'prescription': 'bi-prescription2',
        'hospital_info': 'bi-hospital',
        'emergency_contact': 'bi-exclamation-triangle',
        'insurance': 'bi-shield-check',
        'general': 'bi-file-text',
        'notes': 'bi-journal-text',
        'vitals': 'bi-heart-pulse',
        'diagnosis': 'bi-clipboard-check',
        'treatment': 'bi-capsule',
        'discharge': 'bi-box-arrow-right'
    }
    
    @staticmethod
    def get_default_section_config():
        """Return default section configuration template."""
        return {
            'label': '',
            'description': '',
            'order': 1,
            'collapsed': False,
            'icon': ''
        }
    
    @staticmethod
    def migrate_unsectioned_form(field_config):
        """
        Convert old format (fields only) to new sectioned format.
        
        Args:
            field_config (dict): Original field configuration
            
        Returns:
            dict: New sectioned format with default section
        """
        if not isinstance(field_config, dict):
            return field_config
        
        # Check if already in new format
        if 'sections' in field_config and 'fields' in field_config:
            return field_config
        
        # Check if it's empty
        if not field_config:
            return {
                'sections': {},
                'fields': {}
            }
        
        # Migrate to new format with default section
        default_section_key = 'form_fields'
        migrated_config = {
            'sections': {
                default_section_key: {
                    'label': 'Campos do Formulário',
                    'description': 'Todos os campos do formulário',
                    'order': 1,
                    'collapsed': False,
                    'icon': 'bi-file-text'
                }
            },
            'fields': {}
        }
        
        # Move all fields to the default section
        field_order = 1
        for field_name, field_data in field_config.items():
            if isinstance(field_data, dict):
                # Add section assignment and field order
                migrated_field_data = field_data.copy()
                migrated_field_data['section'] = default_section_key
                migrated_field_data['field_order'] = field_order
                migrated_config['fields'][field_name] = migrated_field_data
                field_order += 1
        
        return migrated_config
    
    @staticmethod
    def validate_section_assignment(sections, fields):
        """
        Validate that all field section assignments reference existing sections.
        
        Args:
            sections (dict): Sections configuration
            fields (dict): Fields configuration
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        errors = []
        
        if not isinstance(sections, dict) or not isinstance(fields, dict):
            return False, ['Sections and fields must be dictionaries']
        
        section_keys = set(sections.keys())
        
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                errors.append(f"Field '{field_name}' configuration must be a dictionary")
                continue
            
            # Check if field has section assignment
            if 'section' in field_config:
                section_key = field_config['section']
                if section_key and section_key not in section_keys:
                    errors.append(f"Field '{field_name}' references non-existent section '{section_key}'")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_section_icons():
        """Return available Bootstrap icons for sections."""
        return [
            {'value': '', 'label': 'No Icon'},
            {'value': 'bi-person', 'label': 'Person'},
            {'value': 'bi-telephone', 'label': 'Phone'},
            {'value': 'bi-journal-medical', 'label': 'Medical Journal'},
            {'value': 'bi-clipboard-pulse', 'label': 'Medical Clipboard'},
            {'value': 'bi-prescription2', 'label': 'Prescription'},
            {'value': 'bi-hospital', 'label': 'Hospital'},
            {'value': 'bi-exclamation-triangle', 'label': 'Emergency'},
            {'value': 'bi-shield-check', 'label': 'Insurance'},
            {'value': 'bi-file-text', 'label': 'Document'},
            {'value': 'bi-journal-text', 'label': 'Notes'},
            {'value': 'bi-heart-pulse', 'label': 'Vitals'},
            {'value': 'bi-clipboard-check', 'label': 'Diagnosis'},
            {'value': 'bi-capsule', 'label': 'Treatment'},
            {'value': 'bi-box-arrow-right', 'label': 'Discharge'}
        ]
    
    @staticmethod
    def organize_fields_by_section(sections_config, fields_config):
        """
        Organize fields by their section assignments.
        
        Args:
            sections_config (dict): Sections configuration
            fields_config (dict): Fields configuration
            
        Returns:
            dict: Organized structure with sections and their fields
        """
        if not isinstance(sections_config, dict) or not isinstance(fields_config, dict):
            return {'sections': {}, 'unsectioned_fields': list(fields_config.keys()) if fields_config else []}
        
        # Sort sections by order
        sorted_sections = sorted(
            sections_config.items(),
            key=lambda x: x[1].get('order', 999)
        )
        
        organized = {
            'sections': {},
            'unsectioned_fields': []
        }
        
        # Initialize sections
        for section_key, section_config in sorted_sections:
            organized['sections'][section_key] = {
                'info': section_config,
                'fields': []
            }
        
        # Assign fields to sections
        for field_name, field_config in fields_config.items():
            if not isinstance(field_config, dict):
                continue
                
            section_key = field_config.get('section')
            
            if section_key and section_key in organized['sections']:
                organized['sections'][section_key]['fields'].append({
                    'name': field_name,
                    'config': field_config,
                    'order': field_config.get('field_order', 999)
                })
            else:
                organized['unsectioned_fields'].append(field_name)
        
        # Sort fields within each section by field_order
        for section_key in organized['sections']:
            organized['sections'][section_key]['fields'].sort(
                key=lambda x: x['order']
            )
        
        return organized
    
    @staticmethod
    def get_section_field_count(section_key, fields_config):
        """
        Count fields assigned to a specific section.
        
        Args:
            section_key (str): Section identifier
            fields_config (dict): Fields configuration
            
        Returns:
            int: Number of fields assigned to the section
        """
        if not isinstance(fields_config, dict):
            return 0
        
        count = 0
        for field_config in fields_config.values():
            if isinstance(field_config, dict) and field_config.get('section') == section_key:
                count += 1
        
        return count
    
    @staticmethod
    def create_section_key(label):
        """
        Create a valid section key from a label.
        
        Args:
            label (str): Section label
            
        Returns:
            str: Valid section key
        """
        if not isinstance(label, str):
            return 'section'
        
        # Convert to lowercase, replace spaces with underscores, keep only alphanumeric and underscores
        key = label.lower().replace(' ', '_')
        key = ''.join(c for c in key if c.isalnum() or c == '_')
        
        # Ensure it doesn't start with a number
        if key and key[0].isdigit():
            key = 'section_' + key
        
        # Fallback if empty
        return key if key else 'section'
    
    @staticmethod
    def get_next_section_order(sections_config):
        """
        Get the next available section order number.
        
        Args:
            sections_config (dict): Existing sections configuration
            
        Returns:
            int: Next available order number
        """
        if not isinstance(sections_config, dict) or not sections_config:
            return 1
        
        max_order = 0
        for section_config in sections_config.values():
            if isinstance(section_config, dict):
                order = section_config.get('order', 0)
                if isinstance(order, int) and order > max_order:
                    max_order = order
        
        return max_order + 1
    
    @staticmethod
    def ensure_unique_section_key(desired_key, existing_sections):
        """
        Ensure section key is unique by appending numbers if necessary.
        
        Args:
            desired_key (str): Desired section key
            existing_sections (dict): Existing sections configuration
            
        Returns:
            str: Unique section key
        """
        if not isinstance(existing_sections, dict):
            return desired_key
        
        if desired_key not in existing_sections:
            return desired_key
        
        counter = 1
        while f"{desired_key}_{counter}" in existing_sections:
            counter += 1
        
        return f"{desired_key}_{counter}"