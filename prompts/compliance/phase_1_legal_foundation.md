# Phase 1: Legal Foundation Implementation

**Timeline**: Week 1-2  
**Priority**: CRITICAL  
**Dependencies**: None  

## Objective

Establish the legal framework required for LGPD compliance by documenting legal basis for all data processing activities and creating the foundational compliance infrastructure.

## Legal Requirements Addressed

- **LGPD Article 7**: Legal basis for personal data processing
- **LGPD Article 11**: Legal basis for sensitive data (health records)
- **LGPD Article 37**: Record of processing activities (ROPA)

## Deliverables

1. **Legal Basis Documentation System**
2. **Data Processing Record (Registro de Atividades)**
3. **Compliance Infrastructure Models**
4. **Staff Role Definitions**

---

## Implementation Steps

### Step 1: Create Legal Basis Models

Create Django models to document and track legal basis for all data processing.

#### 1.1 Data Processing Purpose Model

**File**: `apps/compliance/models.py`

```python
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
    created_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Finalidade de Processamento de Dados"
        verbose_name_plural = "Finalidades de Processamento de Dados"
        ordering = ['data_category', 'purpose']
    
    def __str__(self):
        return f"{self.get_data_category_display()} - {self.get_purpose_display()}"
```

#### 1.2 LGPD Compliance Settings Model

**File**: `apps/compliance/models.py` (additions)

```python
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
```

### Step 2: Data Processing Documentation

#### 2.1 Create Management Command for Legal Basis Setup

**File**: `apps/compliance/management/commands/setup_legal_basis.py`

```python
from django.core.management.base import BaseCommand
from apps.compliance.models import DataProcessingPurpose
import json

class Command(BaseCommand):
    help = 'Sets up LGPD legal basis documentation for EquipeMed'
    
    def handle(self, *args, **options):
        self.stdout.write("Setting up LGPD legal basis documentation...")
        
        # Patient data processing purposes
        patient_purposes = [
            {
                'data_category': 'patient_identification',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Identificação de pacientes para prestação de cuidados médicos conforme protocolo hospitalar',
                'data_fields_included': json.dumps([
                    'nome', 'data_nascimento', 'cpf', 'cartao_sus', 'endereco', 'telefone'
                ]),
                'processing_activities': 'Coleta, armazenamento, consulta, atualização para identificação e contato',
                'data_recipients': 'Equipe médica autorizada, enfermagem, fisioterapeutas, residentes',
                'retention_period_days': 7300,  # 20 years
                'retention_criteria': '20 anos após última consulta conforme Resolução CFM 1.821/2007',
                'security_measures': 'Controle de acesso por função, auditoria completa, criptografia, UUIDs'
            },
            {
                'data_category': 'patient_medical_history',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Registro e acompanhamento do histórico médico para continuidade do tratamento',
                'data_fields_included': json.dumps([
                    'historico_medico', 'diagnosticos', 'medicamentos', 'alergias', 'procedimentos'
                ]),
                'processing_activities': 'Coleta, armazenamento, consulta, atualização, análise clínica',
                'data_recipients': 'Médicos responsáveis, equipe multidisciplinar autorizada',
                'retention_period_days': 7300,
                'retention_criteria': '20 anos após última consulta para preservação histórico médico',
                'security_measures': 'Acesso restrito a profissionais autorizados, logs de auditoria, janela de edição 24h'
            },
            {
                'data_category': 'patient_current_treatment',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Gerenciamento do tratamento atual e evolução clínica do paciente',
                'data_fields_included': json.dumps([
                    'evolucoes_diarias', 'prescricoes', 'exames', 'sinais_vitais', 'procedimentos'
                ]),
                'processing_activities': 'Registro em tempo real, consulta, atualização, compartilhamento entre equipe',
                'data_recipients': 'Equipe médica, enfermagem, especialistas consultados',
                'retention_period_days': 7300,
                'retention_criteria': '20 anos para acompanhamento longitudinal da saúde',
                'security_measures': 'Controle de acesso por setor, monitoramento de atividade suspeita'
            }
        ]
        
        # Staff data processing purposes
        staff_purposes = [
            {
                'data_category': 'staff_identification',
                'purpose': 'legal_obligation',
                'legal_basis': 'art7_ii',
                'description': 'Identificação de profissionais conforme exigências do CFM e CRM',
                'data_fields_included': json.dumps([
                    'nome', 'email', 'crm', 'especialidade', 'telefone'
                ]),
                'processing_activities': 'Cadastro, validação, consulta para identificação profissional',
                'data_recipients': 'Administração hospitalar, outros profissionais da equipe',
                'retention_period_days': 1825,  # 5 years
                'retention_criteria': '5 anos após fim do vínculo profissional para auditoria',
                'security_measures': 'Autenticação forte, controle de sessão, logs de acesso'
            },
            {
                'data_category': 'system_audit',
                'purpose': 'legitimate_interest',
                'legal_basis': 'art7_vi',
                'description': 'Auditoria de segurança e monitoramento de acesso para proteção de dados',
                'data_fields_included': json.dumps([
                    'logs_acesso', 'ip_address', 'timestamp', 'acao_realizada'
                ]),
                'processing_activities': 'Coleta automática, análise, armazenamento para auditoria',
                'data_recipients': 'Administradores de sistema, responsável pela segurança',
                'retention_period_days': 1095,  # 3 years
                'retention_criteria': '3 anos para investigação de incidentes e auditoria de segurança',
                'security_measures': 'Logs protegidos, acesso restrito, detecção de anomalias'
            }
        ]
        
        # Create all purposes
        all_purposes = patient_purposes + staff_purposes
        created_count = 0
        
        for purpose_data in all_purposes:
            obj, created = DataProcessingPurpose.objects.get_or_create(
                data_category=purpose_data['data_category'],
                purpose=purpose_data['purpose'],
                defaults=purpose_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {obj}")
            else:
                self.stdout.write(f"- Exists: {obj}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} legal basis records')
        )
```

