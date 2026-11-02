"""Shared explicit-state parsing and ANY/ALL semantics for tag filters.

One parser serves the patient list and any future map caller. It keeps the
design D6 distinctions apart: no parameters means "initial entry", an explicit
manual selection (including an empty one) means "manual state", and the legacy
``tag=<id>`` form is an explicit ANY single-tag filter. Only tags visible to the
requesting actor may be selected; an unreadable, unknown or malformed identity
raises the generic :class:`InvalidTagFilter` instead of widening the search.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.patients.services import tag_projection

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.http import QueryDict

    from apps.accounts.models import EqmdCustomUser
    from apps.patients.models import AllowedTag, Patient

MATCH_ANY = "any"
MATCH_ALL = "all"
MATCH_MODES = (MATCH_ANY, MATCH_ALL)
DEFAULT_MODE = MATCH_ANY
MANUAL_MARKER = "manual"
TAG_FILTER_PARAM = "tag_filter"
TAG_MODE_PARAM = "tag_mode"
LEGACY_TAG_PARAM = "tag"
TAGS_PARAM = "tags"
TAG_QUERY_KEYS = (
    LEGACY_TAG_PARAM,
    TAGS_PARAM,
    TAG_MODE_PARAM,
    TAG_FILTER_PARAM,
    "page",
)
MODE_LABELS = {MATCH_ANY: "Qualquer tag", MATCH_ALL: "Todas as tags"}
STATE_INITIAL_LABEL = "Sem filtro de tag"
STATE_MANUAL_LABEL = "Filtro manual"
STATE_MANUAL_EMPTY_LABEL = "Sem tags (filtro manual)"


@dataclass(frozen=True)
class TagFilterSelection:
    """One resolved, requester-safe tag filter state."""

    tags: tuple[AllowedTag, ...] = ()
    mode: str = DEFAULT_MODE
    is_manual: bool = False

    @property
    def tag_ids(self) -> tuple[int, ...]:
        return tuple(tag.pk for tag in self.tags)

    @property
    def has_predicate(self) -> bool:
        """Return whether this state should narrow the patient queryset."""
        return bool(self.tags)

    @property
    def mode_label(self) -> str:
        return MODE_LABELS[self.mode]

    @property
    def state_label(self) -> str:
        if not self.is_manual:
            return STATE_INITIAL_LABEL
        return STATE_MANUAL_LABEL if self.tags else STATE_MANUAL_EMPTY_LABEL

    def without_tag_id(self, tag_id: int) -> TagFilterSelection:
        """Return the same manual state with one selected identity removed."""
        return replace(
            self,
            tags=tuple(tag for tag in self.tags if tag.pk != tag_id),
            is_manual=True,
        )


def parse_tag_ids(raw_values: Iterable[object]) -> tuple[int, ...]:
    """Normalise repeated identifier inputs, deduplicating in input order."""
    identifiers: list[int] = []
    for raw_value in raw_values:
        text = str(raw_value).strip()
        if not text:
            continue
        try:
            tag_id = int(text)
        except (TypeError, ValueError) as error:
            raise tag_projection.InvalidTagFilter(
                tag_projection.INVALID_TAG_FILTER_MESSAGE
            ) from error
        if tag_id not in identifiers:
            identifiers.append(tag_id)
    return tuple(identifiers)


def resolve_visible_tags(
    actor: EqmdCustomUser | None, tag_ids: Iterable[int]
) -> tuple[AllowedTag, ...]:
    """Resolve identities against the requester's visible catalogue.

    Every requested identity must be readable *and* present, otherwise the
    caller receives the one generic error: distinguishing unknown, archived
    and inaccessible rows would turn filtering into an existence oracle.
    """
    identifiers = tuple(tag_ids)
    if not identifiers:
        return ()
    rows = {
        tag.pk: tag
        for tag in tag_projection.visible_catalogue(actor).filter(pk__in=identifiers)
    }
    if len(rows) != len(identifiers):
        raise tag_projection.InvalidTagFilter(
            tag_projection.INVALID_TAG_FILTER_MESSAGE
        )
    return tuple(rows[tag_id] for tag_id in identifiers)


def _parse_mode(query: QueryDict) -> str:
    raw_mode = query.get(TAG_MODE_PARAM)
    if raw_mode in (None, ""):
        return DEFAULT_MODE
    if raw_mode not in MATCH_MODES:
        raise tag_projection.InvalidTagFilter(
            tag_projection.INVALID_TAG_FILTER_MESSAGE
        )
    return raw_mode


def _parse_marker(query: QueryDict) -> bool:
    raw_marker = query.get(TAG_FILTER_PARAM, "")
    if raw_marker in ("", MANUAL_MARKER):
        return raw_marker == MANUAL_MARKER
    raise tag_projection.InvalidTagFilter(
        tag_projection.INVALID_TAG_FILTER_MESSAGE
    )


def parse_tag_selection(
    actor: EqmdCustomUser | None, query: QueryDict
) -> TagFilterSelection:
    """Parse one GET query into a resolved explicit or initial filter state.

    ``tags`` repeated parameters take precedence over the legacy single ``tag``
    parameter when both are present. A present empty legacy ``tag=`` or an
    absent/empty ``tags`` with the manual marker means explicit manual-empty.
    """
    mode = _parse_mode(query)
    is_marked_manual = _parse_marker(query)

    if TAGS_PARAM in query:
        tag_ids = parse_tag_ids(query.getlist(TAGS_PARAM))
    elif LEGACY_TAG_PARAM in query:
        tag_ids = parse_tag_ids([query.get(LEGACY_TAG_PARAM, "")])
        mode = MATCH_ANY
    elif is_marked_manual:
        tag_ids = ()
    else:
        return TagFilterSelection(mode=mode)

    return TagFilterSelection(
        tags=resolve_visible_tags(actor, tag_ids),
        mode=mode,
        is_manual=True,
    )


def apply_tag_selection(
    queryset: QuerySet[Patient], selection: TagFilterSelection
) -> QuerySet[Patient]:
    """Apply DISTINCT ANY/ALL semantics alongside the existing predicates.

    ANY is a union of selected identities; ALL requires every identity through
    one join per tag. ``distinct()`` keeps each patient exactly once regardless
    of how many selected associations matched.
    """
    if not selection.has_predicate:
        return queryset
    if selection.mode == MATCH_ALL:
        for tag in selection.tags:
            queryset = queryset.filter(patient_tags__allowed_tag_id=tag.pk)
        return queryset.distinct()
    return queryset.filter(
        patient_tags__allowed_tag_id__in=[tag.pk for tag in selection.tags]
    ).distinct()


def _without_tag_parameters(query: QueryDict) -> QueryDict:
    params = query.copy()
    for key in TAG_QUERY_KEYS:
        params.pop(key, None)
    return params


def effective_query(
    query: QueryDict, selection: TagFilterSelection
) -> QueryDict:
    """Return the canonical query state for form, pagination and links.

    Explicit selections always round-trip as repeated ``tags`` parameters plus
    ``tag_mode`` and the manual marker. Initial entry keeps no tag parameters,
    and an explicit empty selection keeps only the marker/mode so it cannot
    decay into "initial entry" (and later back into a default).
    """
    params = _without_tag_parameters(query)
    if not selection.is_manual:
        return params
    params[TAG_FILTER_PARAM] = MANUAL_MARKER
    params[TAG_MODE_PARAM] = selection.mode
    if selection.tag_ids:
        params.setlist(TAGS_PARAM, [str(tag_id) for tag_id in selection.tag_ids])
    return params


def encoded_query(query: QueryDict, selection: TagFilterSelection) -> str:
    """URL-encode the canonical effective query without the pagination page."""
    return effective_query(query, selection).urlencode()


def remove_tag_query(
    query: QueryDict, selection: TagFilterSelection, tag_id: int
) -> str:
    """Return the effective query with one selected tag removed."""
    return encoded_query(query, selection.without_tag_id(tag_id))


def manual_empty_query(query: QueryDict, selection: TagFilterSelection) -> str:
    """Return the effective query for an explicitly cleared tag filter."""
    cleared = TagFilterSelection(mode=selection.mode, is_manual=True)
    return encoded_query(query, cleared)


def query_without(query: QueryDict, selection: TagFilterSelection, key: str) -> str:
    """Return the effective query with one non-tag parameter removed."""
    params = effective_query(query, selection)
    params.pop(key, None)
    return params.urlencode()
