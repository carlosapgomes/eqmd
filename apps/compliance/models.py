from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, date
import uuid
import hashlib
import json

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


class PrivacyPolicy(models.Model):
    """Manages privacy policy versions and content - LGPD Article 9"""
    
    POLICY_TYPES = [
        ('main', 'Política Principal'),
        ('staff', 'Política para Funcionários'),
        ('research', 'Política para Pesquisa'),
        ('marketing', 'Política para Marketing'),
    ]
    
    # Version control
    version = models.CharField(max_length=10)
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES, default='main')
    title = models.CharField(max_length=200)
    
    # Content
    summary = models.TextField(help_text="Resumo executivo da política")
    content_markdown = models.TextField(help_text="Conteúdo completo em Markdown")
    
    # Metadata
    effective_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=False)
    
    # Legal compliance
    legal_review_completed = models.BooleanField(default=False)
    legal_reviewer = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_policies'
    )
    legal_review_date = models.DateTimeField(null=True, blank=True)
    
    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Política de Privacidade"
        verbose_name_plural = "Políticas de Privacidade"
        ordering = ['-effective_date', '-version']
        unique_together = ['version', 'policy_type']
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate other policies of same type
            PrivacyPolicy.objects.filter(
                policy_type=self.policy_type,
                is_active=True
            ).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('privacy_policy_detail', kwargs={'policy_type': self.policy_type})
    
    def __str__(self):
        return f"{self.title} v{self.version}"


