from django.contrib import admin
from .models import HistoryAndPhysical


@admin.register(HistoryAndPhysical)
class HistoryAndPhysicalAdmin(admin.ModelAdmin):
    """Admin configuration for HistoryAndPhysical model."""

    list_display = [
        'patient',
        'event_datetime',
        'created_by',
        'created_at',
        'updated_at'
    ]

    list_filter = [
        'event_datetime',
        'created_at',
        'updated_at',
        'created_by'
    ]

    search_fields = [
        'patient__name',
        'content',
        'description'
    ]

    readonly_fields = [
        'id',
        'event_type',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('Informações do Evento', {
            'fields': ('patient', 'event_datetime', 'description')
        }),
        ('Conteúdo', {
            'fields': ('content',)
        }),
        ('Auditoria', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Sistema', {
            'fields': ('id', 'event_type'),
            'classes': ('collapse',)
        })
    )

    ordering = ['-event_datetime']

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('patient', 'created_by', 'updated_by')