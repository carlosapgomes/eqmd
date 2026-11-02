"""Transport validation for the explicit specialty preference mutation."""

from __future__ import annotations

from typing import Any

from django import forms

from apps.accounts.services import tag_preferences
from apps.patients.services import tag_filters


class TagIdentifierListField(forms.Field):
    """Parse repeated integer catalogue identities from one POST body."""

    widget = forms.MultipleHiddenInput

    def to_python(self, value: Any) -> list[int]:
        if value in self.empty_values:
            return []
        values = value if isinstance(value, (list, tuple)) else [value]
        identifiers: list[int] = []
        for item in values:
            try:
                identifier = int(str(item).strip())
            except (TypeError, ValueError) as error:
                raise forms.ValidationError(
                    tag_preferences.SAVE_REJECTED_MESSAGE
                ) from error
            if identifier not in identifiers:
                identifiers.append(identifier)
        return identifiers


class TagPreferenceSaveForm(forms.Form):
    """Validate the specialty target, matching mode and selected identities."""

    specialty_id = forms.UUIDField()
    tag_mode = forms.ChoiceField(
        choices=tag_filters.MODE_CHOICES,
        required=False,
        initial=tag_filters.DEFAULT_MODE,
    )
    tags = TagIdentifierListField(required=False)

    def selected_mode(self) -> str:
        """Return ANY when the submitted mode is absent."""
        return self.cleaned_data.get("tag_mode") or tag_filters.DEFAULT_MODE