class DataProcessingNotice(models.Model):
    """Data processing notices for specific activities - LGPD Article 9"""
    
    NOTICE_CONTEXTS = [
        ('patient_registration', 'Cadastro de Paciente'),
        ('medical_consultation', 'Consulta Médica'),
        ('emergency_treatment', 'Atendimento de Emergência'),
        ('staff_onboarding', 'Integração de Funcionário'),
        ('research_participation', 'Participação em Pesquisa'),
        ('photo_video_capture', 'Captura de Foto/Vídeo'),
        ('prescription_management', 'Gestão de Prescrições'),
    ]
    
    # Identification
    notice_id = models.CharField(max_length=50, unique=True)
    context = models.CharField(max_length=30, choices=NOTICE_CONTEXTS)
    title = models.CharField(max_length=200)
    
    # Content
    purpose_description = models.TextField(verbose_name="Descrição da finalidade")
    data_categories = models.TextField(verbose_name="Categorias de dados coletados")
    legal_basis = models.CharField(max_length=100, verbose_name="Base legal")
    retention_period = models.CharField(max_length=200, verbose_name="Período de retenção")
    recipients = models.TextField(verbose_name="Destinatários dos dados")
    
    # Rights information
    rights_summary = models.TextField(verbose_name="Resumo dos direitos do titular")
    contact_info = models.TextField(verbose_name="Informações de contato DPO")
    
    # Display settings
    display_format = models.CharField(
        max_length=20,
        choices=[
            ('modal', 'Modal/Pop-up'),
            ('inline', 'Integrado na página'),
            ('banner', 'Banner de notificação'),
            ('pdf', 'Documento PDF'),
        ],
        default='modal'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Aviso de Processamento de Dados"
        verbose_name_plural = "Avisos de Processamento de Dados"
        ordering = ['context', 'title']
    
    def __str__(self):
        return f"{self.get_context_display()} - {self.title}"


class ConsentRecord(models.Model):
    """Records consent given by data subjects - LGPD Article 8"""
    
    CONSENT_TYPES = [
        ('data_processing', 'Processamento de Dados Gerais'),
        ('medical_treatment', 'Tratamento Médico'),
        ('photo_video', 'Captura de Foto/Vídeo'),
        ('research', 'Pesquisa Médica'),
        ('marketing', 'Comunicações de Marketing'),
        ('data_sharing', 'Compartilhamento de Dados'),
        ('hospital_consent', 'Consentimento Hospitalar'),
    ]
    
    CONSENT_STATUS = [
        ('granted', 'Consentimento Concedido'),
        ('denied', 'Consentimento Negado'),
        ('withdrawn', 'Consentimento Retirado'),
        ('expired', 'Consentimento Expirado'),
    ]
    
    CONSENT_SOURCE = [
        ('direct', 'Consentimento Direto'),
        ('hospital_form', 'Formulário Hospitalar'),
        ('supplementary', 'Consentimento Suplementar'),
    ]
    
    # Consent identification
    consent_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Subject information
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(max_length=30, choices=CONSENT_TYPES)
    
    # Consent details
    purpose_description = models.TextField(verbose_name="Finalidade específica")
    data_categories = models.TextField(verbose_name="Categorias de dados envolvidos")
    processing_activities = models.TextField(verbose_name="Atividades de processamento")
    
    # Consent status
    status = models.CharField(max_length=20, choices=CONSENT_STATUS, default='granted')
    granted_at = models.DateTimeField()
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    
    # Consent context
    granted_by = models.CharField(max_length=200, verbose_name="Concedido por")  # Patient name or guardian
    granted_by_relationship = models.CharField(
        max_length=50,
        choices=[
            ('self', 'Próprio paciente'),
            ('parent', 'Pai/Mãe'),
            ('guardian', 'Responsável legal'),
            ('healthcare_proxy', 'Procurador de saúde'),
        ],
        default='self'
    )
    
    # Technical details
    consent_method = models.CharField(
        max_length=30,
        choices=[
            ('web_form', 'Formulário Web'),
            ('verbal', 'Verbal (registrado)'),
            ('paper_form', 'Formulário Físico'),
            ('electronic_signature', 'Assinatura Eletrônica'),
        ],
        default='web_form'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Legal compliance
    legal_basis = models.CharField(max_length=100)
    lawful_basis_explanation = models.TextField(verbose_name="Explicação da base legal")
    
    # Consent source tracking
    consent_source = models.CharField(
        max_length=20,
        choices=CONSENT_SOURCE,
        default='direct',
        help_text="Origem do consentimento"
    )
    
    hospital_consent_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Referência do consentimento hospitalar (número do documento)"
    )
    
    # Evidence and audit
    consent_evidence = models.FileField(
        upload_to='consent_evidence/',
        null=True,
        blank=True,
        help_text="Documento comprobatório do consentimento (PDF escaneado do hospital)"
    )
    
    hospital_consent_document = models.FileField(
        upload_to='hospital_consent/',
        null=True,
        blank=True,
        help_text="Cópia escaneada do consentimento hospitalar"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Registro de Consentimento"
        verbose_name_plural = "Registros de Consentimento"
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['patient', 'consent_type', 'status']),
            models.Index(fields=['granted_at', 'status']),
        ]
    
    def is_valid(self):
        """Check if consent is currently valid"""
        if self.status != 'granted':
            return False
        
        if self.expiration_date and timezone.now() > self.expiration_date:
            return False
            
        if self.withdrawn_at:
            return False
            
        return True
    
    def withdraw(self, withdrawn_by=None, reason=None):
        """Withdraw consent"""
        self.status = 'withdrawn'
        self.withdrawn_at = timezone.now()
        self.save()
        
        # Create withdrawal record
        ConsentWithdrawal.objects.create(
            consent_record=self,
            withdrawn_by=withdrawn_by or self.granted_by,
            reason=reason or 'Solicitação do titular'
        )
    
    def is_hospital_based(self):
        """Check if consent is based on hospital documentation"""
        return self.consent_source == 'hospital_form'
    
    def requires_supplementary_consent(self):
        """Check if additional consent is needed beyond hospital consent"""
        # Define which activities need explicit consent beyond hospital forms
        supplementary_required = ['research', 'marketing', 'photo_video']
        return self.consent_type in supplementary_required
    
    def __str__(self):
        source_indicator = "[H]" if self.is_hospital_based() else ""
        return f"{self.patient.name} - {self.get_consent_type_display()} - {self.status} {source_indicator}"


class ConsentWithdrawal(models.Model):
    """Records consent withdrawal details"""
    
    consent_record = models.OneToOneField(ConsentRecord, on_delete=models.CASCADE, related_name='withdrawal')
    withdrawn_by = models.CharField(max_length=200)
    reason = models.TextField()
    withdrawn_at = models.DateTimeField(auto_now_add=True)
    
    # Processing after withdrawal
    data_deleted = models.BooleanField(default=False)
    data_deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_evidence = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Retirada de Consentimento"
        verbose_name_plural = "Retiradas de Consentimento"


