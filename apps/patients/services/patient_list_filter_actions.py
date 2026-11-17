"""List-owned action URLs and truthful applied preference presentation."""

from django.http import QueryDict

from apps.accounts.services.tag_preferences import TagPreferenceState
from apps.patients.services import tag_filters


def preference_status(preference: TagPreferenceState) -> str:
    """Describe applied results, never a pending draft or merely stored setting."""
    selection = preference.selection
    if preference.error:
        return "Não foi possível aplicar os filtros."
    if selection.is_manual:
        return (
            "Filtros personalizados em uso."
            if selection.has_predicate
            else "Filtros personalizados sem filtro de tags em uso."
        )
    if preference.warning:
        if not selection.has_predicate:
            return "Sem filtro de tags: padrão indisponível."
        return f"{selection.state_label} aplicado parcialmente (tags disponíveis)."
    if selection.source == tag_filters.SOURCE_SAVED:
        return (
            "Padrão salvo da especialidade aplicado."
            if selection.has_predicate
            else "Padrão salvo sem filtro de tags aplicado."
        )
    if selection.source == tag_filters.SOURCE_PRINCIPAL:
        return "Padrão inicial da especialidade aplicado."
    return "Sem padrão de tags aplicado."


def action_context(
    query: QueryDict,
    preference: TagPreferenceState,
    *,
    page_url: str,
) -> dict[str, str | bool]:
    """Build immediate links from applied request state, not draft form fields."""
    cleared = QueryDict("", mutable=True)
    cleared[tag_filters.TAG_FILTER_PARAM] = tag_filters.MANUAL_MARKER
    cleared[tag_filters.TAG_MODE_PARAM] = tag_filters.MATCH_ANY
    restored = tag_filters.effective_query(
        query, tag_filters.TagFilterSelection()
    ).urlencode()
    specialty = preference.specialty
    return {
        "patient_list_clear_all_url": f"{page_url}?{cleared.urlencode()}",
        "patient_list_restore_tags_url": f"{page_url}?{restored}"
        if restored
        else page_url,
        "patient_list_show_restore": (
            preference.selection.is_manual
            and specialty is not None
            and (
                preference.has_saved_preference
                or specialty.principal_tag_id is not None
            )
        ),
        "patient_list_preference_status": preference_status(preference),
    }
