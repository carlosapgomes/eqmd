from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    DataProcessingPurpose, LGPDComplianceSettings, PatientDataRequest, DataCorrectionDetail,
    PrivacyPolicy, DataProcessingNotice, ConsentRecord, MinorConsentRecord, ConsentWithdrawal,
    DataRetentionPolicy, DataRetentionSchedule, DataDeletionLog, DataAnonymizationLog,
    AnonymizationPolicy, SecurityIncident, IncidentAction, BreachNotification, IncidentEvidence
)

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


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ['title', 'version', 'policy_type', 'effective_date', 'is_active', 'legal_review_completed']
    list_filter = ['policy_type', 'is_active', 'legal_review_completed', 'effective_date']
    search_fields = ['title', 'version', 'summary']
    readonly_fields = ['created_at']
    
    fieldsets = [
        ('Informações Básicas', {
            'fields': ['title', 'version', 'policy_type', 'summary']
        }),
        ('Conteúdo', {
            'fields': ['content_markdown']
        }),
        ('Vigência', {
            'fields': ['effective_date', 'is_active']
        }),
        ('Revisão Legal', {
            'fields': ['legal_review_completed', 'legal_reviewer', 'legal_review_date']
        }),
        ('Notificação', {
            'fields': ['notification_sent', 'notification_sent_at']
        }),
        ('Metadados', {
            'fields': ['created_at', 'created_by'],
            'classes': ['collapse']
        })
    ]
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DataProcessingNotice)
class DataProcessingNoticeAdmin(admin.ModelAdmin):
    list_display = ['notice_id', 'context', 'title', 'display_format', 'is_active']
    list_filter = ['context', 'display_format', 'is_active']
    search_fields = ['notice_id', 'title', 'purpose_description']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['notice_id', 'context', 'title']
        }),
        ('Conteúdo do Aviso', {
            'fields': ['purpose_description', 'data_categories', 'legal_basis', 'retention_period', 'recipients']
        }),
        ('Direitos e Contato', {
            'fields': ['rights_summary', 'contact_info']
        }),
        ('Configurações de Exibição', {
            'fields': ['display_format', 'is_active']
        })
    ]


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ['consent_id', 'patient', 'consent_type', 'consent_source', 'status', 'granted_at', 'is_valid']
    list_filter = ['consent_type', 'consent_source', 'status', 'granted_by_relationship', 'consent_method']
    search_fields = ['patient__name', 'granted_by', 'purpose_description', 'hospital_consent_reference']
    readonly_fields = ['consent_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['consent_id', 'patient', 'consent_type']
        }),
        ('Detalhes do Consentimento', {
            'fields': ['purpose_description', 'data_categories', 'processing_activities']
        }),
        ('Status', {
            'fields': ['status', 'granted_at', 'withdrawn_at', 'expiration_date']
        }),
        ('Contexto', {
            'fields': ['granted_by', 'granted_by_relationship', 'consent_method']
        }),
        ('Dados Técnicos', {
            'fields': ['ip_address', 'user_agent'],
            'classes': ['collapse']
        }),
        ('Base Legal', {
            'fields': ['legal_basis', 'lawful_basis_explanation']
        }),
        ('Evidência', {
            'fields': ['consent_evidence', 'hospital_consent_document', 'hospital_consent_reference']
        }),
        ('Origem do Consentimento', {
            'fields': ['consent_source'],
            'description': 'Identifica se o consentimento veio de formulário hospitalar ou foi coletado diretamente'
        })
    ]
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Válido'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Add annotation to show hospital-based consents clearly
        return qs.select_related('patient')


@admin.register(MinorConsentRecord)
class MinorConsentRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'guardian_name', 'guardian_relationship', 'age_at_consent', 'consent_date', 'guardian_id_verified']
    list_filter = ['guardian_relationship', 'consent_method', 'guardian_id_verified']
    search_fields = ['patient__name', 'guardian_name', 'guardian_email']
    
    fieldsets = [
        ('Paciente Menor', {
            'fields': ['patient', 'patient_birth_date', 'age_at_consent', 'is_minor']
        }),
        ('Responsável Legal', {
            'fields': ['guardian_name', 'guardian_relationship', 'guardian_document', 'guardian_phone', 'guardian_email']
        }),
        ('Consentimento', {
            'fields': ['consent_date', 'consent_method', 'guardian_id_verified', 'verification_method']
        }),
        ('Proteções Especiais', {
            'fields': ['data_sharing_restricted', 'marketing_prohibited', 'research_participation_allowed']
        }),
        ('Documentação', {
            'fields': ['consent_document']
        })
    ]


