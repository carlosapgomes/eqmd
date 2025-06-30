from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.db import models
from apps.drugtemplates.models import DrugTemplate
import json


class DrugTemplateSelectWidget(forms.Select):
    """
    Enhanced select widget for drug templates with template data embedded.
    """
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def format_value(self, value):
        """Format the value for display."""
        if value is None:
            return ''
        return str(value)
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """Create option with template data attributes."""
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        if value and value != '':
            try:
                template = DrugTemplate.objects.get(pk=value)
                option['attrs'].update({
                    'data-name': template.name,
                    'data-presentation': template.presentation,
                    'data-usage-instructions': template.usage_instructions,
                    'data-template-id': str(template.id)
                })
            except DrugTemplate.DoesNotExist:
                pass
        
        return option
    
    def get_context(self, name, value, attrs):
        """Get context for rendering."""
        context = super().get_context(name, value, attrs)
        
        # Add CSS classes for styling and JavaScript hooks
        if 'class' not in context['widget']['attrs']:
            context['widget']['attrs']['class'] = ''
        
        context['widget']['attrs']['class'] += ' drug-template-select'
        context['widget']['attrs']['data-toggle'] = 'template-select'
        
        return context


class DrugTemplateField(forms.ModelChoiceField):
    """
    Enhanced ModelChoiceField for drug templates with user-based queryset.
    """
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        
        # Set up queryset based on user
        if user:
            queryset = DrugTemplate.objects.filter(
                models.Q(creator=user) | models.Q(is_public=True)
            ).order_by('name')
        else:
            queryset = DrugTemplate.objects.filter(is_public=True).order_by('name')
        
        kwargs['queryset'] = queryset
        kwargs['empty_label'] = "Selecione um template (opcional)"
        kwargs['required'] = False
        
        # Use custom widget
        if 'widget' not in kwargs:
            kwargs['widget'] = DrugTemplateSelectWidget(user=user)
        
        super().__init__(*args, **kwargs)
    
    def label_from_instance(self, obj):
        """Custom label format for template options."""
        return f"{obj.name} - {obj.presentation}"


class PrescriptionFormWidget(forms.Widget):
    """
    Custom widget for rendering prescription forms with enhanced functionality.
    """
    
    template_name = 'outpatientprescriptions/widgets/prescription_form_widget.html'
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'prescription-form-widget',
            'data-widget-type': 'prescription-form'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget."""
        context = self.get_context(name, value, attrs)
        return self._render(self.template_name, context, renderer)
    
    def get_context(self, name, value, attrs):
        """Get context for rendering."""
        context = super().get_context(name, value, attrs)
        
        # Add additional context for enhanced functionality
        context['widget'].update({
            'prescription_form': True,
            'supports_templates': True,
            'dynamic_forms': True
        })
        
        return context
    
    def _render(self, template_name, context, renderer=None):
        """Render template with context."""
        if renderer is None:
            renderer = self.renderer
        return mark_safe(renderer.render(template_name, context))


class AutoCompleteWidget(forms.TextInput):
    """
    Enhanced text input with autocomplete functionality for drug names.
    """
    
    def __init__(self, attrs=None, autocomplete_url=None):
        self.autocomplete_url = autocomplete_url
        default_attrs = {
            'class': 'form-control autocomplete-input',
            'data-autocomplete': 'true',
            'autocomplete': 'off'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with autocomplete functionality."""
        html = super().render(name, value, attrs, renderer)
        
        # Add autocomplete container
        autocomplete_html = format_html(
            '<div class="autocomplete-container" data-field="{}">'
            '{}'
            '<div class="autocomplete-suggestions" style="display: none;"></div>'
            '</div>',
            name,
            html
        )
        
        return mark_safe(autocomplete_html)
    
    def get_context(self, name, value, attrs):
        """Get context for rendering."""
        context = super().get_context(name, value, attrs)
        
        if self.autocomplete_url:
            context['widget']['attrs']['data-autocomplete-url'] = self.autocomplete_url
        
        return context


class PrescriptionItemWidget(forms.Widget):
    """
    Composite widget for prescription items with integrated template selection.
    """
    
    def __init__(self, user=None, attrs=None):
        self.user = user
        super().__init__(attrs)
        
        # Initialize sub-widgets
        self.drug_name_widget = AutoCompleteWidget(attrs={'placeholder': 'Nome do medicamento'})
        self.presentation_widget = forms.TextInput(attrs={'placeholder': 'Ex: 500mg comprimidos'})
        self.usage_instructions_widget = forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Ex: Tomar 1 comprimido de 8 em 8 horas'
        })
        self.quantity_widget = forms.TextInput(attrs={'placeholder': 'Ex: 21 comprimidos'})
        self.template_widget = DrugTemplateSelectWidget(user=user)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the composite widget."""
        if value is None:
            value = {}
        
        # Render each sub-widget
        template_html = self.template_widget.render(
            f'{name}_template', 
            value.get('template'), 
            attrs={'class': 'form-control drug-template-select'}
        )
        
        drug_name_html = self.drug_name_widget.render(
            f'{name}_drug_name',
            value.get('drug_name'),
            attrs={'class': 'form-control'}
        )
        
        presentation_html = self.presentation_widget.render(
            f'{name}_presentation',
            value.get('presentation'),
            attrs={'class': 'form-control'}
        )
        
        usage_instructions_html = self.usage_instructions_widget.render(
            f'{name}_usage_instructions',
            value.get('usage_instructions'),
            attrs={'class': 'form-control'}
        )
        
        quantity_html = self.quantity_widget.render(
            f'{name}_quantity',
            value.get('quantity'),
            attrs={'class': 'form-control'}
        )
        
        # Combine into complete widget
        widget_html = format_html(
            '<div class="prescription-item-widget" data-widget-name="{}">'
            '<div class="row">'
            '<div class="col-12 mb-3">'
            '<label>Template de Medicamento</label>'
            '{}'
            '</div>'
            '</div>'
            '<div class="row">'
            '<div class="col-md-6 mb-3">'
            '<label>Medicamento</label>'
            '{}'
            '</div>'
            '<div class="col-md-6 mb-3">'
            '<label>Apresentação</label>'
            '{}'
            '</div>'
            '</div>'
            '<div class="row">'
            '<div class="col-md-8 mb-3">'
            '<label>Instruções de Uso</label>'
            '{}'
            '</div>'
            '<div class="col-md-4 mb-3">'
            '<label>Quantidade</label>'
            '{}'
            '</div>'
            '</div>'
            '</div>',
            name,
            template_html,
            drug_name_html,
            presentation_html,
            usage_instructions_html,
            quantity_html
        )
        
        return mark_safe(widget_html)
    
    def value_from_datadict(self, data, files, name):
        """Extract value from form data."""
        return {
            'template': data.get(f'{name}_template'),
            'drug_name': data.get(f'{name}_drug_name'),
            'presentation': data.get(f'{name}_presentation'),
            'usage_instructions': data.get(f'{name}_usage_instructions'),
            'quantity': data.get(f'{name}_quantity')
        }
    
    def decompress(self, value):
        """Decompress value for sub-widgets."""
        if value:
            return [
                value.get('template'),
                value.get('drug_name'),
                value.get('presentation'),
                value.get('usage_instructions'),
                value.get('quantity')
            ]
        return [None, None, None, None, None]