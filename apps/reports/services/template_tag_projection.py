"""Requester-safe tag projections for report templates (S1, design D3).

Every read resolves persisted associations through the association table and
``AllowedTag.all_objects`` so archived links are not lost through the
soft-delete default manager, then applies the current
``tag_projection.Visibility`` snapshot. Restricted metadata that the actor
may not read is omitted entirely: no names, ids, counts or labels leak.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.patients.models import AllowedTag
from apps.patients.services import tag_policy, tag_projection

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser
    from apps.reports.models import ReportTemplate


@dataclass(frozen=True)
class TemplateTagBadge:
    """One requester-visible template association with lifecycle context."""

    tag_id: int
    name: str
    display_name: str
    color: str
    state: str
    state_label: str
    team_abbreviation: str
    is_restricted: bool
    can_remove: bool


@dataclass(frozen=True)
class EditorTagChoice:
    """One tag offered to the template editor with lifecycle context."""

    tag_id: int
    display_name: str
    state_label: str
    is_selected: bool
    is_historical: bool


def _existing_tag_ids(template_id: uuid.UUID) -> list[int]:
    """Return persisted tag identities through the association table."""
    from apps.reports.models import ReportTemplate

    through = ReportTemplate.tags.through
    return list(
        through.objects.filter(reporttemplate_id=template_id).values_list(
            "allowedtag_id", flat=True
        )
    )


def _fetch_tags(tag_ids: Iterable[int]) -> dict[int, AllowedTag]:
    """Fetch catalogue rows (any lifecycle state) keyed by identity."""
    ids = list(tag_ids)
    if not ids:
        return {}
    queryset: QuerySet[AllowedTag] = (
        AllowedTag.all_objects.select_related("specialty")
        .filter(pk__in=ids)
        .order_by("name")
    )
    return {tag.pk: tag for tag in queryset}


def _badge(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    visibility: tag_projection.Visibility,
) -> TemplateTagBadge:
    badge = tag_projection.tag_badge(tag)
    return TemplateTagBadge(
        tag_id=badge.tag_id,
        name=badge.name,
        display_name=badge.display_name,
        color=badge.color,
        state=badge.state,
        state_label=badge.state_label,
        team_abbreviation=badge.team_abbreviation,
        is_restricted=badge.is_restricted,
        can_remove=visibility.can_remove(actor, tag),
    )


def template_tag_badges(
    *, actor: EqmdCustomUser | None, templates: Iterable[ReportTemplate]
) -> dict[uuid.UUID, list[TemplateTagBadge]]:
    """Return visible badges per template for a bounded set of templates."""
    rows = list(templates)
    if not rows:
        return {}
    visibility = tag_projection.Visibility.for_actor(actor)
    existing: dict[uuid.UUID, list[int]] = {}
    all_ids: set[int] = set()
    for template in rows:
        ids = _existing_tag_ids(template.pk)
        existing[template.pk] = ids
        all_ids.update(ids)
    tags_by_id = _fetch_tags(all_ids)
    badges: dict[uuid.UUID, list[TemplateTagBadge]] = {}
    for template in rows:
        visible = [
            _badge(actor, tags_by_id[tag_id], visibility=visibility)
            for tag_id in existing[template.pk]
            if tag_id in tags_by_id and visibility.can_read(tags_by_id[tag_id])
        ]
        visible.sort(key=lambda badge: badge.display_name)
        badges[template.pk] = visible
    return badges


def template_tag_badges_for(
    *, actor: EqmdCustomUser | None, template: ReportTemplate
) -> list[TemplateTagBadge]:
    """Return the visible badges for a single template."""
    return template_tag_badges(actor=actor, templates=[template]).get(template.pk, [])


def editor_tag_choices(
    *, actor: EqmdCustomUser | None, template: ReportTemplate | None = None
) -> list[EditorTagChoice]:
    """Offer active assignable tags plus editable historical selections.

    New choices are active tags the actor may assign now. Existing
    inactive/archived links the actor may remove (and read) are offered
    labelled with their lifecycle state so they can be retained or
    removed; hidden or non-removable links stay outside the controls.
    """
    visibility = tag_projection.Visibility.for_actor(actor)
    selected_ids: set[int] = set()
    if template is not None and template.pk is not None:
        selected_ids = set(_existing_tag_ids(template.pk))

    active_tags = (
        AllowedTag.all_objects.select_related("specialty")
        .filter(is_active=True, is_deleted=False)
        .order_by("name")
    )
    choices: list[EditorTagChoice] = []
    offered: set[int] = set()
    for tag in active_tags:
        if not tag_policy.can_assign_tag(actor, tag):
            continue
        badge = tag_projection.tag_badge(tag)
        choices.append(
            EditorTagChoice(
                tag_id=tag.pk,
                display_name=badge.display_name,
                state_label=badge.state_label,
                is_selected=tag.pk in selected_ids,
                is_historical=False,
            )
        )
        offered.add(tag.pk)

    if selected_ids:
        historical = _fetch_tags(selected_ids)
        extra = [
            tag
            for tag_id, tag in sorted(historical.items(), key=lambda item: item[1].name)
            if tag_id not in offered
            and tag.lifecycle_state != AllowedTag.LifecycleState.ACTIVE
            and visibility.can_read(tag)
            and tag_policy.can_remove_tag(actor, tag, read_team_ids=visibility.team_ids)
        ]
        for tag in extra:
            badge = tag_projection.tag_badge(tag)
            choices.append(
                EditorTagChoice(
                    tag_id=tag.pk,
                    display_name=badge.display_name,
                    state_label=badge.state_label,
                    is_selected=True,
                    is_historical=True,
                )
            )
    return choices
