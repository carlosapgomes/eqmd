from django.contrib import admin
from .models import Event

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
