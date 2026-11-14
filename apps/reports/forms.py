"""
Forms for reports app.
"""

from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .models import ReportTemplate, Report
from .services.report_service import can_user_use_template
from .services.template_tag_projection import editor_tag_choices
from .services.template_tags import GENERIC_TAG_ERROR_MESSAGE


class _TagIdsField(forms.MultipleChoiceField):
    """Choice field whose membership check is deferred to ``clean_tag_ids``.

    The stock ``MultipleChoiceField`` validation echoes the submitted
    value in its error message, which would leak forged identities and
    distinguish them from unknown ones. Membership is therefore checked
    in ``ReportTemplateForm.clean_tag_ids`` with one generic message.
    """

    def valid_value(
        self, value: Any
    ) -> bool:  # Any: Django passes arbitrary submitted values; all accepted here.
        return True


class ReportUpdateForm(forms.ModelForm):
    """Form for updating an existing report."""

    class Meta:
        model = Report
        fields = ['title', 'document_date', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'text',
                    'placeholder': 'MM-DD-YYYY',
                },
                format='%m-%d-%Y',
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

        self.fields['document_date'].input_formats = ['%m-%d-%Y']

        # Configure content field
        self.fields['content'].required = True
        self.fields['content'].label = "Conteúdo"
        self.fields['content'].help_text = "Conteúdo do relatório (suporte a Markdown)"


class ReportTemplateForm(forms.ModelForm):
    """Form for creating and updating report templates.

    ``tag_ids`` is a bounded, non-model field: its choices are the
    actor's current editor choices (active assignable tags plus
    editable historical selections). It never maps onto the model M2M,
    so the relation cannot be replaced through an unrestricted
    ``ModelForm`` save; persistence goes through the atomic
    association service in the view.
    """

    tag_ids = _TagIdsField(
        required=False,
        label="Tags",
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    class Meta:
        model = ReportTemplate
        fields = ['name', 'markdown_body', 'is_active', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'markdown_body': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(
        self, *args: Any, **kwargs: Any
    ) -> None:  # Any: Django form kwargs forwarded to ModelForm.
        """Initialize form with user instance and bounded tag choices."""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        template = self.instance if self.instance.pk else None
        choices = editor_tag_choices(actor=self.user, template=template)
        tag_ids_field = cast(_TagIdsField, self.fields['tag_ids'])
        tag_ids_field.choices = [
            (
                str(choice.tag_id),
                choice.display_name
                + (f" ({choice.state_label})" if choice.state_label else ""),
            )
            for choice in choices
        ]
        tag_ids_field.initial = [
            str(choice.tag_id) for choice in choices if choice.is_selected
        ]

    def clean_tag_ids(self) -> frozenset[int]:
        """Accept only currently offered identities, with a generic error."""
        raw_values = self.cleaned_data.get('tag_ids') or []
        parsed: set[int] = set()
        for value in raw_values:
            try:
                parsed.add(int(value))
            except (TypeError, ValueError):
                raise ValidationError(GENERIC_TAG_ERROR_MESSAGE) from None
        tag_ids_field = cast(_TagIdsField, self.fields['tag_ids'])
        offered = cast(list[tuple[Any, Any]], tag_ids_field.choices)
        allowed = {int(value) for value, _label in offered}
        if not parsed <= allowed:
            raise ValidationError(GENERIC_TAG_ERROR_MESSAGE)
        return frozenset(parsed)

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
                attrs={
                    'class': 'form-control',
                    'type': 'text',
                    'placeholder': 'MM-DD-YYYY',
                },
                format='%m-%d-%Y',
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

        self.fields['document_date'].input_formats = ['%m-%d-%Y']

        # Set default document_date to today
        if not self.instance.pk and not self.initial.get('document_date'):
            self.fields['document_date'].initial = timezone.localdate().strftime(
                '%m-%d-%Y'
            )

        # Configure content field
        self.fields['content'].required = True
        self.fields['content'].label = "Conteúdo"
        self.fields['content'].help_text = "Conteúdo do relatório (suporte a Markdown)"

        # Filter templates to show only public and user's own
        # (the field is absent in subclasses, e.g. ReportDuplicateForm)
        if self.user and 'template' in self.fields:
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

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        template = cleaned_data.get('template')
        title = (cleaned_data.get('title') or '').strip()
        if template and not title:
            cleaned_data['title'] = template.name

        return cleaned_data

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


class ReportDuplicateForm(ReportCreateForm):
    """Duplication form: a new report pre-filled from an existing one.

    Template selection is deliberately absent. A duplicate repeats the
    source's already-rendered content, so exposing the template selector
    would let a template re-render replace that content.
    """

    class Meta(ReportCreateForm.Meta):
        fields = ['title', 'document_date', 'content']

    def __init__(self, *args, **kwargs):
        """Remove the template field inherited as a declared field."""
        super().__init__(*args, **kwargs)
        # `template` is declared on ReportCreateForm, so Django keeps it in
        # self.fields regardless of Meta.fields.
        del self.fields['template']
