from django import forms
from django.core.exceptions import ValidationError
from .field_mapping import DataFieldMapper
from .section_utils import SectionUtils
from .data_source_utils import DataSourceUtils


class DynamicFormGenerator:
    """
    Generate Django forms based on PDF field configuration.
    Creates form classes dynamically from PDF field mappings.
    """

    FIELD_TYPE_MAPPING = {
        'text': forms.CharField,
        'textarea': forms.CharField,
        'email': forms.EmailField,
        'number': forms.IntegerField,
        'decimal': forms.DecimalField,
        'date': forms.DateField,
        'datetime': forms.DateTimeField,
        'boolean': forms.BooleanField,
        'choice': forms.ChoiceField,
        'multiple_choice': forms.MultipleChoiceField,
    }

    def generate_form_class(self, pdf_template, patient=None):
        """
        Create Django form class from PDF template field configuration.
        Enhanced to handle sectioned field organization.

        Args:
            pdf_template (PDFFormTemplate): Template with field configuration
            patient: Patient object for field auto-population (optional)

        Returns:
            type: Django form class with section metadata
        """
        form_fields = {}
        field_config = pdf_template.form_fields or {}
        initial_values = {}
        
        # Handle empty configuration gracefully (backward compatibility)
        if not field_config:
            # Return empty form class for unconfigured templates
            form_class_name = f"{pdf_template.name.replace(' ', '')}Form"
            form_class = type(form_class_name, (forms.Form,), {})
            
            # Add section metadata for consistency
            form_class._sections_metadata = {'sections': {}, 'unsectioned_fields': []}
            form_class._has_sections = False
            form_class._unsectioned_fields = []
            form_class._patient_initial_values = {}
            
            return form_class

        # Handle both new sectioned format and legacy format
        sections_config, fields_config = self._extract_sections_and_fields(field_config)
        
        # Handle case where fields_config is empty but we have sections
        if not fields_config:
            # Return empty form class for templates with no fields
            form_class_name = f"{pdf_template.name.replace(' ', '')}Form"
            form_class = type(form_class_name, (forms.Form,), {})
            
            # Add section metadata (may have sections but no fields)
            organized_sections = SectionUtils.organize_fields_by_section(sections_config, {})
            form_class._sections_metadata = organized_sections
            form_class._has_sections = bool(sections_config)
            form_class._unsectioned_fields = organized_sections.get('unsectioned_fields', [])
            form_class._patient_initial_values = {}
            
            return form_class
        
        # Validate section assignments
        is_valid, errors = SectionUtils.validate_section_assignment(sections_config, fields_config)
        if not is_valid:
            raise ValidationError(f"Section validation failed: {'; '.join(errors)}")

        # Create Django form fields
        for field_name, config in fields_config.items():
            django_field = self._create_django_field(field_name, config, field_config)
            if django_field:
                form_fields[field_name] = django_field
                
                # Check for auto-fill mapping and set initial value
                auto_fill_path = config.get('auto_fill_mapping') or config.get('patient_field_mapping')
                if auto_fill_path:
                    field_value = DataFieldMapper.get_auto_fill_value(auto_fill_path, patient)
                    if field_value is not None:
                        # Format the value based on field type
                        formatted_value = self._format_field_value(field_value, config.get('type', 'text'))
                        if formatted_value is not None:
                            initial_values[field_name] = formatted_value

        # Create form class dynamically
        form_class_name = f"{pdf_template.name.replace(' ', '')}Form"

        # Create the form class
        form_class = type(form_class_name, (forms.Form,), form_fields)

        # Add custom validation method
        def clean(self):
            cleaned_data = super(forms.Form, self).clean()
            # Add custom validation logic here
            return cleaned_data

        # Bind the clean method to the form class
        form_class.clean = clean
        
        # Store initial values as a class attribute for later use
        form_class._patient_initial_values = initial_values

        # Add section metadata to form class
        sections_metadata = self._organize_sections(sections_config, fields_config)
        form_class._sections_metadata = sections_metadata
        form_class._has_sections = bool(sections_config)
        form_class._unsectioned_fields = sections_metadata.get('unsectioned_fields', [])

        # NEW: Store data source metadata on form class
        if 'data_sources' in field_config:
            form_class._linked_fields_map = DataSourceUtils.build_linked_fields_map(
                field_config
            )
        else:
            form_class._linked_fields_map = {}

        return form_class

    def _create_django_field(self, field_name, config, form_config=None):
        """
        Create Django form field from configuration.
        Enhanced to handle data source choices.

        Args:
            field_name (str): Name of the field
            config (dict): Field configuration
            form_config (dict): Complete form configuration (for data sources)

        Returns:
            forms.Field: Django form field instance
        """
        field_type = config.get('type', 'text')
        required = config.get('required', False)
        label = config.get('label', field_name.replace('_', ' ').title())
        help_text = config.get('help_text', '')
        max_length = config.get('max_length')
        choices = config.get('choices', [])

        # NEW: For choice fields, check if using data source
        if field_type == 'choice' and form_config:
            data_source_choices = DataSourceUtils.get_field_choices_from_source(
                form_config, config
            )
            if data_source_choices:
                # Override config choices with data source choices
                config = config.copy()
                choices = data_source_choices

        # Get the Django field class
        field_class = self.FIELD_TYPE_MAPPING.get(field_type, forms.CharField)

        # Build field kwargs
        field_kwargs = {
            'required': required,
            'label': label,
            'help_text': help_text,
        }

        # Add type-specific kwargs
        if field_type == 'textarea':
            field_kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        elif field_type == 'choice' and choices:
            field_kwargs['choices'] = [(c, c) for c in choices]
            field_kwargs['widget'] = forms.Select(attrs={'class': 'form-select'})
        elif field_type == 'multiple_choice' and choices:
            field_kwargs['choices'] = [(c, c) for c in choices]
            field_kwargs['widget'] = forms.CheckboxSelectMultiple()
        elif field_type == 'boolean':
            field_kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})
        elif field_type == 'date':
            field_kwargs['widget'] = forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            })
        elif field_type == 'datetime':
            field_kwargs['widget'] = forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            })
        elif field_type == 'email':
            field_kwargs['widget'] = forms.EmailInput(attrs={'class': 'form-control'})
        elif field_type in ['number', 'decimal']:
            field_kwargs['widget'] = forms.NumberInput(attrs={'class': 'form-control'})
        else:
            # Default text input styling
            field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})

        # Add max_length for text fields
        if max_length and field_type in ['text', 'textarea']:
            field_kwargs['max_length'] = max_length

        # NEW: Add data attributes for linked fields
        if config.get('data_source'):
            widget_attrs = field_kwargs.get('widget', forms.TextInput()).attrs
            widget_attrs['data-source'] = config['data_source']
            widget_attrs['data-source-key'] = config['data_source_key']

            if config.get('linked_readonly'):
                widget_attrs['data-linked-readonly'] = 'true'

            # Update widget with attributes
            if 'widget' in field_kwargs:
                field_kwargs['widget'].attrs.update(widget_attrs)
            else:
                field_kwargs['widget'] = forms.TextInput(attrs=widget_attrs)

        return field_class(**field_kwargs)

    def _format_field_value(self, value, field_type):
        """
        Format auto-fill field value for form field based on type.
        
        Args:
            value: Raw value from auto-fill source (patient or hospital data)
            field_type (str): Type of the form field
            
        Returns:
            Any: Formatted value suitable for the form field
        """
        if value is None:
            return None
            
        try:
            if field_type == 'date':
                # Handle date fields - convert to string format expected by HTML date input
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%d')
                return str(value)
            elif field_type == 'datetime':
                # Handle datetime fields
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%dT%H:%M')
                return str(value)
            elif field_type in ['number', 'decimal']:
                # Convert to number if possible
                if isinstance(value, (int, float)):
                    return value
                try:
                    return int(value) if field_type == 'number' else float(value)
                except (ValueError, TypeError):
                    return None
            elif field_type == 'boolean':
                # Convert to boolean
                if isinstance(value, bool):
                    return value
                return bool(value)
            elif field_type == 'choice':
                # For choice fields, return the string representation
                return str(value)
            else:
                # Default to string representation for text, textarea, email, etc.
                return str(value)
        except (ValueError, TypeError, AttributeError):
            # If any formatting fails, return None to avoid form errors
            return None

    def _extract_sections_and_fields(self, field_config):
        """
        Extract sections and fields from configuration, handling both formats.
        
        Args:
            field_config (dict): Raw field configuration
            
        Returns:
            tuple: (sections_config, fields_config)
        """
        if not isinstance(field_config, dict):
            return {}, {}
        
        # Check if it's in new sectioned format
        if 'sections' in field_config and 'fields' in field_config:
            return field_config.get('sections', {}), field_config.get('fields', {})
        else:
            # Legacy format - treat entire config as fields
            return {}, field_config

    def _organize_sections(self, sections_config, fields_config):
        """
        Organize sections and fields into structured format for template rendering.
        
        Args:
            sections_config (dict): Sections configuration
            fields_config (dict): Fields configuration
            
        Returns:
            dict: Organized structure with sections and their fields
        """
        # Use SectionUtils to organize fields by section
        organized = SectionUtils.organize_fields_by_section(sections_config, fields_config)
        
        # Convert field lists to just field names for template compatibility
        for section_key in organized['sections']:
            field_objects = organized['sections'][section_key]['fields']
            organized['sections'][section_key]['fields'] = [
                field_obj['name'] for field_obj in field_objects
            ]
        
        return organized

    def _sort_sections_by_order(self, sections):
        """
        Sort sections by their order property.
        
        Args:
            sections (dict): Sections configuration
            
        Returns:
            list: Sorted list of (section_key, section_config) tuples
        """
        if not isinstance(sections, dict):
            return []
        
        return sorted(
            sections.items(),
            key=lambda x: x[1].get('order', 999) if isinstance(x[1], dict) else 999
        )

    def _sort_fields_within_section(self, fields, field_configs):
        """
        Sort fields within a section by field_order property.
        
        Args:
            fields (list): List of field names
            field_configs (dict): Fields configuration
            
        Returns:
            list: Sorted list of field names
        """
        if not isinstance(fields, list) or not isinstance(field_configs, dict):
            return fields
        
        return sorted(
            fields,
            key=lambda field_name: field_configs.get(field_name, {}).get('field_order', 999)
        )

    def _get_section_field_count(self, section_key, field_configs):
        """
        Count fields assigned to a specific section.
        
        Args:
            section_key (str): Section identifier
            field_configs (dict): Fields configuration
            
        Returns:
            int: Number of fields assigned to the section
        """
        return SectionUtils.get_section_field_count(section_key, field_configs)