class MinorConsentRecord(models.Model):
    """Special consent handling for patients under 18 - LGPD Article 14"""
    
    patient = models.OneToOneField('patients.Patient', on_delete=models.CASCADE, related_name='minor_consent')
    
    # Patient age verification
    patient_birth_date = models.DateField()
    age_at_consent = models.IntegerField()
    is_minor = models.BooleanField(default=True)
    
    # Guardian information
    guardian_name = models.CharField(max_length=200)
    guardian_relationship = models.CharField(
        max_length=30,
        choices=[
            ('mother', 'Mãe'),
            ('father', 'Pai'),
            ('legal_guardian', 'Responsável Legal'),
            ('court_appointed', 'Designado pelo Tribunal'),
        ]
    )
    guardian_document = models.CharField(max_length=20, help_text="CPF do responsável")
    guardian_phone = models.CharField(max_length=20)
    guardian_email = models.EmailField()
    
    # Consent details
    consent_date = models.DateTimeField()
    consent_method = models.CharField(
        max_length=30,
        choices=[
            ('in_person', 'Presencial'),
            ('electronic', 'Eletrônico'),
            ('phone_verified', 'Telefone (verificado)'),
        ]
    )
    
    # Documentation
    guardian_id_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=100, blank=True)
    consent_document = models.FileField(upload_to='minor_consent/', null=True, blank=True)
    
    # Special protections
    data_sharing_restricted = models.BooleanField(default=True)
    marketing_prohibited = models.BooleanField(default=True)
    research_participation_allowed = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Consentimento de Menor"
        verbose_name_plural = "Consentimentos de Menores"
    
    def __str__(self):
        return f"Menor: {self.patient.name} - Responsável: {self.guardian_name}"


