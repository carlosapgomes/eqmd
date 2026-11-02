"""Requester-aware presentation of patient tag audit events.

Users read historical tag actions through this module, never through the
stored snapshot/description fields. Visibility is decided from the current
catalogue row and the viewer's current team memberships, so a
public-to-restricted reclassification or a membership revocation applies to the
very next response.

A legacy event whose snapshot resolves but whose current catalogue row is gone
has no current visibility to read, so its stored snapshot only reaches
administrators.

Split plan: if this module grows further, the batched attach/payload helpers
(``attach_tag_audit_presentations``, ``tag_audit_payload``) move to a separate
reader module, leaving the per-event projection here.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from apps.events.models import Event, TagEventReference
from apps.patients.models import AllowedTag

from .tag_audit import (
    UNRESOLVED_TAG_AUDIT_SUMMARY,
    LegacyEventResolver,
    legacy_event_names,
)

ACTION_LABELS = {
    TagEventReference.Action.ADDED: "adicionada",
    TagEventReference.Action.REMOVED: "removida",
}


@dataclass(frozen=True)
class TagActionPresentation:
    """One tag action as the current viewer may read it."""

    action: str
    action_label: str
    visible: bool
    name: str = ""
    color: str = ""
    state_label: str = ""
    team_abbreviation: str = ""


@dataclass(frozen=True)
class TagAuditPresentation:
    """The whole tag audit event as the current viewer may read it."""

    summary: str
    actions: tuple[TagActionPresentation, ...]
    is_bulk: bool
    unresolved: bool


def _team_abbreviation(tag: AllowedTag) -> str:
    """Return the tag's current team abbreviation, empty for global tags."""
    if tag.specialty_id is None or tag.specialty is None:
        return ""
    return str(tag.specialty.abbreviation)


def _action_label(action: str) -> str:
    """Return the Portuguese label for one recorded action."""
    return ACTION_LABELS.get(action, "alterada")


def _hidden_action(action: str, team_abbreviation: str) -> TagActionPresentation:
    """Return the generic restricted action an outsider may see."""
    return TagActionPresentation(
        action=action,
        action_label=_action_label(action),
        visible=False,
        team_abbreviation=team_abbreviation,
    )


def _visible_action(
    *,
    action: str,
    name: str,
    color: str,
    state_label: str = "",
    team_abbreviation: str = "",
) -> TagActionPresentation:
    """Return the detailed action an authorized viewer may see."""
    return TagActionPresentation(
        action=action,
        action_label=_action_label(action),
        visible=True,
        name=name,
        color=color,
        state_label=state_label,
        team_abbreviation=team_abbreviation,
    )


def _summarise(
    actions: Sequence[TagActionPresentation], *, is_bulk: bool, unresolved: bool = False
) -> str:
    """Return the safe one-line description for the projected actions.

    Bulk actions stay count-only: the stored concatenated ``tag_names`` must
    never become the summary again. An unresolved legacy snapshot is described
    as unidentified instead of guessing a classification.
    """
    if is_bulk:
        return f"{len(actions)} tag(s) removida(s) em lote"
    if unresolved or not actions:
        return UNRESOLVED_TAG_AUDIT_SUMMARY
    first = actions[0]
    if first.visible:
        return f'Tag "{first.name}" {first.action_label}'
    team = f" ({first.team_abbreviation})" if first.team_abbreviation else ""
    return f"Tag restrita{team} {first.action_label}"


def _reference_action(
    reference: TagEventReference, visibility: Any
) -> TagActionPresentation:
    """Project one catalogue reference against current visibility."""
    tag = reference.tag
    if not visibility.can_read(tag):
        abbreviation = (
            tag.specialty.abbreviation
            if tag.specialty_id is not None and tag.specialty is not None
            else reference.specialty_abbreviation
        )
        return _hidden_action(reference.action, abbreviation or "")
    from apps.patients.services import tag_projection

    badge = tag_projection.tag_badge(tag)
    return _visible_action(
        action=reference.action,
        name=reference.tag_name,
        color=reference.tag_color,
        state_label=badge.state_label,
        team_abbreviation=badge.team_abbreviation,
    )


