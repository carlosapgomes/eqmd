"""Presentation-only adapter for canonical catalogue filter actions."""

from typing import Any

from django.urls import reverse

from apps.reports.services.template_catalogue_filter_actions import action_context
from apps.reports.views.template_views import TemplateListView


class TemplateCatalogueFilterActionsView(TemplateListView):
    """Preserve eligibility, parsing and fragments from the existing view."""

    def get_context_data(
        self, **kwargs: Any
    ) -> dict[str, Any]:  # Any: Django's heterogeneous template context.
        context = super().get_context_data(**kwargs)
        context.update(
            action_context(
                self.request.GET,
                self.discovery,
                page_url=reverse("reports:template_list"),
            )
        )
        return context
