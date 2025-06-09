from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, Submit, Row, Column, HTML
from crispy_forms.bootstrap import FormActions

from .models import DailyNote
from apps.patients.models import Patient


class DailyNoteForm(forms.ModelForm):
    """
    Form for creating and updating DailyNote instances.
    Uses crispy forms for responsive design and EasyMDE editor for content.
    """
    
    class Meta:
        model = DailyNote
        fields = ['patient', 'event_datetime', 'description', 'content']
        widgets = {
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'content': forms.Textarea(
                attrs={
                    'id': 'id_content',
                    'class': 'form-control',
                    'rows': 10,
                    'placeholder': 'Conteúdo da evolução...'
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default datetime to now if creating new instance
        if not self.instance.pk:
            self.fields['event_datetime'].initial = timezone.now()
            
        # Configure field properties
        self.fields['patient'].queryset = Patient.objects.all()
        self.fields['patient'].empty_label = "Selecione um paciente"
        self.fields['description'].help_text = "Breve descrição da evolução"
        self.fields['content'].help_text = "Conteúdo detalhado da evolução (suporte a Markdown)"
        
        # Configure crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {'novalidate': ''}
        
        self.helper.layout = Layout(
            Fieldset(
                'Informações da Evolução',
                Row(
                    Column('patient', css_class='col-md-6'),
                    Column('event_datetime', css_class='col-md-6'),
                ),
                Field('description', css_class='form-control'),
            ),
            Fieldset(
                'Conteúdo',
                Field('content', css_class='form-control'),
                HTML("""
                    <small class="form-text text-muted">
                        Use Markdown para formatação. O editor oferece uma prévia em tempo real.
                    </small>
                """),
            ),
            FormActions(
                Submit('submit', 'Salvar Evolução', css_class='btn btn-primary'),
                HTML('<a href="{% url "dailynotes:dailynote_list" %}" class="btn btn-secondary ms-2">Cancelar</a>'),
            ),
        )
        
    def clean_event_datetime(self):
        """Validate that event_datetime is not in the future."""
        event_datetime = self.cleaned_data.get('event_datetime')
        if event_datetime and event_datetime > timezone.now():
            raise forms.ValidationError(
                "A data e hora do evento não pode ser no futuro."
            )
        return event_datetime
        
    def clean_content(self):
        """Validate content field."""
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 10:
            raise forms.ValidationError(
                "O conteúdo deve ter pelo menos 10 caracteres."
            )
        return content
        
    def save(self, commit=True):
        """Override save to set created_by and updated_by fields."""
        instance = super().save(commit=False)
        
        if self.user:
            if not instance.pk:  # New instance
                instance.created_by = self.user
            instance.updated_by = self.user
            
        if commit:
            instance.save()
        return instance
