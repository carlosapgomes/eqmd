"""Map-only context adapter; inherit eligibility, permissions and AJAX routing."""

from typing import cast

from django.urls import reverse

from apps.accounts.models import MedicalSpecialty
from apps.accounts.services.tag_preferences import TagPreferenceState
from apps.patients.services.tag_filters import TagFilterSelection
from apps.patients.services.ward_map_filter_actions import (
    MapResultState,
    action_context,
)
from apps.patients.views import WardPatientMapView


class WardMapFilterActionsView(WardPatientMapView):
    """Adapt already-resolved legacy context without resolving preferences twice."""

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context: dict[str, object] = super().get_context_data(**kwargs)
        preference = TagPreferenceState(
            selection=cast(TagFilterSelection, context["tag_selection"]),
            specialty=cast(
                MedicalSpecialty | None, context["tag_preference_specialty"]
            ),
            has_saved_preference=bool(context["tag_preference_has_saved"]),
            warning=cast(str, context["tag_preference_warning"]),
            error=cast(str, context["tag_filter_error"]),
        )
        state = MapResultState(
            preference=preference,
            search_query=cast(str, context["search_query"]),
            ward_filter=cast(str, context["ward_filter"]),
            show_empty_wards=bool(context["show_empty_wards"]),
            total_patients=cast(int, context["total_patients"]),
            total_wards=cast(int, context["total_wards"]),
            updating=bool(context.get("updating", False)),
        )
        context.update(
            action_context(
                self.request.GET, state, page_url=reverse("patients:patient_map")
            )
        )
        return context
