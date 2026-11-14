from collections.abc import Sequence

from django.contrib import admin
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin
from simple_history.models import HistoricalChanges

from .models import ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(SimpleHistoryAdmin):
    """Admin interface for ReportTemplate model.

    Tag controls stay absent from the admin: the admin is not an
    alternative unvalidated tag-write surface, and text saves through it
    preserve existing associations untouched. The M2M delta is also
    omitted from the built-in history display so restricted tag
    metadata cannot leak through history diffs; audit inspection of tag
    deltas remains a technical data-layer operation.
    """

    list_display = ["name", "is_active", "is_public", "updated_at", "updated_by"]
    list_filter = ["is_active", "is_public", "updated_at"]
    search_fields = ["name", "markdown_body"]
    readonly_fields = ["created_at", "created_by", "updated_at", "updated_by"]
    exclude = ("tags",)
    history_list_display = ["name", "is_active", "is_public", "updated_at", "updated_by"]

    fieldsets = (
        ("Template", {
            "fields": ("name", "markdown_body", "is_active", "is_public"),
        }),
        ("Audit", {
            "fields": ("created_at", "created_by", "updated_at", "updated_by"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by fields."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def set_history_delta_changes(
        self,
        request: HttpRequest,
        historical_records: Sequence[HistoricalChanges],
        foreign_keys_are_objs: bool = True,
    ) -> None:
        """Add history deltas with the tags M2M field omitted.

        Mirrors ``SimpleHistoryAdmin.set_history_delta_changes`` but
        excludes ``tags`` from every diff so restricted tag identities
        never appear in the admin history list.
        """
        previous = None
        for current in historical_records:
            if previous is None:
                previous = current
                continue
            delta = previous.diff_against(
                current,
                excluded_fields={"tags"},
                foreign_keys_are_objs=foreign_keys_are_objs,
            )
            helper = self.get_historical_record_context_helper(request, previous)
            previous.history_delta_changes = helper.context_for_delta_changes(delta)
            previous = current
