from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    Event, RecordNumberChangeEvent, AdmissionEvent, DischargeEvent
)

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
        """Soft delete selected events."""
        count = 0
        for event in queryset:
            if not event.is_deleted:
                event.delete(
                    deleted_by=request.user,
                    reason=f'Bulk deletion by admin {request.user.username}'
                )
                count += 1

        messages.success(
            request,
            f'{count} event(s) were soft deleted.'
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
