from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()


class DataProcessingPurpose(models.Model):
    """Documents legal basis for data processing activities - LGPD Article 37"""
    
    PURPOSE_CHOICES = [
        ('medical_care', 'Prestação de cuidados médicos'),
        ('legal_obligation', 'Cumprimento de obrigação legal'),
        ('legitimate_interest', 'Interesse legítimo'),
        ('consent', 'Consentimento do titular'),
        ('vital_interest', 'Proteção da vida'),
    ]
    
    LEGAL_BASIS_CHOICES = [
        # Article 7 - General personal data
        ('art7_i', 'Art. 7º, I - Consentimento do titular'),
        ('art7_ii', 'Art. 7º, II - Cumprimento de obrigação legal ou regulatória'),
        ('art7_iii', 'Art. 7º, III - Execução de políticas públicas'),
        ('art7_iv', 'Art. 7º, IV - Realização de estudos por órgão de pesquisa'),
        ('art7_v', 'Art. 7º, V - Execução de contrato'),
        ('art7_vi', 'Art. 7º, VI - Exercício regular de direitos (interesse legítimo)'),
        ('art7_vii', 'Art. 7º, VII - Proteção da vida ou incolumidade física'),
        ('art7_viii', 'Art. 7º, VIII - Tutela da saúde'),
        ('art7_ix', 'Art. 7º, IX - Interesse legítimo do controlador'),
        ('art7_x', 'Art. 7º, X - Proteção do crédito'),
        
        # Article 11 - Sensitive personal data (health)
        ('art11_ii_a', 'Art. 11º, II, a - Procedimentos médicos/saúde'),
        ('art11_ii_b', 'Art. 11º, II, b - Saúde pública'),
        ('art11_ii_c', 'Art. 11º, II, c - Estudos por órgão de pesquisa'),
        ('art11_ii_d', 'Art. 11º, II, d - Exercício regular de direitos'),
        ('art11_ii_e', 'Art. 11º, II, e - Proteção da vida'),
        ('art11_ii_f', 'Art. 11º, II, f - Tutela da saúde'),
        ('art11_ii_g', 'Art. 11º, II, g - Garantia da prevenção à fraude'),
    ]
    
    DATA_CATEGORY_CHOICES = [
        ('patient_identification', 'Identificação do Paciente'),
        ('patient_contact', 'Contato do Paciente'),
        ('patient_medical_history', 'Histórico Médico'),
        ('patient_current_treatment', 'Tratamento Atual'),
        ('patient_diagnostic_data', 'Dados Diagnósticos'),
        ('staff_identification', 'Identificação da Equipe'),
        ('staff_professional', 'Dados Profissionais'),
        ('system_audit', 'Auditoria do Sistema'),
        ('communication_logs', 'Logs de Comunicação'),
    ]
    
    # Core fields
    data_category = models.CharField(max_length=50, choices=DATA_CATEGORY_CHOICES)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    legal_basis = models.CharField(max_length=20, choices=LEGAL_BASIS_CHOICES)
    
    # Detailed documentation
    description = models.TextField(help_text="Descrição detalhada do processamento")
    data_fields_included = models.TextField(help_text="Campos de dados incluídos (JSON)")
    processing_activities = models.TextField(help_text="Atividades de processamento realizadas")
    
    # Recipients and sharing
    data_recipients = models.TextField(blank=True, help_text="Quem recebe os dados")
    international_transfers = models.BooleanField(default=False)
    transfer_safeguards = models.TextField(blank=True, help_text="Salvaguardas para transferências")
    
    # Retention and security
    retention_period_days = models.IntegerField()
    retention_criteria = models.TextField(help_text="Critérios para retenção")
    security_measures = models.TextField(help_text="Medidas de segurança implementadas")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Finalidade de Processamento de Dados"
        verbose_name_plural = "Finalidades de Processamento de Dados"
        ordering = ['data_category', 'purpose']
    
    def __str__(self):
        return f"{self.get_data_category_display()} - {self.get_purpose_display()}"