class DataRetentionPolicy(models.Model):
    """Defines retention policies for different data categories - LGPD Article 15"""
    
    DATA_CATEGORIES = [
        ('patient_identification', 'Identificação do Paciente'),
        ('patient_medical_records', 'Registros Médicos'),
        ('patient_contact_info', 'Informações de Contato'),
        ('staff_professional_data', 'Dados Profissionais da Equipe'),
        ('audit_logs', 'Logs de Auditoria'),
        ('consent_records', 'Registros de Consentimento'),
        ('media_files', 'Arquivos de Mídia'),
        ('communication_logs', 'Logs de Comunicação'),
        ('emergency_contacts', 'Contatos de Emergência'),
    ]
    
    RETENTION_BASIS = [
        ('legal_obligation', 'Obrigação Legal'),
        ('medical_requirement', 'Exigência Médica'),
        ('consent_duration', 'Duração do Consentimento'),
        ('business_necessity', 'Necessidade Operacional'),
        ('statute_limitation', 'Prazo Prescricional'),
    ]
    
    # Policy identification
    policy_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    data_category = models.CharField(max_length=50, choices=DATA_CATEGORIES)
    
    # Retention rules
    retention_period_days = models.IntegerField(help_text="Período de retenção em dias")
    retention_basis = models.CharField(max_length=30, choices=RETENTION_BASIS)
    legal_reference = models.CharField(max_length=200, help_text="Referência legal (ex: CFM 1.821/2007)")
    
    # Grace periods and warnings
    warning_period_days = models.IntegerField(
        default=180,
        help_text="Dias antes da exclusão para enviar aviso"
    )
    grace_period_days = models.IntegerField(
        default=30,
        help_text="Período de graça após vencimento"
    )
    
    # Deletion behavior
    auto_delete_enabled = models.BooleanField(default=False)
    anonymize_instead_delete = models.BooleanField(default=False)
    require_manual_approval = models.BooleanField(default=True)
    
    # Exceptions and holds
    legal_hold_exempt = models.BooleanField(default=False)
    emergency_access_required = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Política de Retenção"
        verbose_name_plural = "Políticas de Retenção"
        ordering = ['data_category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.retention_period_days} dias)"


class DataRetentionSchedule(models.Model):
    """Tracks retention schedules for specific data records"""
    
    # Record identification
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()  # UUID of the data record
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Retention details
    retention_policy = models.ForeignKey(DataRetentionPolicy, on_delete=models.CASCADE)
    data_creation_date = models.DateTimeField()
    last_activity_date = models.DateTimeField(auto_now=True)
    
    # Calculated dates
    retention_end_date = models.DateField()
    warning_date = models.DateField()
    deletion_date = models.DateField()
    
    # Status tracking
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('warning_sent', 'Aviso Enviado'),
        ('grace_period', 'Período de Graça'),
        ('scheduled_deletion', 'Agendado para Exclusão'),
        ('legal_hold', 'Retenção Legal'),
        ('deleted', 'Excluído'),
        ('anonymized', 'Anonimizado'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Warning and deletion tracking
    warning_sent_at = models.DateTimeField(null=True, blank=True)
    deletion_approved_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_deletions'
    )
    deletion_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Legal holds
    legal_hold_reason = models.TextField(blank=True)
    legal_hold_applied_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_legal_holds'
    )
    legal_hold_applied_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cronograma de Retenção"
        verbose_name_plural = "Cronogramas de Retenção"
        ordering = ['retention_end_date']
        indexes = [
            models.Index(fields=['retention_end_date', 'status']),
            models.Index(fields=['warning_date', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        unique_together = ['content_type', 'object_id']
    
    def save(self, *args, **kwargs):
        if not self.retention_end_date:
            self.calculate_dates()
        super().save(*args, **kwargs)
    
    def calculate_dates(self):
        """Calculate retention and deletion dates"""
        base_date = self.last_activity_date.date() if self.last_activity_date else self.data_creation_date.date()
        
        self.retention_end_date = base_date + timedelta(days=self.retention_policy.retention_period_days)
        self.warning_date = self.retention_end_date - timedelta(days=self.retention_policy.warning_period_days)
        self.deletion_date = self.retention_end_date + timedelta(days=self.retention_policy.grace_period_days)
    
    def is_eligible_for_warning(self):
        """Check if warning should be sent"""
        return (
            date.today() >= self.warning_date and 
            self.status == 'active' and 
            not self.warning_sent_at
        )
    
    def is_eligible_for_deletion(self):
        """Check if data is eligible for deletion"""
        return (
            date.today() >= self.deletion_date and 
            self.status in ['warning_sent', 'grace_period'] and
            not self.legal_hold_applied_at
        )
    
    def apply_legal_hold(self, user, reason):
        """Apply legal hold to prevent deletion"""
        self.status = 'legal_hold'
        self.legal_hold_reason = reason
        self.legal_hold_applied_by = user
        self.legal_hold_applied_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.content_object} - {self.retention_policy.name}"


class DataDeletionLog(models.Model):
    """Audit log for data deletions - compliance evidence"""
    
    # Deletion identification
    deletion_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Original record information
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    original_object_id = models.UUIDField()
    original_object_representation = models.TextField()  # String representation before deletion
    
    # Deletion details
    deletion_type = models.CharField(
        max_length=20,
        choices=[
            ('automatic', 'Automática'),
            ('manual', 'Manual'),
            ('patient_request', 'Solicitação do Paciente'),
            ('legal_requirement', 'Exigência Legal'),
            ('anonymization', 'Anonimização'),
        ]
    )
    
    deletion_reason = models.TextField()
    retention_policy_applied = models.CharField(max_length=200)
    
    # Authorization
    authorized_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='authorized_deletions'
    )
    authorization_date = models.DateTimeField()
    
    # Execution
    executed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_deletions'
    )
    executed_at = models.DateTimeField()
    
    # Technical details
    deletion_method = models.CharField(
        max_length=30,
        choices=[
            ('soft_delete', 'Exclusão Suave'),
            ('hard_delete', 'Exclusão Completa'),
            ('anonymization', 'Anonimização'),
            ('archival', 'Arquivamento'),
        ]
    )
    
    # Verification
    verification_hash = models.CharField(max_length=64, blank=True)  # SHA-256 of deleted data
    deletion_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Related data impact
    related_records_affected = models.IntegerField(default=0)
    cascading_deletions = models.TextField(blank=True)  # JSON list of related deletions
    
    # Legal compliance
    legal_basis_for_deletion = models.CharField(max_length=200)
    compliance_notes = models.TextField(blank=True)
    
    # Recovery information (for soft deletes)
    recovery_possible = models.BooleanField(default=False)
    recovery_deadline = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Log de Exclusão de Dados"
        verbose_name_plural = "Logs de Exclusão de Dados"
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['executed_at', 'deletion_type']),
            models.Index(fields=['content_type', 'deletion_type']),
        ]
    
    def __str__(self):
        return f"{self.deletion_id} - {self.original_object_representation[:50]}"


