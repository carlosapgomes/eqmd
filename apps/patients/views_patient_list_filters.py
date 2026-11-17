"""Narrow patient-list adapter; query, login and permission gates stay inherited."""

from django.urls import reverse

from apps.accounts.services.tag_preferences import TagPreferenceState
from apps.patients.services.patient_list_filter_actions import action_context
from apps.patients.views import PatientListView


class PatientListFilterActionsView(PatientListView):
    """Add only list-owned action presentation after normal list resolution."""

    tag_preference: TagPreferenceState

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context: dict[str, object] = super().get_context_data(**kwargs)
        context.update(
            action_context(
                self.request.GET,
                self.tag_preference,
                page_url=reverse("patients:patient_list"),
            )
        )
        return context
