"""Paginated, visibility-checked catalogue lookup for the tag selector.

This is a read-only search backend. It never creates or mutates catalogue rows,
runs every query through the requester-aware projection and only exposes
inactive/archived entries when historical inclusion is explicitly requested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When

from apps.patients.services import tag_projection

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser
    from apps.patients.services.tag_projection import TagBadge

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


@dataclass(frozen=True)
class TagLookupPage:
    """One bounded page of requester-visible catalogue entries."""

    badges: tuple[TagBadge, ...]
    count: int
    page: int
    num_pages: int
    page_size: int
    has_next: bool
    has_previous: bool


def _state_rank() -> Case:
    """Order active rows before inactive and archived historical rows."""
    return Case(
        When(is_active=True, then=Value(0)),
        When(is_deleted=False, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )


def search_visible_tags(
    actor: EqmdCustomUser | None,
    *,
    query: str = "",
    include_historical: bool = False,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> TagLookupPage:
    """Return one searchable page from the requester's visible catalogue."""
    catalogue = tag_projection.visible_catalogue(actor)
    if not include_historical:
        catalogue = catalogue.filter(is_active=True)
    if query:
        catalogue = catalogue.filter(
            Q(name__unaccent__icontains=query)
            | Q(specialty__abbreviation__icontains=query)
        )
    catalogue = catalogue.annotate(lookup_state_rank=_state_rank()).order_by(
        "lookup_state_rank", "name"
    )

    paginator = Paginator(catalogue, page_size)
    current = paginator.get_page(page)
    return TagLookupPage(
        badges=tuple(tag_projection.tag_badge(tag) for tag in current.object_list),
        count=paginator.count,
        page=current.number,
        num_pages=paginator.num_pages,
        page_size=page_size,
        has_next=current.has_next(),
        has_previous=current.has_previous(),
    )
