from django import forms
from django.core.exceptions import ValidationError


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

    def generate_form_class(self, pdf_template):
        """
        Create Django form class from PDF template field configuration.

        Args:
            pdf_template (PDFFormTemplate): Template with field configuration

        Returns:
            type: Django form class
        """
        form_fields = {}
        field_config = pdf_template.form_fields

        for field_name, config in field_config.items():
            django_field = self._create_django_field(field_name, config)
            if django_field:
                form_fields[field_name] = django_field

        # Create form class dynamically
        form_class_name = f"{pdf_template.name.replace(' ', '')}Form"

        # Add custom validation method
        def clean(self):
            cleaned_data = super().clean()
            # Add custom validation logic here
            return cleaned_data

        form_fields['clean'] = clean

        # Create the form class
        return type(form_class_name, (forms.Form,), form_fields)

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