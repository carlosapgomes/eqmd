from django import forms
from django.utils import timezone

from .models import DailyNote
from apps.core.permissions import can_access_patient
from apps.events.models import Event


class DailyNoteForm(forms.ModelForm):
    """
    Form for creating and updating DailyNote instances.
    Uses EasyMDE editor for content.
    """

    class Meta:
        model = DailyNote
        fields = ["event_datetime", "content"]
        widgets = {
            "event_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "content": forms.Textarea(
                attrs={
                    "id": "id_content",
                    "name": "content",
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": "Conteúdo da evolução...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields["event_datetime"].input_formats = [
            "%Y-%m-%dT%H:%M",  # HTML5 datetime-local format
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y %H:%M:%S",  # Format in your error message
            "%d/%m/%Y %H:%M",
        ]

        # Set default datetime to now if creating new instance
        if not self.instance.pk:
            utc_now = timezone.now().astimezone(timezone.get_default_timezone())
            self.fields["event_datetime"].initial = utc_now.strftime("%Y-%m-%dT%H:%M")
        else:
            dt = self.instance.event_datetime.astimezone(
                timezone.get_default_timezone()
            )
            self.fields["event_datetime"].initial = dt.strftime("%Y-%m-%dT%H:%M")

        print(self.fields["event_datetime"].initial)

        # Configure field properties
        self.fields[
            "content"
        ].help_text = "Conteúdo detalhado da evolução (suporte a Markdown)"

    def clean_event_datetime(self):
        """Validate that event_datetime is not in the future."""
        event_datetime = self.cleaned_data.get("event_datetime")
        if event_datetime and event_datetime > timezone.now():
            raise forms.ValidationError(
                "A data e hora do evento não pode ser no futuro."
            )
        return event_datetime

    def clean_content(self):
        """Validate content field."""
        content = self.cleaned_data.get("content")
        if content and len(content.strip()) < 10:
            raise forms.ValidationError("O conteúdo deve ter pelo menos 10 caracteres.")
        return content

    def save(self, commit=True):
        """Override save to set created_by and updated_by fields."""
        instance = super().save(commit=False)

        instance.description = Event.EVENT_TYPE_CHOICES[Event.DAILY_NOTE_EVENT][1]
        if self.user:
            if not instance.pk:  # New instance
                instance.created_by = self.user
            instance.updated_by = self.user

        if commit:
            instance.save()
        return instance
