"""
Forms for reports app.
"""

from django import forms
from django.db import models
from django.utils import timezone

from .models import ReportTemplate, Report
from .services.report_service import can_user_use_template


class ReportUpdateForm(forms.ModelForm):
    """Form for updating an existing report."""

    class Meta:
        model = Report
        fields = ['title', 'document_date', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'content': forms.Textarea(
                attrs={
                    'id': 'id_content',
                    'class': 'form-control',
                    'rows': 15,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form."""
        super().__init__(*args, **kwargs)

        # Configure content field
        self.fields['content'].required = True
        self.fields['content'].label = "Conteúdo"
        self.fields['content'].help_text = "Conteúdo do relatório (suporte a Markdown)"


class ReportTemplateForm(forms.ModelForm):
    """Form for creating and updating report templates."""

    class Meta:
        model = ReportTemplate
        fields = ['name', 'markdown_body', 'is_active', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'markdown_body': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with user instance."""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        """Save template with creator/updater fields."""
        # Set created_by/updated_by before saving
        if not self.user:
            raise ValueError("User is required to save template")

        # Track if this is a new instance before calling super().save()
        is_new = self.instance._state.adding

        # Set fields directly on instance
        if is_new:
            self.instance.created_by = self.user
        self.instance.updated_by = self.user

        instance = super().save(commit=commit)

        return instance


class ReportCreateForm(forms.ModelForm):
    """Form for creating a new report from a template."""

    template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.none(),
        required=False,
        label="Template",
        help_text="Select a template to pre-fill the content (optional)",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Report
        fields = ['template', 'title', 'document_date', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'content': forms.Textarea(
                attrs={
                    'id': 'id_content',
                    'class': 'form-control',
                    'rows': 15,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with user and patient."""
        self.user = kwargs.pop('user', None)
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)

        # Set default document_date to today
        if not self.instance.pk:
            self.fields['document_date'].initial = timezone.now().date()

        # Configure content field
        self.fields['content'].required = True
        self.fields['content'].label = "Conteúdo"
        self.fields['content'].help_text = "Conteúdo do relatório (suporte a Markdown)"

        # Filter templates to show only public and user's own
        if self.user:
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                is_active=True
            ).filter(
                models.Q(is_public=True) | models.Q(created_by=self.user)
            )

    def clean_template(self):
        """Validate that selected template is accessible."""
        template = self.cleaned_data.get('template')
        if template and not can_user_use_template(self.user, template):
            raise forms.ValidationError(
                "You cannot use this template (private template from another user)"
            )
        return template

    def save(self, commit=True):
        """Save report with patient, creator, and other required fields."""
        instance = super().save(commit=False)

        # Set required fields
        instance.patient = self.patient
        instance.created_by = self.user
        instance.updated_by = self.user
        instance.description = f"Relatório - {instance.title}"

        if commit:
            instance.save()

        return instance