@admin.register(ConsentWithdrawal)
class ConsentWithdrawalAdmin(admin.ModelAdmin):
    list_display = ['consent_record', 'withdrawn_by', 'withdrawn_at', 'data_deleted']
    list_filter = ['withdrawn_at', 'data_deleted']
    search_fields = ['consent_record__patient__name', 'withdrawn_by', 'reason']
    readonly_fields = ['withdrawn_at']
    
    fieldsets = [
        ('Retirada', {
            'fields': ['consent_record', 'withdrawn_by', 'reason', 'withdrawn_at']
        }),
        ('Processamento Pós-Retirada', {
            'fields': ['data_deleted', 'data_deleted_at', 'deletion_evidence']
        })
    ]


@admin.register(DataRetentionPolicy)
class DataRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_id', 'name', 'data_category', 'retention_period_days', 
        'retention_years', 'auto_delete_enabled', 'is_active'
    ]
    list_filter = [
        'data_category', 'retention_basis', 'auto_delete_enabled', 
        'anonymize_instead_delete', 'is_active'
    ]
    search_fields = ['policy_id', 'name', 'legal_reference']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['policy_id', 'name', 'data_category', 'is_active']
        }),
        ('Período de Retenção', {
            'fields': ['retention_period_days', 'retention_basis', 'legal_reference']
        }),
        ('Avisos e Prazos', {
            'fields': ['warning_period_days', 'grace_period_days']
        }),
        ('Comportamento de Exclusão', {
            'fields': [
                'auto_delete_enabled', 'anonymize_instead_delete', 
                'require_manual_approval'
            ]
        }),
        ('Proteções', {
            'fields': ['legal_hold_exempt', 'emergency_access_required']
        }),
        ('Metadados', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        })
    ]
    
    def retention_years(self, obj):
        return f"{obj.retention_period_days / 365.25:.1f} anos"
    retention_years.short_description = 'Anos de Retenção'
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DataRetentionSchedule)
class DataRetentionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'content_object_link', 'retention_policy', 'status', 
        'retention_end_date', 'days_remaining', 'warning_sent'
    ]
    list_filter = [
        'status', 'retention_policy__data_category', 'content_type',
        'retention_end_date', 'warning_sent_at'
    ]
    search_fields = ['object_id']
    readonly_fields = [
        'content_type', 'object_id', 'data_creation_date', 
        'retention_end_date', 'warning_date', 'deletion_date',
        'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Objeto de Dados', {
            'fields': ['content_type', 'object_id']
        }),
        ('Política de Retenção', {
            'fields': ['retention_policy']
        }),
        ('Datas Calculadas', {
            'fields': [
                'data_creation_date', 'last_activity_date',
                'retention_end_date', 'warning_date', 'deletion_date'
            ]
        }),
        ('Status e Processamento', {
            'fields': [
                'status', 'warning_sent_at', 'deletion_approved_by', 
                'deletion_approved_at'
            ]
        }),
        ('Retenção Legal', {
            'fields': [
                'legal_hold_reason', 'legal_hold_applied_by', 
                'legal_hold_applied_at'
            ]
        })
    ]
    
    def content_object_link(self, obj):
        if obj.content_object:
            return format_html(
                '<a href="{}">{}</a>',
                reverse(f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                       args=[obj.object_id]),
                str(obj.content_object)
            )
        return "Object not found"
    content_object_link.short_description = 'Objeto'
    
    def days_remaining(self, obj):
        from datetime import date
        if obj.retention_end_date:
            remaining = (obj.retention_end_date - date.today()).days
            if remaining < 0:
                return format_html('<span style="color: red;">Vencido ({} dias)</span>', abs(remaining))
            elif remaining < 30:
                return format_html('<span style="color: orange;">{} dias</span>', remaining)
            else:
                return f"{remaining} dias"
        return "-"
    days_remaining.short_description = 'Dias Restantes'
    
    def warning_sent(self, obj):
        return obj.warning_sent_at is not None
    warning_sent.boolean = True
    warning_sent.short_description = 'Aviso Enviado'
    
    actions = ['apply_legal_hold', 'approve_deletion']
    
    def apply_legal_hold(self, request, queryset):
        # Would open a form for legal hold reason
        pass
    apply_legal_hold.short_description = 'Aplicar retenção legal'
    
    def approve_deletion(self, request, queryset):
        updated = queryset.update(
            deletion_approved_by=request.user,
            deletion_approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} exclusões aprovadas.')
    approve_deletion.short_description = 'Aprovar exclusão'


