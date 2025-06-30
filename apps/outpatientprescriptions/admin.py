from django.contrib import admin
from .models import OutpatientPrescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    """Inline admin for PrescriptionItem within OutpatientPrescription."""
    model = PrescriptionItem
    extra = 1
    fields = ['order', 'drug_name', 'presentation', 'usage_instructions', 'quantity']
    ordering = ['order']


@admin.register(OutpatientPrescription)
class OutpatientPrescriptionAdmin(admin.ModelAdmin):
    """Admin configuration for OutpatientPrescription model."""
    list_display = ['patient', 'prescription_date', 'status', 'created_by']
    list_filter = ['status', 'prescription_date', 'created_at']
    search_fields = ['patient__name', 'instructions']
    readonly_fields = ['created_at', 'updated_at', 'event_datetime']
    inlines = [PrescriptionItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('patient', 'prescription_date', 'status')
        }),
        ('Instruções', {
            'fields': ('instructions',)
        }),
        ('Metadados', {
            'fields': ('created_by', 'created_at', 'updated_at', 'event_datetime'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    """Admin configuration for PrescriptionItem model."""
    list_display = ['prescription', 'drug_name', 'presentation', 'order']
    list_filter = ['prescription__status', 'prescription__prescription_date']
    search_fields = ['drug_name', 'presentation', 'prescription__patient__name']
    ordering = ['prescription', 'order']
