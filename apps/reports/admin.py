from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(SimpleHistoryAdmin):
    """Admin interface for ReportTemplate model."""

    list_display = ["name", "is_active", "is_public", "updated_at", "updated_by"]
    list_filter = ["is_active", "is_public", "updated_at"]
    search_fields = ["name", "markdown_body"]
    readonly_fields = ["created_at", "created_by", "updated_at", "updated_by"]
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
