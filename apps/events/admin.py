from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Event, RecordNumberChangeEvent, AdmissionEvent, DischargeEvent
)


def is_tag_audit_event(event):
    """Return whether the event records an immutable patient tag action."""
    return event is not None and event.event_type in Event.TAG_AUDIT_EVENT_TYPES


@admin.register(Event)
class EventAdmin(SimpleHistoryAdmin):
    list_display = (
        'description', 'event_type', 'event_datetime', 'patient', 'created_by', 
        'is_deleted', 'deleted_at', 'deleted_by', 'created_at'
    )
    list_filter = ('is_deleted', 'event_type', 'created_at', 'event_datetime', 'deleted_at')
    search_fields = ('description', 'patient__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'deleted_at', 'deleted_by', 'deletion_reason', 'created_at', 'updated_at')
    history_list_display = ['description', 'event_type', 'patient', 'history_change_reason']

    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'event_datetime', 'patient', 'description')
        }),
        ('Deletion Information', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by', 'deletion_reason'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        # Show all events including deleted ones in admin
        return Event.all_objects.select_related(
            'patient', 'created_by', 'updated_by'
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/restore/',
                self.admin_site.admin_view(self.restore_event),
                name='events_event_restore',
            ),
        ]
        return custom_urls + urls

    def restore_event(self, request, object_id):
        """Restore a soft-deleted event."""
        event = Event.all_objects.get(id=object_id)
        event.restore(restored_by=request.user)

        messages.success(
            request,
            f'Event "{event.description}" has been successfully restored.'
        )

        return HttpResponseRedirect(f'/admin/events/event/{object_id}/change/')

    actions = ['soft_delete_selected', 'restore_selected']

    def soft_delete_selected(self, request, queryset):
        """Soft delete selected events, skipping immutable tag audit events."""
        count = 0
        skipped = 0
        for event in queryset:
            if event.is_deleted:
                continue
            if is_tag_audit_event(event):
                skipped += 1
                continue
            event.delete(
                deleted_by=request.user,
                reason=f'Bulk deletion by admin {request.user.username}'
            )
            count += 1

        messages.success(
            request,
            f'{count} event(s) were soft deleted.'
        )
        if skipped:
            messages.warning(
                request,
                f'{skipped} tag audit event(s) were kept: correct the tag '
                'assignment instead of deleting its history.'
            )
    soft_delete_selected.short_description = "Soft delete selected events"

    def restore_selected(self, request, queryset):
        """Restore selected events."""
        count = 0
        for event in queryset:
            if event.is_deleted:
                event.restore(restored_by=request.user)
                count += 1

        messages.success(
            request,
            f'{count} event(s) were restored.'
        )
    restore_selected.short_description = "Restore selected events"

    def has_change_permission(self, request, obj=None):
        """Tag audit events are append-only: no ordinary admin edit."""
        if is_tag_audit_event(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Tag audit events cannot be deleted, also not in bulk."""
        if is_tag_audit_event(obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if is_tag_audit_event(obj):
            readonly.extend(
                ['event_type', 'event_datetime', 'patient', 'description']
            )
        return readonly

    def save_model(self, request, obj, form, change):
        """Refuse fabricating tag audit events outside the tag workflow."""
        if is_tag_audit_event(obj):
            raise PermissionDenied(
                'Tag audit events are recorded by the patient tag workflow.'
            )
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        if is_tag_audit_event(obj):
            raise PermissionDenied(
                'Tag audit events are immutable and cannot be deleted.'
            )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if any(is_tag_audit_event(event) for event in queryset):
            raise PermissionDenied(
                'Tag audit events are immutable and cannot be deleted.'
            )
        super().delete_queryset(request, queryset)


@admin.register(RecordNumberChangeEvent)
class RecordNumberChangeEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'old_record_number', 'new_record_number', 'created_by']
    list_filter = ['event_datetime', 'created_at']
    search_fields = ['patient__name', 'old_record_number', 'new_record_number']
    readonly_fields = ['event_type', 'created_at', 'updated_at']


@admin.register(AdmissionEvent)
class AdmissionEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'admission_type', 'initial_bed', 'created_by']
    list_filter = ['admission_type', 'event_datetime', 'created_at']
    search_fields = ['patient__name', 'admission_diagnosis']
    readonly_fields = ['event_type', 'created_at', 'updated_at']


@admin.register(DischargeEvent)
class DischargeEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'discharge_type', 'stay_duration_days', 'created_by']
    list_filter = ['discharge_type', 'event_datetime', 'created_at']
    search_fields = ['patient__name', 'discharge_diagnosis']
    readonly_fields = ['event_type', 'created_at', 'updated_at']
