"""Read-only, requester-aware searchable tag lookup (TFUX S3, design D5).

The catalogue's enhanced selector reuses ``tag_lookup.search_visible_tags``
and the requester-aware projection, but through a reports-owned read-only
view/URL gated by the same boundary as report-template discovery: any
authenticated report reader. It never requires ``patients.view_patient`` and
never weakens ``TagLookupView``. Only metadata the projection already allows
reaches the payload.
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, JsonResponse
from django.views import View

from apps.patients.models import AllowedTag
from apps.patients.services import tag_filters, tag_lookup, tag_projection
from apps.patients.services.tag_projection import TagBadge
from apps.reports.forms_report_tag_lookup import ReportTagLookupForm


def _badge_payload(badge: TagBadge) -> dict[str, object]:
    """Serialize only metadata the requester projection already allowed."""
    return {
        "id": badge.tag_id,
        "name": badge.name,
        "display_name": badge.display_name,
        "color": badge.color,
        "team_abbreviation": badge.team_abbreviation,
        "state": badge.state,
        "state_label": badge.state_label,
        "is_historical": badge.state != AllowedTag.LifecycleState.ACTIVE,
        "is_restricted": badge.is_restricted,
    }


class ReportTagLookupView(LoginRequiredMixin, View):
    """GET-only paginated catalogue search for the catalogue selector."""

    def get(
        self, request: HttpRequest, *args: HttpRequest, **kwargs: HttpRequest
    ) -> JsonResponse:
        form = ReportTagLookupForm(request.GET)
        if not form.is_valid():
            return self._generic_error()

        try:
            selected_tags = tag_filters.resolve_visible_tags(
                request.user,
                tag_filters.parse_tag_ids(request.GET.getlist("selected")),
            )
        except tag_projection.InvalidTagFilter:
            return self._generic_error()

        page = tag_lookup.search_visible_tags(
            request.user,
            query=form.cleaned_search(),
            include_historical=form.include_historical_requested(),
            page=form.page_or_default(),
            page_size=form.page_size_or_default(),
        )
        return JsonResponse(
            {
                "results": [_badge_payload(badge) for badge in page.badges],
                "selected": [
                    _badge_payload(tag_projection.tag_badge(tag))
                    for tag in selected_tags
                ],
                "count": page.count,
                "page": page.page,
                "num_pages": page.num_pages,
                "page_size": page.page_size,
                "has_next": page.has_next,
                "has_previous": page.has_previous,
                "include_historical": form.include_historical_requested(),
            },
            json_dumps_params={"ensure_ascii": False},
        )

    def _generic_error(self) -> JsonResponse:
        return JsonResponse(
            {"error": tag_projection.INVALID_TAG_FILTER_MESSAGE},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
