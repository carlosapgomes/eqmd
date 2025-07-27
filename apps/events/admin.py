from django.contrib import admin
from .models import (
    Event, RecordNumberChangeEvent, AdmissionEvent, DischargeEvent
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('description', 'event_type', 'event_datetime', 'patient', 'created_by', 'created_at')
    list_filter = ('event_type', 'created_at', 'event_datetime')
    search_fields = ('description', 'patient__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient', 'created_by', 'updated_by'
        )


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
