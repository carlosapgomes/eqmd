"""
Forms for reports app.
"""

from django import forms

from .models import ReportTemplate


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