#### 2.2 Create LGPD Settings Setup Command

**File**: `apps/core/management/commands/setup_lgpd_settings.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import LGPDComplianceSettings
from datetime import date

class Command(BaseCommand):
    help = 'Sets up initial LGPD compliance settings'
    
    def add_arguments(self, parser):
        parser.add_argument('--dpo-name', type=str, help='DPO name')
        parser.add_argument('--dpo-email', type=str, help='DPO email')
        parser.add_argument('--hospital-name', type=str, help='Hospital name')
        parser.add_argument('--cnpj', type=str, help='Hospital CNPJ')
    
    def handle(self, *args, **options):
        if LGPDComplianceSettings.objects.exists():
            self.stdout.write(self.style.WARNING('LGPD settings already exist'))
            return
        
        # Use provided values or defaults
        dpo_name = options.get('dpo_name') or '[NOME_DO_DPO]'
        dpo_email = options.get('dpo_email') or 'lgpd@hospital.com.br'
        hospital_name = options.get('hospital_name') or '[NOME_DO_HOSPITAL]'
        cnpj = options.get('cnpj') or '[CNPJ_DO_HOSPITAL]'
        
        settings = LGPDComplianceSettings.objects.create(
            dpo_name=dpo_name,
            dpo_email=dpo_email,
            dpo_phone='[TELEFONE_DPO]',
            controller_name=hospital_name,
            controller_address='[ENDEREÇO_DO_HOSPITAL]',
            controller_cnpj=cnpj,
            anpd_notification_threshold=100,
            breach_notification_email=dpo_email,
            default_retention_days=7300,  # 20 years
            deletion_warning_days=180,    # 6 months
            privacy_policy_version="1.0"
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'LGPD settings created successfully: {settings}')
        )
        self.stdout.write(
            self.style.WARNING('Remember to update placeholder values in Django admin')
        )
```

### Step 3: Database Migration

#### 3.1 Create Migration

```bash
# Create compliance app
python manage.py startapp compliance apps/compliance

# Add to INSTALLED_APPS in settings.py:
# 'apps.compliance',

# Run these commands after implementing the models
python manage.py makemigrations compliance --name "add_lgpd_compliance_models"
python manage.py migrate
```

#### 3.2 Initial Data Setup

```bash
# Set up legal basis documentation
python manage.py setup_legal_basis

# Set up LGPD settings (customize with your hospital info)
python manage.py setup_lgpd_settings \
    --dpo-name "Dr. [Nome do Responsável]" \
    --dpo-email "lgpd@[hospital].com.br" \
    --hospital-name "[Nome do Hospital]" \
    --cnpj "[CNPJ]"
```

### Step 4: Django Admin Configuration

#### 4.1 Admin Interface for Legal Basis

**File**: `apps/compliance/admin.py`

```python
from django.contrib import admin
from .models import DataProcessingPurpose, LGPDComplianceSettings

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
        })
    ]
    
    def has_add_permission(self, request):
        # Only allow one settings record
        return not LGPDComplianceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
```

### Step 5: Documentation Templates

#### 5.1 Create Data Processing Record Template

**File**: `prompts/compliance/templates/legal_basis_mapping.md`

