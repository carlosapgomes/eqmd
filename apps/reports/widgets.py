"""Bounded rendering for the report-creation template selector (S3, D6).

The widget renders only the current discovery result page plus, when
present, the currently selected template. It is presentation-only: the
``ModelChoiceField`` validation queryset stays the complete active
public-or-own set, so a still-authorized choice outside the current
page still submits successfully. An unavailable choice keeps its
submitted identity for validation but is labelled generically, without
revealing any stored metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django import forms

if TYPE_CHECKING:
    from apps.reports.models import ReportTemplate

OUTSIDE_RESULTS_LABEL = " (fora dos resultados atuais)"
UNAVAILABLE_LABEL = "Modelo selecionado indisponível"


class BoundedTemplateSelect(forms.Select):
    """Single-choice select rendering a bounded page plus the selection."""

    def __init__(self, attrs: dict[str, Any] | None = None) -> None:
        super().__init__(attrs=attrs)
        self.bounded_templates: list[ReportTemplate] = []
        self.selected_template: ReportTemplate | None = None
        self.selected_template_id: str = ""
        self.selected_unavailable: bool = False
        self._bounded_configured: bool = False

    def set_bounded_choices(
        self,
        templates: list[ReportTemplate] | tuple[ReportTemplate, ...],
        *,
        selected_template: ReportTemplate | None = None,
        selected_template_id: str = "",
        selected_unavailable: bool = False,
    ) -> None:
        """Fix the rendered choices for one form rendering.

        ``templates`` is the current result page. A selected template
        outside that page is appended with an outside-results label; an
        unavailable identity is appended with a generic label only.
        """
        self.bounded_templates = list(templates)
        self.selected_template = selected_template
        if selected_template is not None:
            self.selected_template_id = str(selected_template.pk)
        else:
            self.selected_template_id = str(selected_template_id or "")
        self.selected_unavailable = bool(selected_unavailable)
        self._bounded_configured = True

    def _bounded_choices(self) -> list[tuple[str, str]]:
        choices: list[tuple[str, str]] = [("", "---------")]
        seen: set[str] = {""}
        for template in self.bounded_templates:
            value = str(template.pk)
            choices.append((value, template.name))
            seen.add(value)
        selected_id = self.selected_template_id
        if selected_id and selected_id not in seen:
            if self.selected_unavailable or self.selected_template is None:
                choices.append((selected_id, UNAVAILABLE_LABEL))
            else:
                choices.append(
                    (selected_id, self.selected_template.name + OUTSIDE_RESULTS_LABEL)
                )
        return choices

    def get_context(
        self, name: str, value: Any, attrs: Any = None
    ) -> dict[str, Any]:  # Any: Django widget rendering contract.
        if self._bounded_configured:
            self.choices = self._bounded_choices()
            if not value and self.selected_template_id:
                # An unavailable choice has no form initial (the prefill
                # flow refuses it), but its identity is still the
                # current selection and must render as selected.
                value = self.selected_template_id
        return super().get_context(name, value, attrs)