class DataAnonymizationLog(models.Model):
    """Log for data anonymization processes"""
    
    anonymization_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Source data
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    original_object_id = models.UUIDField()
    anonymized_object_id = models.UUIDField(null=True, blank=True)  # If creating new anonymized record
    
    # Anonymization details
    anonymization_method = models.CharField(
        max_length=30,
        choices=[
            ('field_removal', 'Remoção de Campos'),
            ('field_masking', 'Mascaramento'),
            ('data_generalization', 'Generalização'),
            ('pseudonymization', 'Pseudonimização'),
            ('statistical_disclosure', 'Controle Estatístico'),
        ]
    )
    
    fields_anonymized = models.TextField()  # JSON list of fields
    anonymization_rules = models.TextField()  # JSON with anonymization rules
    
    # Quality control
    anonymization_quality_score = models.FloatField(null=True, blank=True)  # 0-1 score
    re_identification_risk = models.CharField(
        max_length=10,
        choices=[('low', 'Baixo'), ('medium', 'Médio'), ('high', 'Alto')],
        default='low'
    )
    
    # Execution details
    executed_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # Purpose and retention
    anonymization_purpose = models.CharField(
        max_length=30,
        choices=[
            ('research', 'Pesquisa'),
            ('statistics', 'Estatísticas'),
            ('quality_improvement', 'Melhoria da Qualidade'),
            ('retention_compliance', 'Conformidade de Retenção'),
        ]
    )
    
    anonymized_data_retention = models.IntegerField(help_text="Dias para manter dados anonimizados")
    
    class Meta:
        verbose_name = "Log de Anonimização"
        verbose_name_plural = "Logs de Anonimização"
        ordering = ['-executed_at']


class AnonymizationPolicy(models.Model):
    """Formal anonymization policy for data lifecycle management - Architectural Suggestion #2"""
    
    ANONYMIZATION_TECHNIQUES = [
        ('k_anonymity', 'K-Anonimato'),
        ('l_diversity', 'L-Diversidade'),
        ('t_closeness', 'T-Proximidade'),
        ('differential_privacy', 'Privacidade Diferencial'),
        ('data_masking', 'Mascaramento de Dados'),
        ('generalization', 'Generalização'),
        ('suppression', 'Supressão'),
        ('noise_addition', 'Adição de Ruído'),
        ('pseudonymization', 'Pseudonimização'),
    ]
    
    RISK_LEVELS = [
        ('very_low', 'Muito Baixo (< 1%)'),
        ('low', 'Baixo (1-5%)'),
        ('medium', 'Médio (5-15%)'),
        ('high', 'Alto (15-30%)'),
        ('very_high', 'Muito Alto (> 30%)'),
    ]
    
    # Policy identification
    policy_name = models.CharField(max_length=200)
    data_category = models.CharField(max_length=50)
    purpose = models.CharField(max_length=200, help_text="Finalidade da anonimização", default='')
    
    # Technical specifications
    anonymization_technique = models.CharField(max_length=30, choices=ANONYMIZATION_TECHNIQUES)
    k_value = models.IntegerField(null=True, blank=True, help_text="Valor K para k-anonimato")
    l_value = models.IntegerField(null=True, blank=True, help_text="Valor L para l-diversidade")
    
    # Risk assessment
    acceptable_risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='low')
    risk_assessment_method = models.TextField(help_text="Método de avaliação de risco de reidentificação", default='')
    
    # Implementation details
    fields_to_anonymize = models.TextField(help_text="JSON list of fields to anonymize", default='[]')
    anonymization_rules = models.TextField(help_text="JSON with specific anonymization rules", default='{}')
    
    # Validation requirements
    validation_required = models.BooleanField(default=True)
    validation_method = models.TextField(help_text="Método de validação da eficácia da anonimização", default='')
    specialist_review_required = models.BooleanField(default=True)
    
    # Legal compliance
    legal_basis_for_retention = models.TextField(help_text="Base legal para manter dados anonimizados", default='')
    anonymized_data_purpose = models.TextField(help_text="Finalidade dos dados anonimizados", default='')
    anonymized_retention_period = models.IntegerField(help_text="Período de retenção em dias", default=1095)
    
    # Quality control
    re_identification_test_results = models.TextField(blank=True)
    effectiveness_score = models.FloatField(null=True, blank=True, help_text="Score de eficácia 0-100")
    
    # Approval and review
    approved_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_anonymization_policies'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    specialist_reviewed_by = models.CharField(max_length=200, blank=True)
    specialist_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Review cycle
    next_review_date = models.DateField()
    review_frequency_months = models.IntegerField(default=12)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)  # Requires approval to activate
    
    class Meta:
        verbose_name = "Política de Anonimização"
        verbose_name_plural = "Políticas de Anonimização"
        ordering = ['data_category', 'policy_name']
    
    def calculate_next_review_date(self):
        """Calculate next review date"""
        if self.approved_at:
            return self.approved_at.date() + timedelta(days=self.review_frequency_months * 30)
        return timezone.now().date() + timedelta(days=self.review_frequency_months * 30)
    
    def save(self, *args, **kwargs):
        if not self.next_review_date:
            self.next_review_date = self.calculate_next_review_date()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.policy_name} - {self.data_category}"