@admin.register(DataDeletionLog)
class DataDeletionLogAdmin(admin.ModelAdmin):
    list_display = [
        'deletion_id', 'original_object_representation', 'deletion_type',
        'executed_at', 'authorized_by', 'deletion_verified'
    ]
    list_filter = [
        'deletion_type', 'deletion_method', 'deletion_verified', 
        'executed_at', 'content_type'
    ]
    search_fields = [
        'deletion_id', 'original_object_representation', 'deletion_reason'
    ]
    readonly_fields = [
        'deletion_id', 'content_type', 'original_object_id',
        'verification_hash', 'executed_at'
    ]
    
    fieldsets = [
        ('Identificação da Exclusão', {
            'fields': [
                'deletion_id', 'content_type', 'original_object_id',
                'original_object_representation'
            ]
        }),
        ('Detalhes da Exclusão', {
            'fields': [
                'deletion_type', 'deletion_reason', 'retention_policy_applied'
            ]
        }),
        ('Autorização', {
            'fields': ['authorized_by', 'authorization_date']
        }),
        ('Execução', {
            'fields': [
                'executed_by', 'executed_at', 'deletion_method'
            ]
        }),
        ('Verificação', {
            'fields': [
                'verification_hash', 'deletion_verified', 'verification_date'
            ]
        }),
        ('Impacto', {
            'fields': [
                'related_records_affected', 'cascading_deletions'
            ]
        }),
        ('Conformidade Legal', {
            'fields': ['legal_basis_for_deletion', 'compliance_notes']
        }),
        ('Recuperação', {
            'fields': [
                'recovery_possible', 'recovery_deadline'
            ]
        })
    ]
    
    def has_add_permission(self, request):
        return False  # Logs should only be created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should be immutable


@admin.register(DataAnonymizationLog)
class DataAnonymizationLogAdmin(admin.ModelAdmin):
    list_display = [
        'anonymization_id', 'content_type', 'anonymization_method',
        'anonymization_purpose', 're_identification_risk', 'executed_at'
    ]
    list_filter = [
        'anonymization_method', 'anonymization_purpose', 're_identification_risk',
        'executed_at'
    ]
    readonly_fields = ['anonymization_id', 'executed_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': [
                'anonymization_id', 'content_type', 'original_object_id',
                'anonymized_object_id'
            ]
        }),
        ('Método de Anonimização', {
            'fields': [
                'anonymization_method', 'fields_anonymized', 'anonymization_rules'
            ]
        }),
        ('Controle de Qualidade', {
            'fields': [
                'anonymization_quality_score', 're_identification_risk'
            ]
        }),
        ('Execução', {
            'fields': ['executed_by', 'executed_at']
        }),
        ('Finalidade e Retenção', {
            'fields': [
                'anonymization_purpose', 'anonymized_data_retention'
            ]
        })
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AnonymizationPolicy)
class AnonymizationPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_name', 'data_category', 'anonymization_technique',
        'acceptable_risk_level', 'is_active', 'approved_by'
    ]
    list_filter = [
        'data_category', 'anonymization_technique', 'acceptable_risk_level',
        'is_active', 'validation_required', 'specialist_review_required'
    ]
    search_fields = ['policy_name', 'data_category', 'purpose']
    readonly_fields = ['created_at', 'updated_at', 'next_review_date']
    
    fieldsets = [
        ('Identificação da Política', {
            'fields': ['policy_name', 'data_category', 'purpose']
        }),
        ('Especificações Técnicas', {
            'fields': [
                'anonymization_technique', 'k_value', 'l_value'
            ]
        }),
        ('Avaliação de Risco', {
            'fields': [
                'acceptable_risk_level', 'risk_assessment_method'
            ]
        }),
        ('Detalhes de Implementação', {
            'fields': [
                'fields_to_anonymize', 'anonymization_rules'
            ]
        }),
        ('Requisitos de Validação', {
            'fields': [
                'validation_required', 'validation_method', 
                'specialist_review_required'
            ]
        }),
        ('Conformidade Legal', {
            'fields': [
                'legal_basis_for_retention', 'anonymized_data_purpose',
                'anonymized_retention_period'
            ]
        }),
        ('Controle de Qualidade', {
            'fields': [
                're_identification_test_results', 'effectiveness_score'
            ]
        }),
        ('Aprovação e Revisão', {
            'fields': [
                'approved_by', 'approved_at', 'specialist_reviewed_by',
                'specialist_reviewed_at', 'next_review_date', 
                'review_frequency_months'
            ]
        }),
        ('Status', {
            'fields': ['is_active']
        }),
        ('Metadados', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(SecurityIncident)
class SecurityIncidentAdmin(admin.ModelAdmin):
    list_display = [
        'incident_id', 'title', 'incident_type', 'severity', 'status',
        'detected_at', 'anpd_required', 'subject_required', 'overdue_status'
    ]
    list_filter = [
        'incident_type', 'severity', 'status', 'risk_level',
        'anpd_notification_required', 'data_subject_notification_required',
        'detected_at'
    ]
    search_fields = ['incident_id', 'title', 'description']
    readonly_fields = ['incident_id', 'uuid', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['incident_id', 'uuid', 'title', 'incident_type']
        }),
        ('Classificação', {
            'fields': ['severity', 'status', 'risk_level']
        }),
        ('Detecção', {
            'fields': [
                'detected_at', 'detected_by', 'detection_method',
                'description', 'initial_assessment'
            ]
        }),
        ('Impacto', {
            'fields': [
                'affected_systems', 'affected_data_categories',
                'estimated_records_affected', 'potential_impact'
            ]
        }),
        ('Equipe de Resposta', {
            'fields': ['incident_commander', 'response_team']
        }),
        ('Cronologia', {
            'fields': [
                'containment_at', 'eradication_at', 'recovery_at', 'resolution_at'
            ]
        }),
        ('Notificações', {
            'fields': [
                'anpd_notification_required', 'anpd_notification_deadline',
                'data_subject_notification_required', 'subject_notification_deadline'
            ]
        }),
        ('Avaliação de Risco', {
            'fields': ['risk_assessment_notes']
        })
    ]
    
    def anpd_required(self, obj):
        if obj.anpd_notification_required:
            if obj.is_anpd_notification_overdue():
                return format_html('<span style="color: red;">⚠️ Overdue</span>')
            return format_html('<span style="color: orange;">📋 Required</span>')
        return '❌'
    anpd_required.short_description = 'ANPD'
    
    def subject_required(self, obj):
        if obj.data_subject_notification_required:
            if obj.is_subject_notification_overdue():
                return format_html('<span style="color: red;">⚠️ Overdue</span>')
            return format_html('<span style="color: orange;">📧 Required</span>')
        return '❌'
    subject_required.short_description = 'Subjects'
    
    def overdue_status(self, obj):
        overdue_items = []
        if obj.is_anpd_notification_overdue():
            overdue_items.append('ANPD')
        if obj.is_subject_notification_overdue():
            overdue_items.append('Subjects')
        
        if overdue_items:
            return format_html('<span style="color: red; font-weight: bold;">🚨 {}</span>', ', '.join(overdue_items))
        return '✓'
    overdue_status.short_description = 'Status'
    
    actions = ['create_notifications', 'escalate_severity']
    
    def create_notifications(self, request, queryset):
        from apps.compliance.services.breach_notification import BreachNotificationService
        
        notification_service = BreachNotificationService()
        total_notifications = 0
        
        for incident in queryset:
            notifications = notification_service.process_notification_requirements(incident)
            total_notifications += len(notifications)
        
        self.message_user(request, f'{total_notifications} notifications created for {queryset.count()} incidents.')
    create_notifications.short_description = 'Create required notifications'
    
    def escalate_severity(self, request, queryset):
        from apps.compliance.services.breach_detection import BreachDetectionService
        
        detection_service = BreachDetectionService()
        escalated = 0
        
        for incident in queryset:
            if incident.severity != 'critical':
                detection_service.escalate_incident(incident, "Manual escalation from admin")
                escalated += 1
        
        self.message_user(request, f'{escalated} incidents escalated.')
    escalate_severity.short_description = 'Escalate severity'


