"""Leader-facing forms for the team tag page.

Only the descriptive fields are form input: origin, visibility, namespace,
responsibility and lifecycle state are derived by the catalogue service, so a
forged POST value has nothing to bind to.
"""

from __future__ import annotations

import re
from typing import Any

from django import forms

from apps.accounts.models import MedicalSpecialty
from apps.patients.services import tag_catalogue

HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")
NAME_REQUIRED_MESSAGE = "Informe o nome da tag."
NAME_RESERVED_MESSAGE = (
    "Este nome já está reservado nesta equipe, inclusive para tags inativas "
    "ou arquivadas."
)


class TeamTagForm(forms.Form):
    """Edit the leader-editable fields of a custom restricted team tag."""

    name = forms.CharField(
        max_length=100,
        label="Nome",
        error_messages={"required": NAME_REQUIRED_MESSAGE},
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        required=False,
        label="Descrição",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    color = forms.CharField(
        max_length=7,
        label="Cor",
        initial=tag_catalogue.DEFAULT_TAG_COLOR,
        widget=forms.TextInput(
            attrs={"type": "color", "class": "form-control form-control-color"}
        ),
    )

    def __init__(
        self,
        *args: Any,
        specialty: MedicalSpecialty,
        exclude_pk: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.specialty = specialty
        self.exclude_pk = exclude_pk
        super().__init__(*args, **kwargs)

    def clean_name(self) -> str:
        """Trim the name and enforce the namespace reservation in any state."""
        name = str(self.cleaned_data["name"]).strip()
        if tag_catalogue.name_is_reserved(
            name, specialty_id=self.specialty.pk, exclude_pk=self.exclude_pk
        ):
            raise forms.ValidationError(NAME_RESERVED_MESSAGE)
        return name

    def clean_color(self) -> str:
        """Require a hex colour so the badge stays renderable."""
        color = str(self.cleaned_data["color"]).strip()
        if not HEX_COLOR_PATTERN.fullmatch(color):
            raise forms.ValidationError(
                "Informe uma cor hexadecimal no formato #RRGGBB."
            )
        return color
