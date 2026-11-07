from django.contrib import admin
from django.forms import ClearableFileInput
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin

from .models import ConsentTemplate, ConsentForm, ConsentAttachment


class ConsentAttachmentServeLink:
    """File value whose ``url`` resolves to the authenticated serve route.

    ``ClearableFileInput`` renders ``value.url`` for the existing-file link, so
    swapping only that attribute reroutes the link without touching the stored
    field (design D3).
    """

    def __init__(self, file_field, url):
        self._file_field = file_field
        self.url = url

    def __str__(self):
        return str(self._file_field)


class ConsentAttachmentServeFileInput(ClearableFileInput):
    """Existing-file link for consent attachments points at the serve route."""

    def format_value(self, value):
        instance = getattr(value, "instance", None)
        if instance is None or not instance.pk:
            return super().format_value(value)
        return ConsentAttachmentServeLink(
            value,
            reverse(
                "consentforms:consentattachment_serve", kwargs={"pk": instance.pk}
            ),
        )


@admin.register(ConsentTemplate)
class ConsentTemplateAdmin(SimpleHistoryAdmin):
    list_display = ["name", "is_active", "updated_at", "updated_by"]
    list_filter = ["is_active", "updated_at"]
    search_fields = ["name", "markdown_body"]
    readonly_fields = ["created_at", "created_by", "updated_at", "updated_by"]
    history_list_display = ["name", "is_active", "updated_at", "updated_by"]

    fieldsets = (
        ("Template", {
            "fields": ("name", "markdown_body", "is_active"),
        }),
        ("Auditoria", {
            "fields": ("created_at", "created_by", "updated_at", "updated_by"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class ConsentAttachmentInline(admin.TabularInline):
    model = ConsentAttachment
    extra = 0
    readonly_fields = ["original_filename", "file_size", "mime_type", "file_type", "created_at"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "file":
            kwargs.setdefault("widget", ConsentAttachmentServeFileInput)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(ConsentForm)
class ConsentFormAdmin(admin.ModelAdmin):
    list_display = ["patient", "template", "document_date", "created_by", "created_at"]
    list_filter = ["document_date", "created_at", "template"]
    search_fields = ["patient__name", "template__name", "procedure_description"]
    readonly_fields = ["event_type", "created_at", "updated_at", "rendered_at"]
    inlines = [ConsentAttachmentInline]

    fieldsets = (
        ("Evento", {
            "fields": ("patient", "template", "document_date", "event_datetime", "description"),
        }),
        ("Conteúdo", {
            "fields": ("procedure_description", "rendered_markdown", "rendered_at"),
        }),
        ("Auditoria", {
            "fields": ("created_by", "updated_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
        ("Sistema", {
            "fields": ("event_type",),
            "classes": ("collapse",),
        }),
    )


@admin.register(ConsentAttachment)
class ConsentAttachmentAdmin(admin.ModelAdmin):
    list_display = ["consent_form", "original_filename", "file_type", "created_at"]
    list_filter = ["file_type", "created_at"]
    search_fields = ["original_filename", "consent_form__patient__name"]
    readonly_fields = ["created_at", "file_size", "mime_type"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "file":
            kwargs.setdefault("widget", ConsentAttachmentServeFileInput)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
