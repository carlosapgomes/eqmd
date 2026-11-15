"""Selectable-model lookup for report creation (S3, design D6).

Authenticated JSON discovery sharing the S2 query contract with the
catalogue, restricted to active public-or-own templates. The response
carries only projected metadata for readable templates/tags, bounded
pages, and a separately revalidated ``selected_template`` projection
that never broadens results or their count.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views import View

from apps.patients.models import AllowedTag
from apps.patients.services import tag_filters, tag_projection
from apps.reports.services import template_discovery
from apps.reports.services.template_tag_projection import template_tag_badges

SELECTED_TEMPLATE_PARAM = "selected_template"
RETAINED_TAGS_PARAM = "retained_tags"
INVALID_SELECTION_MESSAGE = "Seleção de modelo inválida."


def _query_without_transport_parameters(query):
    """Copy the lookup query without transport-only parameters.

    ``retained_tags`` (authorization input for pending choices) and
    ``selected_template`` (pinned-choice identity) are not filter
    state. Stripping them locally -- shared tag-filter helpers and
    the S2 catalogue are untouched -- keeps omitted/unreadable ids
    out of rebuilt ``remove_querystring`` links and browser URLs.
    """
    params = query.copy()
    params.pop(RETAINED_TAGS_PARAM, None)
    params.pop(SELECTED_TEMPLATE_PARAM, None)
    return params


def _tag_payload(actor, templates) -> dict:
    """Project visible tag badges for a bounded set of templates."""
    badges = template_tag_badges(actor=actor, templates=templates)
    payload: dict[str, list[dict]] = {}
    for template in templates:
        payload[str(template.pk)] = [
            {
                "tag_id": badge.tag_id,
                "name": badge.name,
                "display_name": badge.display_name,
                "color": badge.color,
                "state": badge.state,
                "state_label": badge.state_label,
                "team_abbreviation": badge.team_abbreviation,
                "is_restricted": badge.is_restricted,
            }
            for badge in badges.get(template.pk, [])
        ]
    return payload


def _selected_tag_payload(actor, tags, *, query, selection) -> list[dict]:
    """Project the filter's selected tags (already visibility-checked).

    Each entry also carries the effective ``remove_querystring`` for
    that tag (manual state minus the tag), mirroring the server
    rendered summary badges so enhanced rebuilds recreate the
    per-badge remove links with the same parameters.
    """
    return [
        {
            "tag_id": badge.tag_id,
            "name": badge.name,
            "display_name": badge.display_name,
            "color": badge.color,
            "state": badge.state,
            "state_label": badge.state_label,
            "team_abbreviation": badge.team_abbreviation,
            "is_restricted": badge.is_restricted,
            "remove_querystring": tag_filters.remove_tag_query(
                query, selection, badge.tag_id
            ),
        }
        for badge in (tag_projection.tag_badge(tag) for tag in tags)
    ]


def _retained_tag_options(actor, raw_values) -> list[dict]:
    """Authorize pending retained tag choices against current visibility.

    The client sends the ids currently selected in the tag control
    (pending, not necessarily applied) via ``retained_tags`` so the
    server can tell readable historical omissions from revoked
    choices. Only ids readable right now (``visible_catalogue``,
    archived rows included) are returned, projected like
    ``tag_options``; unknown, malformed or unreadable ids are
    silently omitted (never echoed, never a filter, never a 400),
    so a revoked pending choice simply is not authorized to stay.
    """
    requested: list[int] = []
    for raw in raw_values:
        try:
            tag_id = int(str(raw))
        except (TypeError, ValueError):
            continue
        if tag_id not in requested:
            requested.append(tag_id)
    if not requested:
        return []
    rows = list(
        tag_projection.visible_catalogue(actor)
        .filter(pk__in=requested)
        .order_by("name", "pk")
    )
    return [
        {
            "tag_id": badge.tag_id,
            "display_name": badge.display_name,
            "state_label": badge.state_label,
            "is_selected": True,
            "is_historical": (tag.lifecycle_state != AllowedTag.LifecycleState.ACTIVE),
        }
        for tag in rows
        for badge in (tag_projection.tag_badge(tag),)
    ]


class TemplateSelectionView(LoginRequiredMixin, View):
    """Return one bounded page of selectable templates as JSON."""

    def get(self, request, *args, **kwargs):
        """Resolve filters, page and selected choice without content data."""
        discovery = template_discovery.resolve_discovery_state(
            request.user, request.GET
        )
        if discovery.error:
            return JsonResponse({"error": discovery.error}, status=400)

        selected_raw = request.GET.get(SELECTED_TEMPLATE_PARAM)
        selected_uuid: uuid.UUID | None = None
        if selected_raw:
            try:
                selected_uuid = uuid.UUID(str(selected_raw))
            except (ValueError, AttributeError, TypeError):
                return JsonResponse({"error": INVALID_SELECTION_MESSAGE}, status=400)

        base = template_discovery.selectable_base_queryset(request.user)
        filtered = template_discovery.apply_discovery_filters(
            base, discovery.selection, discovery.name_query
        )
        paginator = Paginator(filtered, template_discovery.PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))
        page_templates = list(page_obj.object_list)
        tags_by_template = _tag_payload(request.user, page_templates)

        selected = None
        selection_unavailable = False
        if selected_uuid is not None:
            match = base.filter(pk=selected_uuid).first()
            if match is None:
                selection_unavailable = True
            else:
                selected_tags = _tag_payload(request.user, [match])[str(match.pk)]
                selected = {
                    "id": str(match.pk),
                    "name": match.name,
                    "tags": selected_tags,
                }

        selection = discovery.selection
        include_historical = template_discovery.parse_include_historical(request.GET)
        payload = {
            "results": [
                {
                    "id": str(template.pk),
                    "name": template.name,
                    "tags": tags_by_template[str(template.pk)],
                }
                for template in page_templates
            ],
            "count": paginator.count,
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "filter": {
                "source": selection.source,
                "mode": selection.mode,
                "selected_tags": _selected_tag_payload(
                    request.user,
                    selection.tags,
                    query=_query_without_transport_parameters(request.GET),
                    selection=selection,
                ),
                "warning": discovery.warning,
            },
            "tag_options": [
                {
                    "tag_id": option.tag_id,
                    "display_name": option.display_name,
                    "state_label": option.state_label,
                    "is_selected": option.is_selected,
                    "is_historical": option.is_historical,
                }
                for option in template_discovery.discovery_tag_options(
                    request.user,
                    selected_ids=selection.tag_ids,
                    include_historical=include_historical,
                )
            ],
            "retained_tag_options": _retained_tag_options(
                request.user, request.GET.getlist(RETAINED_TAGS_PARAM)
            ),
            "selected": selected,
            "selection_unavailable": selection_unavailable,
        }
        response = JsonResponse(payload)
        response["Cache-Control"] = "no-store"
        return response