@admin.register(IncidentAction)
class IncidentActionAdmin(admin.ModelAdmin):
    list_display = ['incident', 'action_type', 'title', 'performed_by', 'performed_at', 'completed']
    list_filter = ['action_type', 'completed', 'performed_at']
    search_fields = ['incident__incident_id', 'title', 'description']


@admin.register(BreachNotification)
class BreachNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'notification_id', 'incident', 'notification_type', 'recipient_name',
        'delivery_method', 'status', 'scheduled_at', 'is_overdue'
    ]
    list_filter = ['notification_type', 'delivery_method', 'status', 'scheduled_at']
    search_fields = ['notification_id', 'incident__incident_id', 'recipient_name', 'subject']
    readonly_fields = ['notification_id', 'created_at', 'updated_at']
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    actions = ['send_notifications']
    
    def send_notifications(self, request, queryset):
        from apps.compliance.services.breach_notification import BreachNotificationService
        
        notification_service = BreachNotificationService()
        sent = 0
        
        for notification in queryset.filter(status='pending'):
            if notification_service.send_notification(notification):
                sent += 1
        
        self.message_user(request, f'{sent} notifications sent successfully.')
    send_notifications.short_description = 'Send selected notifications'


@admin.register(IncidentEvidence)
class IncidentEvidenceAdmin(admin.ModelAdmin):
    list_display = ['incident', 'evidence_type', 'name', 'collected_by', 'collected_at', 'integrity_verified']
    list_filter = ['evidence_type', 'integrity_verified', 'collected_at']
    search_fields = ['incident__incident_id', 'name', 'description']
    readonly_fields = ['file_hash', 'file_size']
