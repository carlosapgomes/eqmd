"""Transport validation for the reports-owned tag lookup.

Mirrors ``apps.patients.forms_tag_filters.TagLookupForm`` on purpose: only
lookup-shaping inputs live here. Tag identity resolution stays in the shared
``tag_filters`` service so malformed or inaccessible identifiers yield one
generic error instead of a field-specific existence oracle.
"""

from __future__ import annotations

from django import forms

from apps.patients.services.tag_lookup import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class ReportTagLookupForm(forms.Form):
    """Validate search, historical inclusion and pagination inputs."""

    q = forms.CharField(required=False, max_length=100)
    include_historical = forms.ChoiceField(
        choices=(("", ""), ("1", "1")), required=False
    )
    page = forms.IntegerField(required=False, min_value=1)
    page_size = forms.IntegerField(required=False, min_value=1, max_value=MAX_PAGE_SIZE)

    def include_historical_requested(self) -> bool:
        return self.cleaned_data.get("include_historical") == "1"

    def page_size_or_default(self) -> int:
        return self.cleaned_data.get("page_size") or DEFAULT_PAGE_SIZE

    def page_or_default(self) -> int:
        return self.cleaned_data.get("page") or 1

    def cleaned_search(self) -> str:
        return (self.cleaned_data.get("q") or "").strip()