```markdown
# Registro de Atividades de Tratamento - LGPD Art. 37

## Informações do Controlador
- **Nome**: [NOME_DO_HOSPITAL]
- **CNPJ**: [CNPJ]
- **Endereço**: [ENDEREÇO_COMPLETO]
- **DPO/Responsável**: [NOME_DPO]
- **Contato DPO**: [EMAIL_DPO] | [TELEFONE_DPO]

---

## 1. DADOS DE PACIENTES

### 1.1 Identificação do Paciente
- **Base Legal**: Art. 11º, II, a (procedimentos médicos)
- **Finalidade**: Identificação e contato para prestação de cuidados médicos
- **Categorias de Dados**: Nome, CPF, data nascimento, endereço, telefone, cartão SUS
- **Origem**: Formulário de cadastro hospitalar, sistema de referência
- **Destinatários**: Equipe médica autorizada, enfermagem, administration
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 20 anos após última consulta (Resolução CFM 1.821/2007)
- **Medidas de Segurança**: Controle de acesso por função, auditoria, criptografia, UUIDs

### 1.2 Dados Médicos Sensíveis  
- **Base Legal**: Art. 11º, II, a (procedimentos médicos)
- **Finalidade**: Registro histórico médico e continuidade tratamento
- **Categorias de Dados**: Diagnósticos, prescrições, exames, evolução clínica, procedimentos
- **Origem**: Registro direto por profissionais de saúde
- **Destinatários**: Médicos responsáveis, equipe multidisciplinar autorizada
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 20 anos após última consulta
- **Medidas de Segurança**: Acesso restrito, logs auditoria, janela edição 24h

---

## 2. DADOS DA EQUIPE MÉDICA

### 2.1 Identificação Profissional
- **Base Legal**: Art. 7º, II (obrigação legal - CFM)
- **Finalidade**: Identificação profissional conforme regulamentação CFM/CRM
- **Categorias de Dados**: Nome, email, CRM, especialidade, telefone
- **Origem**: Cadastro de profissionais, validação CRM
- **Destinatários**: Administração hospitalar, outros profissionais
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 5 anos após fim do vínculo
- **Medidas de Segurança**: Autenticação forte, controle de sessão

---

## 3. DADOS DE AUDITORIA

### 3.1 Logs de Segurança
- **Base Legal**: Art. 7º, VI (interesse legítimo - segurança)
- **Finalidade**: Auditoria de segurança e monitoramento de acesso
- **Categorias de Dados**: Logs de acesso, IP, timestamp, ações realizadas
- **Origem**: Sistema automático de auditoria
- **Destinatários**: Administradores de sistema, DPO
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 3 anos para investigação de incidentes
- **Medidas de Segurança**: Logs protegidos, acesso restrito, detecção anomalias

---

**Data da Elaboração**: [DATA]  
**Responsável**: [NOME_DPO]  
**Próxima Revisão**: [DATA + 1 ANO]
```

## Testing and Validation

### Step 6: Verification Commands

#### 6.1 Legal Basis Validation Command

**File**: `apps/core/management/commands/validate_legal_basis.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import DataProcessingPurpose
from apps.patients.models import Patient
from apps.accounts.models import EqmdCustomUser

class Command(BaseCommand):
    help = 'Validates LGPD legal basis coverage'
    
    def handle(self, *args, **options):
        self.stdout.write("Validating LGPD legal basis coverage...")
        
        # Check if basic purposes are defined
        required_categories = [
            'patient_identification',
            'patient_medical_history', 
            'staff_identification',
            'system_audit'
        ]
        
        missing_categories = []
        for category in required_categories:
            if not DataProcessingPurpose.objects.filter(data_category=category, is_active=True).exists():
                missing_categories.append(category)
        
        if missing_categories:
            self.stdout.write(
                self.style.ERROR(f"Missing legal basis for: {', '.join(missing_categories)}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All required data categories have legal basis documented")
            )
        
        # Show statistics
        total_purposes = DataProcessingPurpose.objects.filter(is_active=True).count()
        patient_count = Patient.objects.count()
        staff_count = EqmdCustomUser.objects.count()
        
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"- Legal basis records: {total_purposes}")
        self.stdout.write(f"- Patients in system: {patient_count}")
        self.stdout.write(f"- Staff members: {staff_count}")
        
        # Compliance status
        compliance_percentage = (len(required_categories) - len(missing_categories)) / len(required_categories) * 100
        self.stdout.write(f"- Legal basis compliance: {compliance_percentage:.0f}%")
```

## Deliverable Summary

### Files Created
1. **App Structure**: New `apps/compliance` app for all LGPD-related functionality (Architectural Suggestion #1)
2. **Models**: `DataProcessingPurpose`, `LGPDComplianceSettings` (with configurable breach detection thresholds per Suggestion #4)
3. **Commands**: `setup_legal_basis.py`, `setup_lgpd_settings.py`, `validate_legal_basis.py`
4. **Admin**: LGPD admin interfaces in `apps/compliance/admin.py`
5. **Documentation**: Legal basis mapping template

### Database Changes
- New app: `apps/compliance` with dedicated models
- New tables: `compliance_dataprocessingpurpose`, `compliance_lgpdcompliancesettings`
- Indexes on key fields for performance
- Configurable breach detection thresholds in settings
- Foreign key relationships to user model

### Configuration Required
1. Update hospital-specific information in admin interface
2. Designate DPO/responsible person
3. Customize legal basis descriptions for specific medical procedures
4. Review and approve retention periods

## Next Phase

After completing Phase 1, proceed to **Phase 2: Patient Rights System** to implement data access and correction request mechanisms required by LGPD Article 18.

---

**Phase 1 Completion Criteria**:
- [ ] All models created and migrated  
- [ ] Legal basis documented for all data processing
- [ ] LGPD settings configured with hospital information
- [ ] Admin interfaces functional
- [ ] Validation command shows 100% legal basis compliance
- [ ] DPO designated and contact information updated