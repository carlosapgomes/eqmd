from django.contrib import admin
from .models import DataProcessingPurpose, LGPDComplianceSettings, PatientDataRequest, DataCorrectionDetail

@admin.register(DataProcessingPurpose)
class DataProcessingPurposeAdmin(admin.ModelAdmin):
    list_display = ['data_category', 'purpose', 'legal_basis', 'retention_period_days', 'is_active']
    list_filter = ['data_category', 'purpose', 'legal_basis', 'is_active']
    search_fields = ['description', 'data_fields_included']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = [
        ('Informações Básicas', {
            'fields': ['data_category', 'purpose', 'legal_basis', 'is_active']
        }),
        ('Documentação', {
            'fields': ['description', 'data_fields_included', 'processing_activities']
        }),
        ('Compartilhamento', {
            'fields': ['data_recipients', 'international_transfers', 'transfer_safeguards']
        }),
        ('Retenção e Segurança', {
            'fields': ['retention_period_days', 'retention_criteria', 'security_measures']
        }),
        ('Metadados', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        })
    ]
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(LGPDComplianceSettings)
class LGPDComplianceSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Encarregado de Dados (DPO)', {
            'fields': ['dpo_name', 'dpo_email', 'dpo_phone']
        }),
        ('Controlador de Dados', {
            'fields': ['controller_name', 'controller_address', 'controller_cnpj']
        }),
        ('Configurações de Incidente', {
            'fields': ['anpd_notification_threshold', 'breach_notification_email']
        }),
        ('Retenção de Dados', {
            'fields': ['default_retention_days', 'deletion_warning_days']
        }),
        ('Política de Privacidade', {
            'fields': ['privacy_policy_version', 'privacy_policy_last_updated']
        }),
        ('Limites de Detecção de Incidentes', {
            'fields': [
                'breach_detection_failed_login_threshold',
                'breach_detection_bulk_access_threshold', 
                'breach_detection_off_hours_threshold',
                'breach_detection_geographic_anomaly_km',
                'breach_detection_data_export_threshold'
            ]
        })
    ]
    
    def has_add_permission(self, request):
        # Only allow one settings record
        return not LGPDComplianceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False


@admin.register(PatientDataRequest)
class PatientDataRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'request_type', 'requester_name', 'status', 'requested_at', 'due_date', 'is_overdue']
    list_filter = ['request_type', 'status', 'requester_relationship', 'requested_at']
    search_fields = ['request_id', 'requester_name', 'requester_email', 'patient_name_provided']
    readonly_fields = ['request_id', 'requested_at', 'due_date', 'created_at', 'updated_at']

    fieldsets = [
        ('Identificação da Solicitação', {
            'fields': ['request_id', 'request_type', 'priority', 'status']
        }),
        ('Dados do Solicitante', {
            'fields': ['requester_name', 'requester_email', 'requester_phone', 'requester_relationship']
        }),
        ('Identificação do Paciente', {
            'fields': ['patient', 'patient_name_provided', 'patient_cpf_provided', 'patient_birth_date_provided', 'additional_identifiers']
        }),
        ('Solicitação', {
            'fields': ['description', 'data_export_format']
        }),
        ('Documentos', {
            'fields': ['identity_document', 'authorization_document']
        }),
        ('Processamento', {
            'fields': ['created_by', 'assigned_to', 'reviewed_by', 'reviewed_at', 'response_notes', 'rejection_reason', 'legal_basis_for_rejection']
        }),
        ('Resposta', {
            'fields': ['response_file', 'response_sent_at', 'anpd_notification_sent']
        }),
        ('Datas', {
            'fields': ['requested_at', 'due_date', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Em atraso'

    actions = ['mark_as_completed', 'export_selected']

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} solicitações marcadas como concluídas.')
    mark_as_completed.short_description = 'Marcar como concluído'


@admin.register(DataCorrectionDetail)
class DataCorrectionDetailAdmin(admin.ModelAdmin):
    list_display = ['request', 'field_name', 'approved', 'correction_applied', 'reviewed_by']
    list_filter = ['approved', 'correction_applied', 'reviewed_at']
    search_fields = ['request__request_id', 'field_name', 'current_value', 'requested_value']

    fieldsets = [
        ('Solicitação de Correção', {
            'fields': ['request', 'field_name', 'current_value', 'requested_value', 'justification']
        }),
        ('Revisão', {
            'fields': ['approved', 'review_notes', 'reviewed_by', 'reviewed_at']
        }),
        ('Aplicação', {
            'fields': ['correction_applied', 'applied_at', 'applied_by']
        })
    ]
