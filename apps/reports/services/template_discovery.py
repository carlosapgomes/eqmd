"""Report-template catalogue discovery queries (S2, design D4).

One typed query contract serves the catalogue now and the report-creation
selector later (S3): the same resolved tag state and name predicate apply to
either explicit base queryset. Tag matching uses the reports relation path
(``tags``), never patient joins. Explicit invalid filters are reported as an
error state *before* any result query runs, so a malformed filter can never
decay into successful unfiltered discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.accounts.services import tag_preferences
from apps.patients.models import AllowedTag
from apps.patients.services import tag_filters, tag_projection

if TYPE_CHECKING:
    from django.http import QueryDict

    from apps.accounts.models import EqmdCustomUser, MedicalSpecialty
    from apps.reports.models import ReportTemplate

MAX_NAME_QUERY_LENGTH = 255
NAME_QUERY_PARAM = "q"
NAME_QUERY_TOO_LONG_MESSAGE = "A busca deve ter no máximo 255 caracteres."
FRAGMENT_PARAM = "fragment"
FRAGMENT_RESULTS = "results"
INCLUDE_HISTORICAL_PARAM = "include_historical"
PAGE_SIZE = 20


class InvalidNameQuery(ValidationError):
    """The trimmed name query exceeds the accepted length."""


@dataclass(frozen=True)
class DiscoveryState:
    """Resolved catalogue filter state for one request."""

    selection: tag_filters.TagFilterSelection
    name_query: str = ""
    warning: str = ""
    error: str = ""
    specialty: MedicalSpecialty | None = None
    has_saved_preference: bool = False

    @property
    def is_manual(self) -> bool:
        return self.selection.is_manual


@dataclass(frozen=True)
class DiscoveryTagOption:
    """One readable catalogue choice for the native tag select."""

    tag_id: int
    display_name: str
    state_label: str
    is_selected: bool
    is_historical: bool


def parse_name_query(query: QueryDict) -> str:
    """Return the trimmed name query, rejecting oversized input."""
    trimmed = (query.get(NAME_QUERY_PARAM) or "").strip()
    if len(trimmed) > MAX_NAME_QUERY_LENGTH:
        raise InvalidNameQuery(NAME_QUERY_TOO_LONG_MESSAGE)
    return trimmed


def parse_include_historical(query: QueryDict) -> bool:
    """Return whether historical choices were explicitly requested."""
    return query.get(INCLUDE_HISTORICAL_PARAM) == "1"


def is_fragment_request(query: QueryDict) -> bool:
    """Return whether the results partial was requested."""
    return query.get(FRAGMENT_PARAM) == FRAGMENT_RESULTS


def resolve_discovery_state(
    actor: EqmdCustomUser | None, query: QueryDict
) -> DiscoveryState:
    """Resolve defaults, explicit state and the name query for one request."""
    preference = tag_preferences.resolve_request_state(actor, query)
    if preference.error:
        return DiscoveryState(
            selection=preference.selection,
            warning=preference.warning,
            error=preference.error,
            specialty=preference.specialty,
            has_saved_preference=preference.has_saved_preference,
        )
    try:
        name_query = parse_name_query(query)
    except InvalidNameQuery as error:
        return DiscoveryState(
            selection=preference.selection,
            warning=preference.warning,
            error=str(error.messages[0])
            if error.messages
            else NAME_QUERY_TOO_LONG_MESSAGE,
            specialty=preference.specialty,
            has_saved_preference=preference.has_saved_preference,
        )
    return DiscoveryState(
        selection=preference.selection,
        name_query=name_query,
        warning=preference.warning,
        specialty=preference.specialty,
        has_saved_preference=preference.has_saved_preference,
    )


def catalogue_base_queryset(
    actor: EqmdCustomUser | None,
) -> QuerySet[ReportTemplate]:
    """Public-or-own templates, including inactive ones for management."""
    from apps.reports.models import ReportTemplate

    queryset = ReportTemplate.objects.select_related("created_by", "updated_by")
    return queryset.filter(Q(is_public=True) | Q(created_by=actor))


def selectable_base_queryset(
    actor: EqmdCustomUser | None,
) -> QuerySet[ReportTemplate]:
    """Catalogue base restricted to active templates (S3 selector scope)."""
    return catalogue_base_queryset(actor).filter(is_active=True)


def apply_discovery_filters(
    queryset: QuerySet[ReportTemplate],
    selection: tag_filters.TagFilterSelection,
    name_query: str,
) -> QuerySet[ReportTemplate]:
    """Apply distinct ANY/ALL tag matching and name search in stable order."""
    if selection.has_predicate:
        if selection.mode == tag_filters.MATCH_ALL:
            for tag in selection.tags:
                queryset = queryset.filter(tags__pk=tag.pk)
        else:
            queryset = queryset.filter(tags__pk__in=[tag.pk for tag in selection.tags])
        queryset = queryset.distinct()
    if name_query:
        queryset = queryset.filter(name__unaccent__icontains=name_query)
    return queryset.order_by("name", "pk")


def discovery_tag_options(
    actor: EqmdCustomUser | None,
    *,
    selected_ids: tuple[int, ...] | list[int] = (),
    include_historical: bool = False,
) -> tuple[DiscoveryTagOption, ...]:
    """Return readable choices: active tags, plus historical ones on request.

    A readable historical identity stays offered while it is selected, even
    when the historical toggle is off. Unreadable rows never appear.
    """
    selected = set(selected_ids)
    rows = list(tag_projection.visible_catalogue(actor).order_by("name", "pk"))
    options: list[DiscoveryTagOption] = []
    for tag in rows:
        is_historical = tag.lifecycle_state != AllowedTag.LifecycleState.ACTIVE
        if is_historical and not include_historical and tag.pk not in selected:
            continue
        badge = tag_projection.tag_badge(tag)
        options.append(
            DiscoveryTagOption(
                tag_id=badge.tag_id,
                display_name=badge.display_name,
                state_label=badge.state_label,
                is_selected=tag.pk in selected,
                is_historical=is_historical,
            )
        )
    return tuple(options)
