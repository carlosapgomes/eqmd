"""Catalogue-owned action URLs derived only from resolved applied state."""

from django.http import QueryDict

from apps.reports.services.template_discovery import (
    DiscoveryState,
    parse_include_historical,
)


def action_context(
    query: QueryDict, state: DiscoveryState, *, page_url: str
) -> dict[str, str | bool]:
    """Keep clear-all fresh and specialty restore restricted to applied options."""
    cleared = QueryDict("", mutable=True)
    cleared["tag_filter"] = "manual"
    cleared["tag_mode"] = "any"
    restored = QueryDict("", mutable=True)
    if state.name_query:
        restored["q"] = state.name_query
    if parse_include_historical(query):
        restored["include_historical"] = "1"
    specialty = state.specialty
    restore_query = restored.urlencode()
    return {
        "catalogue_filter_actions": True,
        "catalogue_clear_all_url": f"{page_url}?{cleared.urlencode()}",
        "catalogue_restore_tags_url": (
            f"{page_url}?{restore_query}" if restore_query else page_url
        ),
        "catalogue_show_restore": (
            state.is_manual
            and specialty is not None
            and (state.has_saved_preference or specialty.principal_tag_id is not None)
        ),
    }