class SecurityIncident(models.Model):
    """Security incidents and data breaches - LGPD Article 48"""
    
    INCIDENT_TYPES = [
        ('data_breach', 'Violação de Dados'),
        ('unauthorized_access', 'Acesso Não Autorizado'),
        ('data_loss', 'Perda de Dados'),
        ('system_intrusion', 'Intrusão no Sistema'),
        ('malware_attack', 'Ataque de Malware'),
        ('phishing_attack', 'Ataque de Phishing'),
        ('insider_threat', 'Ameaça Interna'),
        ('physical_security', 'Segurança Física'),
        ('data_corruption', 'Corrupção de Dados'),
        ('service_disruption', 'Interrupção de Serviço'),
        ('configuration_error', 'Erro de Configuração'),
        ('human_error', 'Erro Humano'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    STATUS_CHOICES = [
        ('detected', 'Detectado'),
        ('investigating', 'Em Investigação'),
        ('contained', 'Contido'),
        ('eradicated', 'Erradicado'),
        ('recovering', 'Em Recuperação'),
        ('resolved', 'Resolvido'),
        ('closed', 'Fechado'),
    ]
    
    RISK_LEVELS = [
        ('minimal', 'Mínimo'),
        ('low', 'Baixo'),
        ('moderate', 'Moderado'),
        ('high', 'Alto'),
        ('severe', 'Severo'),
    ]
    
    # Incident identification
    incident_id = models.CharField(max_length=20, unique=True, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Basic incident information
    title = models.CharField(max_length=200)
    incident_type = models.CharField(max_length=30, choices=INCIDENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='detected')
    
    # Detection details
    detected_at = models.DateTimeField()
    detected_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detected_incidents'
    )
    detection_method = models.CharField(
        max_length=50,
        choices=[
            ('automated_monitoring', 'Monitoramento Automatizado'),
            ('user_report', 'Relatório de Usuário'),
            ('security_audit', 'Auditoria de Segurança'),
            ('external_notification', 'Notificação Externa'),
            ('routine_inspection', 'Inspeção de Rotina'),
            ('third_party_alert', 'Alerta de Terceiros'),
        ]
    )
    
    # Incident description
    description = models.TextField()
    initial_assessment = models.TextField(blank=True)
    
    # Affected systems and data
    affected_systems = models.TextField(
        help_text="JSON list of affected systems",
        default=list
    )
    affected_data_categories = models.TextField(
        help_text="JSON list of affected data categories",
        default=list
    )
    estimated_records_affected = models.IntegerField(default=0)
    
    # Risk assessment
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='low')
    risk_assessment_notes = models.TextField(blank=True)
    potential_impact = models.TextField(blank=True)
    
    # Response team
    incident_commander = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commanded_incidents'
    )
    response_team = models.ManyToManyField(
        'accounts.EqmdCustomUser',
        related_name='incident_responses',
        blank=True
    )
    
    # Timeline tracking
    containment_at = models.DateTimeField(null=True, blank=True)
    eradication_at = models.DateTimeField(null=True, blank=True)
    recovery_at = models.DateTimeField(null=True, blank=True)
    resolution_at = models.DateTimeField(null=True, blank=True)
    
    # Notification requirements
    anpd_notification_required = models.BooleanField(default=False)
    data_subject_notification_required = models.BooleanField(default=False)
    
    # Compliance tracking
    anpd_notification_deadline = models.DateTimeField(null=True, blank=True)
    subject_notification_deadline = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Incidente de Segurança"
        verbose_name_plural = "Incidentes de Segurança"
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['detected_at', 'incident_type']),
            models.Index(fields=['anpd_notification_required', 'anpd_notification_deadline']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.incident_id:
            self.incident_id = self.generate_incident_id()
        
        # Auto-calculate notification deadlines
        if self.anpd_notification_required and not self.anpd_notification_deadline:
            # LGPD requires "reasonable time" - we use 72 hours as best practice
            self.anpd_notification_deadline = self.detected_at + timedelta(hours=72)
        
        if self.data_subject_notification_required and not self.subject_notification_deadline:
            # Give more time for subject notification after investigation
            self.subject_notification_deadline = self.detected_at + timedelta(hours=120)  # 5 days
        
        super().save(*args, **kwargs)
    
    def generate_incident_id(self):
        """Generate unique incident ID: INC-YYYYMMDD-XXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        sequence = SecurityIncident.objects.filter(
            incident_id__startswith=f'INC-{date_str}'
        ).count() + 1
        return f'INC-{date_str}-{sequence:04d}'
    
    def is_anpd_notification_overdue(self):
        """Check if ANPD notification is overdue"""
        if not self.anpd_notification_required or not self.anpd_notification_deadline:
            return False
        return timezone.now() > self.anpd_notification_deadline
    
    def is_subject_notification_overdue(self):
        """Check if subject notification is overdue"""
        if not self.data_subject_notification_required or not self.subject_notification_deadline:
            return False
        return timezone.now() > self.subject_notification_deadline
    
    def calculate_response_time(self):
        """Calculate incident response time metrics"""
        if not self.resolution_at:
            return None
        
        return {
            'detection_to_containment': (self.containment_at - self.detected_at).total_seconds() / 3600 if self.containment_at else None,
            'detection_to_resolution': (self.resolution_at - self.detected_at).total_seconds() / 3600,
            'containment_to_resolution': (self.resolution_at - self.containment_at).total_seconds() / 3600 if self.containment_at else None,
        }
    
    def __str__(self):
        return f"{self.incident_id} - {self.title}"


class IncidentAction(models.Model):
    """Track actions taken during incident response"""
    
    ACTION_TYPES = [
        ('investigation', 'Investigação'),
        ('containment', 'Contenção'),
        ('eradication', 'Erradicação'),
        ('recovery', 'Recuperação'),
        ('communication', 'Comunicação'),
        ('documentation', 'Documentação'),
        ('evidence_collection', 'Coleta de Evidências'),
        ('system_change', 'Alteração de Sistema'),
        ('notification', 'Notificação'),
        ('training', 'Treinamento'),
    ]
    
    incident = models.ForeignKey(SecurityIncident, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Execution details
    performed_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField()
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    # Status and results
    completed = models.BooleanField(default=False)
    results = models.TextField(blank=True)
    evidence_collected = models.TextField(blank=True)
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_deadline = models.DateTimeField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Ação de Resposta"
        verbose_name_plural = "Ações de Resposta"
        ordering = ['performed_at']
    
    def __str__(self):
        return f"{self.incident.incident_id} - {self.title}"


class BreachNotification(models.Model):
    """Track breach notifications to authorities and data subjects"""
    
    NOTIFICATION_TYPES = [
        ('anpd', 'ANPD (Autoridade Nacional)'),
        ('data_subject', 'Titular dos Dados'),
        ('regulatory_authority', 'Autoridade Regulatória'),
        ('law_enforcement', 'Autoridades Policiais'),
        ('business_partner', 'Parceiro de Negócios'),
        ('media', 'Mídia'),
        ('public_notice', 'Aviso Público'),
    ]
    
    NOTIFICATION_STATUS = [
        ('pending', 'Pendente'),
        ('drafted', 'Rascunho Preparado'),
        ('reviewed', 'Revisado'),
        ('sent', 'Enviado'),
        ('acknowledged', 'Confirmado'),
        ('failed', 'Falhou'),
    ]
    
    DELIVERY_METHODS = [
        ('email', 'Email'),
        ('postal_mail', 'Correio'),
        ('web_portal', 'Portal Web'),
        ('phone_call', 'Ligação Telefônica'),
        ('in_person', 'Presencial'),
        ('public_notice', 'Aviso Público'),
        ('media_release', 'Comunicado à Imprensa'),
    ]
    
    # Notification identification
    notification_id = models.CharField(max_length=20, unique=True, editable=False)
    incident = models.ForeignKey(SecurityIncident, on_delete=models.CASCADE, related_name='notifications')
    
    # Notification details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    recipient_name = models.CharField(max_length=200)
    recipient_contact = models.CharField(max_length=200)  # Email, phone, address
    delivery_method = models.CharField(max_length=15, choices=DELIVERY_METHODS)
    
    # Content
    subject = models.CharField(max_length=300)
    content = models.TextField()
    attachments = models.TextField(blank=True, help_text="JSON list of attachment files")
    
    # Timing
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=15, choices=NOTIFICATION_STATUS, default='pending')
    delivery_confirmation = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Legal compliance
    legal_basis = models.CharField(max_length=100)
    compliance_notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notificação de Violação"
        verbose_name_plural = "Notificações de Violação"
        ordering = ['scheduled_at']
    
    def save(self, *args, **kwargs):
        if not self.notification_id:
            self.notification_id = self.generate_notification_id()
        super().save(*args, **kwargs)
    
    def generate_notification_id(self):
        """Generate notification ID: NOT-INC-YYYYMMDD-XX"""
        date_str = timezone.now().strftime('%Y%m%d')
        incident_sequence = self.incident.notifications.count() + 1
        return f'NOT-{self.incident.incident_id}-{incident_sequence:02d}'
    
    def is_overdue(self):
        """Check if notification is overdue"""
        if self.status in ['sent', 'acknowledged']:
            return False
        return timezone.now() > self.scheduled_at
    
    def __str__(self):
        return f"{self.notification_id} - {self.get_notification_type_display()}"


class IncidentEvidence(models.Model):
    """Store evidence and artifacts related to security incidents"""
    
    EVIDENCE_TYPES = [
        ('log_file', 'Arquivo de Log'),
        ('screenshot', 'Captura de Tela'),
        ('network_capture', 'Captura de Rede'),
        ('file_sample', 'Amostra de Arquivo'),
        ('email_header', 'Cabeçalho de Email'),
        ('system_dump', 'Dump de Sistema'),
        ('database_record', 'Registro de Banco'),
        ('witness_statement', 'Declaração de Testemunha'),
        ('external_report', 'Relatório Externo'),
        ('forensic_image', 'Imagem Forense'),
    ]
    
    incident = models.ForeignKey(SecurityIncident, on_delete=models.CASCADE, related_name='evidence')
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # File storage
    evidence_file = models.FileField(upload_to='incident_evidence/', null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)  # SHA-256
    file_size = models.BigIntegerField(null=True, blank=True)
    
    # Chain of custody
    collected_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    collected_at = models.DateTimeField()
    collection_method = models.CharField(max_length=100)
    
    # Integrity
    integrity_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=100, blank=True)
    
    # Legal considerations
    attorney_client_privileged = models.BooleanField(default=False)
    retention_required = models.BooleanField(default=True)
    retention_deadline = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Evidência de Incidente"
        verbose_name_plural = "Evidências de Incidente"
        ordering = ['collected_at']
    
    def __str__(self):
        return f"{self.incident.incident_id} - {self.name}"