class LGPDComplianceSettings(models.Model):
    """Global LGPD compliance configuration"""
    
    # Data Protection Officer
    dpo_name = models.CharField(max_length=200, verbose_name="Nome do DPO/Responsável")
    dpo_email = models.EmailField(verbose_name="Email do DPO")
    dpo_phone = models.CharField(max_length=20, verbose_name="Telefone do DPO")
    
    # Organization details
    controller_name = models.CharField(max_length=200, verbose_name="Nome do Controlador")
    controller_address = models.TextField(verbose_name="Endereço do Controlador")
    controller_cnpj = models.CharField(max_length=18, verbose_name="CNPJ")
    
    # Breach notification settings
    anpd_notification_threshold = models.IntegerField(
        default=100, 
        verbose_name="Limite para notificação ANPD (nº pacientes)"
    )
    breach_notification_email = models.EmailField(verbose_name="Email para notificações de incidente")
    
    # Retention settings
    default_retention_days = models.IntegerField(
        default=7300,  # 20 years
        verbose_name="Período de retenção padrão (dias)"
    )
    deletion_warning_days = models.IntegerField(
        default=180,  # 6 months
        verbose_name="Aviso antes da exclusão (dias)"
    )
    
    # Privacy policy
    privacy_policy_version = models.CharField(max_length=10, default="1.0")
    privacy_policy_last_updated = models.DateField(auto_now=True)
    
    # Breach detection thresholds (Architectural Suggestion #4)
    breach_detection_failed_login_threshold = models.IntegerField(
        default=10,
        verbose_name="Limite de tentativas de login falhadas"
    )
    breach_detection_bulk_access_threshold = models.IntegerField(
        default=50,
        verbose_name="Limite de acesso em massa a registros"
    )
    breach_detection_off_hours_threshold = models.IntegerField(
        default=5,
        verbose_name="Limite de atividade fora do horário"
    )
    breach_detection_geographic_anomaly_km = models.IntegerField(
        default=100,
        verbose_name="Limite de distância para anomalia geográfica (km)"
    )
    breach_detection_data_export_threshold = models.IntegerField(
        default=100,
        verbose_name="Limite de exportação de dados"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração de Conformidade LGPD"
        verbose_name_plural = "Configurações de Conformidade LGPD"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings record exists
        if not self.pk and LGPDComplianceSettings.objects.exists():
            raise ValueError("Só pode existir uma configuração LGPD")
        super().save(*args, **kwargs)


class PatientDataRequest(models.Model):
    """Handles patient data rights requests - LGPD Article 18"""

    REQUEST_TYPES = [
        ('access', 'Acesso aos dados (Art. 18, I e II)'),
        ('correction', 'Correção de dados (Art. 18, III)'),
        ('deletion', 'Exclusão de dados (Art. 18, IV)'),
        ('portability', 'Portabilidade de dados (Art. 18, V)'),
        ('objection', 'Oposição ao tratamento (Art. 18, § 2º)'),
        ('consent_revocation', 'Revogação de Consentimento (Art. 8, § 5º / Art. 18, IX)'),
        ('consent_update', 'Atualização de Consentimento'),
        ('information', 'Informações sobre compartilhamento (Art. 18, VII)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('under_review', 'Em análise'),
        ('identity_verification', 'Verificação de identidade'),
        ('approved', 'Aprovado'),
        ('in_progress', 'Em andamento'),
        ('completed', 'Concluído'),
        ('rejected', 'Rejeitado'),
        ('cancelled', 'Cancelado'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    # Request identification
    request_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='data_requests', null=True, blank=True)

    # Request details
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    description = models.TextField(verbose_name="Descrição da solicitação")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')

    # Requester information (may be different from patient)
    requester_name = models.CharField(max_length=200, verbose_name="Nome do solicitante")
    requester_email = models.EmailField(verbose_name="Email para contato")
    requester_phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    requester_relationship = models.CharField(
        max_length=50,
        choices=[
            ('self', 'Próprio paciente'),
            ('parent', 'Pai/Mãe'),
            ('guardian', 'Responsável legal'),
            ('attorney', 'Procurador'),
            ('heir', 'Herdeiro'),
        ],
        default='self',
        verbose_name="Relação com o paciente"
    )

    # Patient identification for matching
    patient_name_provided = models.CharField(max_length=200, verbose_name="Nome do paciente informado")
    patient_cpf_provided = models.CharField(max_length=14, blank=True, verbose_name="CPF informado")
    patient_birth_date_provided = models.DateField(null=True, blank=True, verbose_name="Data nascimento informada")
    additional_identifiers = models.TextField(blank=True, verbose_name="Outros identificadores")

    # Supporting documentation (scanned/uploaded by staff during in-person verification)
    identity_document = models.FileField(
        upload_to='lgpd/identity_docs/',
        null=True,
        blank=True,
        verbose_name="Documento de identidade (digitalizado pela equipe)"
    )
    authorization_document = models.FileField(
        upload_to='lgpd/authorization_docs/',
        null=True,
        blank=True,
        verbose_name="Procuração/autorização (se aplicável)"
    )

    # Processing details
    requested_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(editable=False)  # Auto-calculated: 15 days from request

    # Staff processing (all requests created and managed by staff)
    created_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_data_requests',
        verbose_name="Criado por (funcionário)"
    )
    assigned_to = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_data_requests',
        verbose_name="Responsável pelo atendimento"
    )
    reviewed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_data_requests',
        verbose_name="Revisado por"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Response details
    response_notes = models.TextField(blank=True, verbose_name="Notas da resposta")
    rejection_reason = models.TextField(blank=True, verbose_name="Motivo da rejeição")
    response_sent_at = models.DateTimeField(null=True, blank=True)

    # Files and data
    response_file = models.FileField(
        upload_to='lgpd/responses/',
        null=True,
        blank=True,
        verbose_name="Arquivo de resposta"
    )
    data_export_format = models.CharField(
        max_length=10,
        choices=[('pdf', 'PDF'), ('json', 'JSON'), ('csv', 'CSV')],
        default='pdf',
        verbose_name="Formato de exportação"
    )

    # Compliance tracking
    legal_basis_for_rejection = models.CharField(max_length=100, blank=True)
    anpd_notification_sent = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Solicitação de Direitos do Titular"
        verbose_name_plural = "Solicitações de Direitos dos Titulares"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['patient', 'request_type']),
            models.Index(fields=['requester_email', 'requested_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = self.generate_request_id()
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=15)
        super().save(*args, **kwargs)

    def generate_request_id(self):
        """Generate unique request ID: REQ-YYYYMMDD-XXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        sequence = PatientDataRequest.objects.filter(
            request_id__startswith=f'REQ-{date_str}'
        ).count() + 1
        return f'REQ-{date_str}-{sequence:04d}'

    def is_overdue(self):
        """Check if request is overdue (LGPD requires response within reasonable time)"""
        return timezone.now() > self.due_date and self.status not in ['completed', 'rejected', 'cancelled']

    def days_remaining(self):
        """Days remaining to comply with request"""
        if self.status in ['completed', 'rejected', 'cancelled']:
            return 0
        remaining = (self.due_date - timezone.now()).days
        return max(0, remaining)

    def __str__(self):
        return f"{self.request_id} - {self.get_request_type_display()} - {self.requester_name}"


class DataCorrectionDetail(models.Model):
    """Detailed correction requests for specific data fields"""

    request = models.ForeignKey(PatientDataRequest, on_delete=models.CASCADE, related_name='correction_details')
    field_name = models.CharField(max_length=100, verbose_name="Campo a corrigir")
    current_value = models.TextField(verbose_name="Valor atual")
    requested_value = models.TextField(verbose_name="Valor solicitado")
    justification = models.TextField(verbose_name="Justificativa para correção")

    # Staff review
    approved = models.BooleanField(null=True, blank=True)
    review_notes = models.TextField(blank=True, verbose_name="Notas da revisão")
    reviewed_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Implementation
    correction_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_corrections'
    )

    class Meta:
        verbose_name = "Detalhe de Correção"
        verbose_name_plural = "Detalhes de Correção"
