from django import forms
from django.core.exceptions import ValidationError
from .field_mapping import PatientFieldMapper


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

        Args:
            pdf_template (PDFFormTemplate): Template with field configuration
            patient: Patient object for field auto-population (optional)

        Returns:
            type: Django form class
        """
        form_fields = {}
        field_config = pdf_template.form_fields or {}
        initial_values = {}
        
        # Check if template is configured
        if not field_config:
            raise ValidationError(
                f"Template '{pdf_template.name}' is not configured. "
                "Please configure the field positions first using the admin interface."
            )

        for field_name, config in field_config.items():
            django_field = self._create_django_field(field_name, config)
            if django_field:
                form_fields[field_name] = django_field
                
                # Check for patient field mapping and set initial value
                if patient and 'patient_field_mapping' in config:
                    patient_field_path = config['patient_field_mapping']
                    if patient_field_path:
                        field_value = PatientFieldMapper.get_patient_field_value(patient, patient_field_path)
                        if field_value is not None:
                            # Format the value based on field type
                            formatted_value = self._format_patient_field_value(field_value, config.get('type', 'text'))
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

        return form_class

    def _create_django_field(self, field_name, config):
        """
        Create Django form field from configuration.

        Args:
            field_name (str): Name of the field
            config (dict): Field configuration

        Returns:
            forms.Field: Django form field instance
        """
        field_type = config.get('type', 'text')
        required = config.get('required', False)
        label = config.get('label', field_name.replace('_', ' ').title())
        help_text = config.get('help_text', '')
        max_length = config.get('max_length')
        choices = config.get('choices', [])

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

        return field_class(**field_kwargs)

    def _format_patient_field_value(self, value, field_type):
        """
        Format patient field value for form field based on type.
        
        Args:
            value: Raw value from patient field
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