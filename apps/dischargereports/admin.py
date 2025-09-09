from django.contrib import admin
from .models import DischargeReport


@admin.register(DischargeReport)
class DischargeReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medical_specialty', 'admission_date', 'discharge_date', 'status_display', 'created_at']
    list_filter = ['is_draft', 'medical_specialty', 'admission_date', 'discharge_date', 'created_at']
    search_fields = ['patient__name', 'medical_specialty', 'problems_and_diagnosis']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'status_display']

    def status_display(self, obj):
        return obj.status_display
    status_display.short_description = 'Status'

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('patient', 'event_datetime', 'description', 'is_draft')
        }),
        ('Datas', {
            'fields': ('admission_date', 'discharge_date')
        }),
        ('Especialidade', {
            'fields': ('medical_specialty',)
        }),
        ('Conteúdo Médico', {
            'fields': ('problems_and_diagnosis', 'admission_history', 'exams_list',
                      'procedures_list', 'inpatient_medical_history', 'discharge_status',
                      'discharge_recommendations'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )