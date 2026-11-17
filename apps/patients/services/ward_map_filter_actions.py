"""Map-owned action URLs and presentation facts; no queries or mutations."""

from dataclasses import dataclass

from django.http import QueryDict

from apps.accounts.services.tag_preferences import TagPreferenceState
from apps.patients.services import tag_filters
from apps.patients.services.patient_list_filter_actions import preference_status


@dataclass(frozen=True)
class MapResultState:
    """Applied result facts already resolved by the inherited map view."""

    preference: TagPreferenceState
    search_query: str
    ward_filter: str
    show_empty_wards: bool
    total_patients: int
    total_wards: int
    updating: bool


def action_context(
    query: QueryDict, state: MapResultState, *, page_url: str
) -> dict[str, str | bool]:
    """Keep origin, effective filtering and within-ward narrowing distinct."""
    preference = state.preference
    patient_predicates = bool(
        state.search_query.strip() or preference.selection.has_predicate
    )
    effective_filters = patient_predicates or bool(state.ward_filter.strip())
    cleared = QueryDict("", mutable=True)
    cleared[tag_filters.TAG_FILTER_PARAM] = tag_filters.MANUAL_MARKER
    cleared[tag_filters.TAG_MODE_PARAM] = tag_filters.MATCH_ANY
    restored = tag_filters.effective_query(
        query, tag_filters.TagFilterSelection()
    ).urlencode()
    return {
        "map_clear_all_url": f"{page_url}?{cleared.urlencode()}",
        "map_restore_tags_url": f"{page_url}?{restored}" if restored else page_url,
        "map_show_restore": _has_restorable_default(preference),
        "map_preference_status": preference_status(preference),
        "map_has_patient_predicates": patient_predicates,
        "map_has_effective_filters": effective_filters,
        "map_show_zero_notice": (
            effective_filters
            and state.show_empty_wards
            and state.total_patients == 0
            and state.total_wards > 0
            and not preference.error
            and not state.updating
        ),
    }


def _has_restorable_default(preference: TagPreferenceState) -> bool:
    specialty = preference.specialty
    return (
        preference.selection.is_manual
        and specialty is not None
        and (preference.has_saved_preference or specialty.principal_tag_id is not None)
    )