def _legacy_actions(
    event: Event,
    *,
    visibility: Any,
    resolver: LegacyEventResolver,
) -> tuple[tuple[TagActionPresentation, ...], bool]:
    """Project a reference-less legacy event, never guessing an identity."""
    resolution = resolver.resolve_event(event)
    names = legacy_event_names(event)
    action = (
        TagEventReference.Action.REMOVED
        if event.event_type != Event.TAG_ADDED_EVENT
        else TagEventReference.Action.ADDED
    )
    snapshot_color = str(getattr(event, "tag_color", "") or "")
    if resolution.status == "known" and len(names) == len(resolution.tag_ids):
        from apps.patients.services import tag_projection

        actions: list[TagActionPresentation] = []
        unidentified = False
        for name, tag_id in zip(names, resolution.tag_ids):
            tag = resolver.tag(tag_id)
            if tag is None:
                # Without the current catalogue row the current visibility
                # cannot be established, so the stored snapshot is only
                # presented to administrators.
                if visibility.is_administrator:
                    actions.append(
                        _visible_action(action=action, name=name, color=snapshot_color)
                    )
                else:
                    unidentified = True
                    actions.append(_hidden_action(action, ""))
                continue
            if not visibility.can_read(tag):
                actions.append(_hidden_action(action, _team_abbreviation(tag)))
                continue
            badge = tag_projection.tag_badge(tag)
            actions.append(
                _visible_action(
                    action=action,
                    name=name,
                    color=snapshot_color,
                    state_label=badge.state_label,
                    team_abbreviation=badge.team_abbreviation,
                )
            )
        return tuple(actions), unidentified
    if visibility.is_administrator:
        admin_actions = tuple(
            _visible_action(action=action, name=name, color=snapshot_color)
            for name in names
        )
        return admin_actions, True
    return (_hidden_action(action, ""),), True


def project_tag_audit_event(
    event: Event,
    *,
    viewer: Any,
    visibility: Any = None,
    references: Sequence[TagEventReference] | None = None,
    resolver: LegacyEventResolver | None = None,
) -> TagAuditPresentation | None:
    """Project one tag audit event for the requesting viewer.

    Returns ``None`` for events that are not tag audit events. Callers must use
    the returned presentation instead of the stored description, which keeps
    action-time tag names.
    """
    if event.event_type not in Event.TAG_AUDIT_EVENT_TYPES:
        return None
    from apps.patients.services import tag_projection

    visibility = visibility or tag_projection.Visibility.for_actor(viewer)
    is_bulk = event.event_type == Event.TAG_BULK_REMOVE_EVENT
    if references is None:
        references = list(
            TagEventReference.objects.filter(event_id=event.pk)
            .select_related("tag__specialty")
            .order_by("pk")
        )
    if references:
        actions = tuple(
            _reference_action(reference, visibility) for reference in references
        )
        return TagAuditPresentation(
            summary=_summarise(actions, is_bulk=is_bulk),
            actions=actions,
            is_bulk=is_bulk,
            unresolved=False,
        )
    actions, unresolved = _legacy_actions(
        event,
        visibility=visibility,
        resolver=resolver or LegacyEventResolver(),
    )
    return TagAuditPresentation(
        summary=_summarise(actions, is_bulk=is_bulk, unresolved=unresolved),
        actions=actions,
        is_bulk=is_bulk,
        unresolved=unresolved,
    )


def attach_tag_audit_presentations(events: Iterable[Event], *, viewer: Any) -> None:
    """Attach requester projections to tag audit events in one batched pass."""
    rows = list(events)
    audit_events = [row for row in rows if row.event_type in Event.TAG_AUDIT_EVENT_TYPES]
    if not audit_events:
        return
    from apps.patients.services import tag_projection

    visibility = tag_projection.Visibility.for_actor(viewer)
    references_by_event: dict[Any, list[TagEventReference]] = {}
    references = (
        TagEventReference.objects.filter(
            event_id__in=[row.pk for row in audit_events]
        )
        .select_related("tag__specialty")
        .order_by("pk")
    )
    for reference in references:
        references_by_event.setdefault(reference.event_id, []).append(reference)
    resolver = (
        LegacyEventResolver()
        if any(not references_by_event.get(row.pk) for row in audit_events)
        else None
    )
    for event in audit_events:
        event.tag_audit_presentation = project_tag_audit_event(
            event,
            viewer=viewer,
            visibility=visibility,
            references=references_by_event.get(event.pk, []),
            resolver=resolver,
        )


def tag_audit_payload(presentation: TagAuditPresentation) -> dict[str, Any]:
    """Serialize a presentation for JSON responses.

    Only fields the viewer may read are serialized; hidden actions carry the
    team abbreviation at most, never a name, colour, note or identifier.
    """
    return {
        "summary": presentation.summary,
        "is_bulk": presentation.is_bulk,
        "unresolved": presentation.unresolved,
        "actions": [
            {
                "action": action.action,
                "action_label": action.action_label,
                "visible": action.visible,
                "name": action.name,
                "color": action.color,
                "state_label": action.state_label,
                "team_abbreviation": action.team_abbreviation,
            }
            for action in presentation.actions
        ],
    }
