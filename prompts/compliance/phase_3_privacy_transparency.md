# Phase 3: Privacy Transparency Implementation

**Timeline**: Week 5-6  
**Priority**: HIGH  
**Dependencies**: Phase 1 completed  

## Objective

Implement privacy transparency requirements by creating comprehensive privacy policies, data processing notices, and consent management systems as required by LGPD Article 9.

## Legal Requirements Addressed

- **LGPD Article 9**: Information to be provided to data subjects
- **LGPD Article 8**: Basis for consent 
- **LGPD Article 14**: Processing of personal data of children and adolescents
- **LGPD Article 43**: Data Protection Officer disclosure

## Deliverables

1. **Dynamic Privacy Policy System**
2. **Data Processing Notices**  
3. **Consent Management Framework**
4. **Minor/Parental Consent System**
5. **DPO Contact Information**

---

## Implementation Steps

### Step 1: Privacy Policy Management System

#### 1.1 Privacy Policy Models

**File**: `apps/core/models.py` (additions)

```python
from django.db import models
from django.utils import timezone
from django.urls import reverse
import uuid

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
    ]
    
    CONSENT_STATUS = [
        ('granted', 'Consentimento Concedido'),
        ('denied', 'Consentimento Negado'),
        ('withdrawn', 'Consentimento Retirado'),
        ('expired', 'Consentimento Expirado'),
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
    
    # Evidence and audit
    consent_evidence = models.FileField(
        upload_to='consent_evidence/',
        null=True,
        blank=True,
        help_text="Documento comprobatório do consentimento"
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
    
    def __str__(self):
        return f"{self.patient.name} - {self.get_consent_type_display()} - {self.status}"

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
```

#### 1.2 Minor Consent Management

```python
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
```

### Step 2: Privacy Policy Content Management

#### 2.1 Privacy Policy Content Templates

**File**: `prompts/compliance/templates/privacy_policy_template.md`

```markdown
# Política de Privacidade - {{ hospital_name }}

**Versão:** {{ version }}  
**Data de Vigência:** {{ effective_date }}  
**Última Atualização:** {{ last_updated }}

---

## 1. INFORMAÇÕES GERAIS

### 1.1 Sobre Esta Política
Esta Política de Privacidade descreve como {{ hospital_name }} coleta, usa, armazena e protege suas informações pessoais, em conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD - Lei 13.709/2018).

### 1.2 Controlador de Dados
**{{ hospital_name }}**  
CNPJ: {{ cnpj }}  
Endereço: {{ address }}  
Telefone: {{ phone }}  
Email: {{ email }}

### 1.3 Encarregado de Proteção de Dados (DPO)
**Nome:** {{ dpo_name }}  
**Email:** {{ dpo_email }}  
**Telefone:** {{ dpo_phone }}

---

## 2. DADOS COLETADOS

### 2.1 Dados Pessoais de Pacientes

#### Dados de Identificação
- **Dados coletados:** Nome completo, CPF, RG, data de nascimento, endereço, telefone, email
- **Finalidade:** Identificação e contato para prestação de cuidados médicos
- **Base legal:** Art. 11º, II, 'a' da LGPD (procedimentos médicos/saúde)
- **Fonte:** Formulário de cadastro hospitalar, sistemas de referência

#### Dados de Saúde (Sensíveis)
- **Dados coletados:** Histórico médico, diagnósticos, prescrições, exames, sinais vitais, evolução clínica
- **Finalidade:** Prestação de cuidados médicos, continuidade do tratamento, histórico clínico
- **Base legal:** Art. 11º, II, 'a' da LGPD (procedimentos médicos/saúde)
- **Fonte:** Consultas médicas, exames, registros de enfermagem

#### Dados de Contato de Emergência
- **Dados coletados:** Nome, telefone, endereço, relação com paciente
- **Finalidade:** Contato em situações de emergência
- **Base legal:** Art. 11º, II, 'e' da LGPD (proteção da vida)
- **Fonte:** Formulário de cadastro fornecido pelo paciente

### 2.2 Dados da Equipe Médica

#### Identificação Profissional
- **Dados coletados:** Nome, email, telefone, CRM, especialidade, CPF
- **Finalidade:** Identificação profissional e comunicação da equipe
- **Base legal:** Art. 7º, II da LGPD (cumprimento de obrigação legal - CFM)
- **Fonte:** Documentos profissionais, cadastro de funcionários

### 2.3 Dados de Auditoria e Segurança
- **Dados coletados:** Logs de acesso, endereço IP, timestamp, ações realizadas
- **Finalidade:** Segurança dos dados, auditoria, detecção de incidentes
- **Base legal:** Art. 7º, VI da LGPD (interesse legítimo - segurança)
- **Fonte:** Sistema automático de auditoria

---

## 3. USO DOS DADOS

### 3.1 Finalidades Principais
- **Prestação de cuidados médicos:** Diagnóstico, tratamento, acompanhamento
- **Continuidade do cuidado:** Histórico médico, referências entre especialistas
- **Segurança do paciente:** Verificação de alergias, interações medicamentosas
- **Administração hospitalar:** Agendamentos, faturamento, estatísticas

### 3.2 Finalidades Secundárias (com consentimento específico)
- **Pesquisa médica:** Estudos clínicos, estatísticas epidemiológicas (dados anonimizados)
- **Melhoria da qualidade:** Análise de indicadores, treinamento de equipe
- **Comunicação:** Lembretes de consultas, informações de saúde relevantes

### 3.3 Bases Legais para Processamento
- **Cuidados médicos:** Art. 11º, II, 'a' (procedimentos médicos)
- **Obrigações legais:** Art. 7º, II (Resolução CFM, vigilância sanitária)
- **Interesse legítimo:** Art. 7º, VI (segurança, prevenção de fraudes)
- **Proteção da vida:** Art. 11º, II, 'e' (emergências médicas)

---

## 4. COMPARTILHAMENTO DE DADOS

### 4.1 Compartilhamento Interno
Seus dados são compartilhados apenas com:
- **Equipe médica direta:** Médicos, enfermeiros, fisioterapeutas responsáveis pelo seu cuidado
- **Especialistas consultados:** Quando há necessidade de segunda opinião ou tratamento especializado
- **Administração hospitalar:** Para agendamentos, faturamento e administração do cuidado

### 4.2 Compartilhamento Externo
Dados podem ser compartilhados com terceiros apenas em situações específicas:
- **Autoridades de saúde:** Quando exigido por lei (vigilância epidemiológica, notificação compulsória)
- **Planos de saúde:** Para autorização e cobrança de procedimentos (com seu consentimento)
- **Outros prestadores:** Para continuidade do cuidado (com sua autorização)
- **Autoridades judiciais:** Quando determinado por ordem judicial

### 4.3 Transferências Internacionais
Atualmente não realizamos transferências internacionais de dados. Caso seja necessário, será solicitado consentimento específico e implementadas salvaguardas adequadas.

---

## 5. RETENÇÃO DE DADOS

### 5.1 Períodos de Retenção

#### Dados Médicos
- **Período:** 20 anos após a última consulta
- **Base legal:** Resolução CFM 1.821/2007
- **Finalidade:** Preservação do histórico médico para cuidados futuros

#### Dados Administrativos
- **Período:** 5 anos após encerramento do vínculo
- **Base legal:** Legislação trabalhista e fiscal
- **Finalidade:** Cumprimento de obrigações legais

#### Dados de Auditoria
- **Período:** 3 anos
- **Base legal:** Interesse legítimo em segurança
- **Finalidade:** Investigação de incidentes e auditoria

### 5.2 Procedimentos de Exclusão
Ao final do período de retenção:
1. **Notificação prévia:** 6 meses antes da exclusão
2. **Anonimização:** Remoção de identificadores pessoais
3. **Exclusão segura:** Eliminação definitiva dos dados
4. **Documentação:** Registro do processo de exclusão

---

## 6. SEUS DIREITOS

Conforme a LGPD, você tem os seguintes direitos:

### 6.1 Direito de Acesso (Art. 18, I e II)
- Confirmar se tratamos seus dados
- Acessar seus dados pessoais
- Receber cópia dos seus dados

### 6.2 Direito de Correção (Art. 18, III)
- Corrigir dados incompletos, inexatos ou desatualizados

### 6.3 Direito de Exclusão (Art. 18, IV)
- Solicitar exclusão de dados desnecessários ou excessivos
- **Limitação:** Dados médicos essenciais podem ser mantidos por obrigação legal

### 6.4 Direito de Portabilidade (Art. 18, V)
- Receber seus dados em formato estruturado
- Transferir dados para outro controlador

### 6.5 Direito de Oposição (Art. 18, § 2º)
- Opor-se ao tratamento de dados com base em interesse legítimo
- **Limitação:** Não se aplica a dados essenciais para cuidados médicos

### 6.6 Direito à Informação (Art. 18, VII)
- Saber com quem compartilhamos seus dados
- Receber informações sobre processamento

### 6.7 Direito de Revogação (Art. 18, IX)
- Retirar consentimento a qualquer momento
- **Efeito:** Aplicável apenas a dados processados com base em consentimento

### 6.8 Como Exercer Seus Direitos
Para exercer qualquer direito:
- **Formulário online:** [LINK_FORMULARIO]
- **Email:** {{ dpo_email }}
- **Telefone:** {{ dpo_phone }}
- **Prazo de resposta:** Até 15 dias

---

## 7. SEGURANÇA DOS DADOS

### 7.1 Medidas Técnicas
- **Criptografia:** Dados protegidos em trânsito e em repouso
- **Controle de acesso:** Autenticação multifator, autorização baseada em função
- **Auditoria:** Logs completos de todas as operações
- **Backup:** Cópias de segurança regulares e testadas

### 7.2 Medidas Organizacionais
- **Treinamento:** Capacitação regular da equipe em proteção de dados
- **Políticas internas:** Procedimentos claros de segurança
- **Controle de acesso físico:** Restrição a áreas sensíveis
- **Monitoramento:** Vigilância contínua de atividades suspeitas

### 7.3 Incidentes de Segurança
Em caso de incidente:
1. **Contenção imediata:** Interrupção do vazamento
2. **Investigação:** Análise de causa e impacto
3. **Notificação:** ANPD e titulares afetados conforme necessário
4. **Correção:** Implementação de melhorias

---

## 8. MENORES DE IDADE

### 8.1 Consentimento Parental
Para pacientes menores de 18 anos:
- **Consentimento:** Pai, mãe ou responsável legal
- **Verificação:** Documentação da relação familiar/legal
- **Proteções especiais:** Restrições adicionais de compartilhamento

### 8.2 Direitos dos Menores
- **Participação:** Opinião considerada conforme maturidade
- **Proteção reforçada:** Proibição de marketing direto
- **Transição:** Aos 18 anos, controle total dos dados

---

## 9. COOKIES E TECNOLOGIAS

### 9.1 Uso de Cookies
Utilizamos cookies para:
- **Funcionais:** Manter sessão de usuário logado
- **Segurança:** Prevenção de ataques CSRF
- **Não utilizamos:** Cookies de rastreamento ou marketing

### 9.2 Controle
Você pode:
- **Gerenciar:** Configurações do navegador
- **Recusar:** Cookies não essenciais
- **Impacto:** Funcionalidades podem ser limitadas

---

## 10. ATUALIZAÇÕES DA POLÍTICA

### 10.1 Modificações
Esta política pode ser atualizada para:
- **Conformidade legal:** Mudanças na legislação
- **Melhorias:** Aprimoramento dos processos
- **Novos serviços:** Expansão das atividades

### 10.2 Notificação
Você será notificado sobre mudanças significativas:
- **Antecedência:** 30 dias antes da vigência
- **Meios:** Email, avisos no sistema, site
- **Direito de oposição:** Possibilidade de discordar

---

## 11. CONTATO

### 11.1 Dúvidas e Solicitações
**Encarregado de Proteção de Dados:**
- **Nome:** {{ dpo_name }}
- **Email:** {{ dpo_email }}
- **Telefone:** {{ dpo_phone }}
- **Endereço:** {{ hospital_address }}

### 11.2 Autoridade Supervisora
**ANPD - Autoridade Nacional de Proteção de Dados:**
- **Site:** https://www.gov.br/anpd/pt-br
- **Email:** [conforme disponibilizado pela ANPD]

---

## 12. DISPOSIÇÕES FINAIS

### 12.1 Prevalência
Em caso de conflito entre esta política e a lei, a legislação prevalece.

### 12.2 Idioma
Esta política está disponível em português. Traduções são apenas para conveniência.

### 12.3 Vigência
Esta política entra em vigor em {{ effective_date }} e permanece válida até nova versão.

---

**Documento aprovado por:** {{ legal_reviewer }}  
**Data da aprovação:** {{ legal_review_date }}  
**Próxima revisão:** {{ next_review_date }}
```

#### 2.2 Privacy Policy Management Command

**File**: `apps/core/management/commands/create_privacy_policy.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import PrivacyPolicy, LGPDComplianceSettings
from datetime import date, datetime
import os

class Command(BaseCommand):
    help = 'Creates initial privacy policy from template'
    
    def add_arguments(self, parser):
        parser.add_argument('--template', type=str, help='Template file path')
        parser.add_argument('--version', type=str, default='1.0', help='Policy version')
        parser.add_argument('--preview', action='store_true', help='Preview without saving')
    
    def handle(self, *args, **options):
        # Get LGPD settings
        try:
            lgpd_settings = LGPDComplianceSettings.objects.first()
            if not lgpd_settings:
                self.stdout.write(self.style.ERROR('LGPD settings not configured. Run setup_lgpd_settings first.'))
                return
        except:
            self.stdout.write(self.style.ERROR('LGPD settings not found.'))
            return
        
        # Load template
        template_path = options.get('template') or 'prompts/compliance/templates/privacy_policy_template.md'
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Template file not found: {template_path}'))
            return
        
        # Template variables
        variables = {
            'hospital_name': lgpd_settings.controller_name,
            'cnpj': lgpd_settings.controller_cnpj,
            'address': lgpd_settings.controller_address,
            'phone': '[TELEFONE_HOSPITAL]',  # Not in settings yet
            'email': '[EMAIL_HOSPITAL]',     # Not in settings yet
            'dpo_name': lgpd_settings.dpo_name,
            'dpo_email': lgpd_settings.dpo_email,
            'dpo_phone': lgpd_settings.dpo_phone,
            'version': options['version'],
            'effective_date': date.today().strftime('%d/%m/%Y'),
            'last_updated': date.today().strftime('%d/%m/%Y'),
            'legal_reviewer': '[REVISOR_JURIDICO]',
            'legal_review_date': '[DATA_REVISAO]',
            'next_review_date': '[PROXIMA_REVISAO]',
            'hospital_address': lgpd_settings.controller_address,
        }
        
        # Replace template variables
        content = template_content
        for key, value in variables.items():
            content = content.replace(f'{{{{ {key} }}}}', str(value))
        
        if options['preview']:
            self.stdout.write("Privacy Policy Preview:")
            self.stdout.write("-" * 50)
            self.stdout.write(content[:1000] + "..." if len(content) > 1000 else content)
            return
        
        # Create privacy policy
        policy = PrivacyPolicy.objects.create(
            version=options['version'],
            policy_type='main',
            title=f'Política de Privacidade - {lgpd_settings.controller_name}',
            summary='Política principal de privacidade conforme LGPD',
            content_markdown=content,
            effective_date=datetime.now(),
            is_active=True,
            legal_review_completed=False
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Privacy policy created successfully: {policy}')
        )
        self.stdout.write(
            self.style.WARNING('Remember to:')
        )
        self.stdout.write('1. Review and complete placeholder values')
        self.stdout.write('2. Have legal team review the policy')
        self.stdout.write('3. Mark legal_review_completed = True')
        self.stdout.write('4. Configure hospital contact information')
```

### Step 3: Consent Management Forms

#### 3.1 Consent Collection Forms

**File**: `apps/patients/forms.py` (additions)

```python
from django import forms
from apps.core.models import ConsentRecord, MinorConsentRecord
from apps.patients.models import Patient
from datetime import date, datetime

class PatientConsentForm(forms.Form):
    """Consent collection form for new patients"""
    
    # Patient identification
    patient_name = forms.CharField(max_length=200, label="Nome do Paciente")
    patient_birth_date = forms.DateField(label="Data de Nascimento", widget=forms.DateInput(attrs={'type': 'date'}))
    
    # Consent types
    medical_treatment = forms.BooleanField(
        required=True,
        label="Tratamento Médico",
        help_text="Concordo com o processamento dos meus dados para prestação de cuidados médicos"
    )
    
    data_storage = forms.BooleanField(
        required=True,
        label="Armazenamento de Dados",
        help_text="Concordo com o armazenamento dos meus dados médicos pelo período legal"
    )
    
    emergency_contact = forms.BooleanField(
        required=False,
        label="Contato de Emergência",
        help_text="Autorizo o contato com familiares em caso de emergência"
    )
    
    photo_video = forms.BooleanField(
        required=False,
        label="Fotos e Vídeos Médicos",
        help_text="Autorizo a captura de imagens para fins médicos"
    )
    
    research_participation = forms.BooleanField(
        required=False,
        label="Pesquisa Médica",
        help_text="Autorizo o uso dos meus dados anonimizados para pesquisa médica"
    )
    
    quality_improvement = forms.BooleanField(
        required=False,
        label="Melhoria da Qualidade",
        help_text="Autorizo o uso dos dados para análise e melhoria dos serviços"
    )
    
    # Terms acceptance
    privacy_policy_read = forms.BooleanField(
        required=True,
        label="Li e compreendi a Política de Privacidade",
        help_text="Declaro que li, compreendi e aceito os termos da Política de Privacidade"
    )
    
    consent_method = forms.CharField(widget=forms.HiddenInput(), initial='web_form')
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_patient_birth_date(self):
        birth_date = self.cleaned_data.get('patient_birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            # Store age for later use
            self.patient_age = age
            
            if age < 0:
                raise forms.ValidationError("Data de nascimento não pode ser no futuro")
            if age > 120:
                raise forms.ValidationError("Data de nascimento parece incorreta")
        
        return birth_date
    
    def is_minor(self):
        """Check if patient is a minor"""
        return hasattr(self, 'patient_age') and self.patient_age < 18
    
    def save(self, patient):
        """Save consent records for patient"""
        consent_data = self.cleaned_data
        
        # Get IP address from request
        ip_address = None
        user_agent = ""
        if self.request:
            ip_address = self.get_client_ip(self.request)
            user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        
        # Create consent records for each granted consent
        consent_records = []
        
        consent_mappings = [
            ('medical_treatment', 'medical_treatment', 'Tratamento médico e cuidados de saúde'),
            ('data_storage', 'data_processing', 'Armazenamento de dados médicos'),
            ('emergency_contact', 'data_sharing', 'Contato de emergência com familiares'),
            ('photo_video', 'photo_video', 'Captura de fotos e vídeos médicos'),
            ('research_participation', 'research', 'Participação em pesquisa médica'),
            ('quality_improvement', 'data_processing', 'Melhoria da qualidade dos serviços'),
        ]
        
        for form_field, consent_type, description in consent_mappings:
            if consent_data.get(form_field):
                consent_record = ConsentRecord.objects.create(
                    patient=patient,
                    consent_type=consent_type,
                    purpose_description=description,
                    data_categories='Dados médicos e identificação',
                    processing_activities='Coleta, armazenamento, uso conforme finalidade',
                    status='granted',
                    granted_at=datetime.now(),
                    granted_by=consent_data['patient_name'],
                    granted_by_relationship='self' if not self.is_minor() else 'parent',
                    consent_method=consent_data['consent_method'],
                    ip_address=ip_address,
                    user_agent=user_agent,
                    legal_basis='art11_ii_a' if consent_type == 'medical_treatment' else 'art7_i',
                    lawful_basis_explanation=f'Consentimento para {description.lower()}'
                )
                consent_records.append(consent_record)
        
        return consent_records
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class MinorConsentForm(forms.ModelForm):
    """Special consent form for patients under 18"""
    
    class Meta:
        model = MinorConsentRecord
        fields = [
            'guardian_name', 'guardian_relationship', 'guardian_document',
            'guardian_phone', 'guardian_email', 'consent_method',
            'guardian_id_verified', 'verification_method',
            'data_sharing_restricted', 'marketing_prohibited', 'research_participation_allowed'
        ]
        
        widgets = {
            'guardian_name': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_relationship': forms.Select(attrs={'class': 'form-select'}),
            'guardian_document': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CPF do responsável'}),
            'guardian_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'consent_method': forms.Select(attrs={'class': 'form-select'}),
            'verification_method': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
        labels = {
            'guardian_name': 'Nome do Responsável',
            'guardian_relationship': 'Relação com o Paciente',
            'guardian_document': 'CPF do Responsável',
            'guardian_phone': 'Telefone do Responsável',
            'guardian_email': 'Email do Responsável',
            'consent_method': 'Método de Consentimento',
            'guardian_id_verified': 'Identidade Verificada',
            'verification_method': 'Método de Verificação',
            'data_sharing_restricted': 'Restringir Compartilhamento',
            'marketing_prohibited': 'Proibir Marketing',
            'research_participation_allowed': 'Permitir Pesquisa',
        }
    
    # Additional consent confirmations
    understands_minor_rights = forms.BooleanField(
        required=True,
        label="Compreendo os direitos especiais de menores conforme LGPD"
    )
    
    accepts_responsibility = forms.BooleanField(
        required=True,
        label="Aceito a responsabilidade pelo consentimento como responsável legal"
    )
    
    def save(self, patient):
        """Save minor consent record"""
        instance = super().save(commit=False)
        instance.patient = patient
        instance.patient_birth_date = patient.birthday
        
        # Calculate age
        today = date.today()
        age = today.year - patient.birthday.year - ((today.month, today.day) < (patient.birthday.month, patient.birthday.day))
        instance.age_at_consent = age
        instance.is_minor = age < 18
        instance.consent_date = datetime.now()
        
        instance.save()
        return instance
```

### Step 4: Views and Templates

#### 4.1 Privacy Policy Views

**File**: `apps/core/views.py` (additions)

```python
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.generic import DetailView
from .models import PrivacyPolicy, DataProcessingNotice
import markdown

def privacy_policy(request, policy_type='main'):
    """Display current privacy policy"""
    policy = get_object_or_404(
        PrivacyPolicy,
        policy_type=policy_type,
        is_active=True
    )
    
    # Convert markdown to HTML
    content_html = markdown.markdown(policy.content_markdown, extensions=['tables', 'toc'])
    
    context = {
        'policy': policy,
        'content_html': content_html,
    }
    
    return render(request, 'core/privacy_policy.html', context)

def data_processing_notice(request, context):
    """Display data processing notice for specific context"""
    notice = get_object_or_404(
        DataProcessingNotice,
        context=context,
        is_active=True
    )
    
    return render(request, 'core/data_processing_notice.html', {'notice': notice})

class PrivacyPolicyDetailView(DetailView):
    """Detailed privacy policy view with version history"""
    model = PrivacyPolicy
    template_name = 'core/privacy_policy_detail.html'
    context_object_name = 'policy'
    
    def get_object(self):
        policy_type = self.kwargs.get('policy_type', 'main')
        return get_object_or_404(
            PrivacyPolicy,
            policy_type=policy_type,
            is_active=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add version history
        context['version_history'] = PrivacyPolicy.objects.filter(
            policy_type=self.object.policy_type
        ).order_by('-effective_date')[:5]
        
        # Convert markdown to HTML
        context['content_html'] = markdown.markdown(
            self.object.content_markdown,
            extensions=['tables', 'toc', 'codehilite']
        )
        
        return context
```

#### 4.2 Privacy Policy Template

**File**: `apps/core/templates/core/privacy_policy.html`

```html
{% extends "base.html" %}
{% load static %}

{% block title %}Política de Privacidade{% endblock %}

{% block extra_css %}
<style>
.privacy-header {
    background: linear-gradient(135deg, #2c3e50, #34495e);
    color: white;
    padding: 2rem 0;
}
.policy-meta {
    background: #f8f9fa;
    border-left: 4px solid #007bff;
    padding: 1rem;
    margin-bottom: 2rem;
}
.policy-content {
    line-height: 1.6;
}
.policy-content h2 {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.5rem;
    margin-top: 2rem;
}
.policy-content h3 {
    color: #34495e;
    margin-top: 1.5rem;
}
.table-of-contents {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
    padding: 1rem;
    margin-bottom: 2rem;
}
.table-of-contents ul {
    margin-bottom: 0;
}
.table-of-contents a {
    text-decoration: none;
    color: #0066cc;
}
.table-of-contents a:hover {
    text-decoration: underline;
}
</style>
{% endblock %}

{% block content %}
<div class="privacy-header">
    <div class="container">
        <div class="row">
            <div class="col-md-8">
                <h1><i class="bi bi-shield-lock me-3"></i>{{ policy.title }}</h1>
                <p class="lead">Proteção e transparência no tratamento dos seus dados pessoais</p>
            </div>
            <div class="col-md-4 text-md-end">
                <span class="badge bg-light text-dark fs-6">
                    Versão {{ policy.version }}
                </span>
            </div>
        </div>
    </div>
</div>

<div class="container mt-4">
    <div class="row">
        <div class="col-lg-3">
            <!-- Table of Contents -->
            <div class="table-of-contents sticky-top">
                <h6><i class="bi bi-list me-2"></i>Índice</h6>
                <ul class="list-unstyled">
                    <li><a href="#informacoes-gerais">1. Informações Gerais</a></li>
                    <li><a href="#dados-coletados">2. Dados Coletados</a></li>
                    <li><a href="#uso-dos-dados">3. Uso dos Dados</a></li>
                    <li><a href="#compartilhamento">4. Compartilhamento</a></li>
                    <li><a href="#retencao">5. Retenção de Dados</a></li>
                    <li><a href="#seus-direitos">6. Seus Direitos</a></li>
                    <li><a href="#seguranca">7. Segurança</a></li>
                    <li><a href="#menores">8. Menores de Idade</a></li>
                    <li><a href="#cookies">9. Cookies</a></li>
                    <li><a href="#atualizacoes">10. Atualizações</a></li>
                    <li><a href="#contato">11. Contato</a></li>
                </ul>
            </div>
        </div>
        
        <div class="col-lg-9">
            <!-- Policy Metadata -->
            <div class="policy-meta">
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="bi bi-info-circle me-2"></i>Informações da Política</h6>
                        <p class="mb-1"><strong>Versão:</strong> {{ policy.version }}</p>
                        <p class="mb-1"><strong>Vigência:</strong> {{ policy.effective_date|date:"d/m/Y" }}</p>
                        <p class="mb-0"><strong>Última Atualização:</strong> {{ policy.created_at|date:"d/m/Y H:i" }}</p>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="bi bi-download me-2"></i>Download</h6>
                        <a href="{% url 'privacy_policy_pdf' policy.policy_type %}" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-file-pdf me-1"></i>Baixar PDF
                        </a>
                        <a href="{% url 'privacy_policy_print' policy.policy_type %}" class="btn btn-sm btn-outline-secondary ms-2" target="_blank">
                            <i class="bi bi-printer me-1"></i>Imprimir
                        </a>
                    </div>
                </div>
            </div>
            
            <!-- Policy Content -->
            <div class="policy-content">
                {{ content_html|safe }}
            </div>
            
            <!-- Contact Information -->
            <div class="alert alert-info mt-4">
                <h6><i class="bi bi-person-badge me-2"></i>Dúvidas sobre esta Política?</h6>
                <p class="mb-1">Entre em contato com nosso Encarregado de Proteção de Dados:</p>
                <p class="mb-0">
                    <i class="bi bi-envelope me-1"></i>
                    <a href="mailto:{{ lgpd_settings.dpo_email }}">{{ lgpd_settings.dpo_email }}</a>
                    |
                    <i class="bi bi-telephone ms-2 me-1"></i>
                    {{ lgpd_settings.dpo_phone }}
                </p>
            </div>
            
            <!-- Rights Summary -->
            <div class="card mt-4">
                <div class="card-header">
                    <h6><i class="bi bi-shield-check me-2"></i>Resumo dos Seus Direitos</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <ul class="list-unstyled">
                                <li class="mb-2">
                                    <i class="bi bi-eye text-primary me-2"></i>
                                    <strong>Acesso:</strong> Conhecer seus dados
                                </li>
                                <li class="mb-2">
                                    <i class="bi bi-pencil text-primary me-2"></i>
                                    <strong>Correção:</strong> Corrigir dados incorretos
                                </li>
                                <li class="mb-2">
                                    <i class="bi bi-trash text-primary me-2"></i>
                                    <strong>Exclusão:</strong> Remover dados desnecessários
                                </li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <ul class="list-unstyled">
                                <li class="mb-2">
                                    <i class="bi bi-download text-primary me-2"></i>
                                    <strong>Portabilidade:</strong> Receber seus dados
                                </li>
                                <li class="mb-2">
                                    <i class="bi bi-x-circle text-primary me-2"></i>
                                    <strong>Oposição:</strong> Objetar ao processamento
                                </li>
                                <li class="mb-2">
                                    <i class="bi bi-info-circle text-primary me-2"></i>
                                    <strong>Informação:</strong> Saber sobre compartilhamento
                                </li>
                            </ul>
                        </div>
                    </div>
                    <div class="text-center mt-3">
                        <a href="{% url 'patient_data_request' %}" class="btn btn-primary">
                            <i class="bi bi-plus-circle me-2"></i>Exercer Meus Direitos
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// Smooth scrolling for table of contents
document.querySelectorAll('.table-of-contents a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
</script>
{% endblock %}
```

### Step 5: URL Configuration

#### 5.1 Privacy URLs

**File**: `apps/core/urls.py` (additions)

```python
from django.urls import path
from . import views

app_name = 'core'

urlpatterns += [
    # Privacy policy URLs
    path('privacidade/', views.privacy_policy, name='privacy_policy'),
    path('privacidade/<str:policy_type>/', views.privacy_policy, name='privacy_policy_type'),
    path('privacidade/<str:policy_type>/detalhes/', views.PrivacyPolicyDetailView.as_view(), name='privacy_policy_detail'),
    
    # Data processing notices
    path('aviso-processamento/<str:context>/', views.data_processing_notice, name='data_processing_notice'),
]
```

### Step 6: Admin Configuration

#### 6.1 Privacy Policy Admin

**File**: `apps/core/admin.py` (additions)

```python
from django.contrib import admin
from .models import PrivacyPolicy, DataProcessingNotice, ConsentRecord, MinorConsentRecord

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
    list_display = ['consent_id', 'patient', 'consent_type', 'status', 'granted_at', 'is_valid']
    list_filter = ['consent_type', 'status', 'granted_by_relationship', 'consent_method']
    search_fields = ['patient__name', 'granted_by', 'purpose_description']
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
            'fields': ['consent_evidence']
        })
    ]
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Válido'

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
```

## Migration and Setup

### Step 7: Database Migration and Initial Data

```bash
# Create and run migrations
python manage.py makemigrations core --name "add_privacy_transparency_models"
python manage.py migrate

# Install required packages
pip install markdown  # For converting markdown to HTML

# Create initial privacy policy
python manage.py create_privacy_policy --version "1.0"

# Create initial data processing notices
python manage.py create_processing_notices
```

### Step 8: Initial Data Processing Notices

**File**: `apps/core/management/commands/create_processing_notices.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import DataProcessingNotice

class Command(BaseCommand):
    help = 'Creates initial data processing notices'
    
    def handle(self, *args, **options):
        notices = [
            {
                'notice_id': 'PATIENT_REGISTRATION',
                'context': 'patient_registration',
                'title': 'Aviso de Processamento - Cadastro de Paciente',
                'purpose_description': 'Coletamos seus dados pessoais para identificação e prestação de cuidados médicos conforme protocolos hospitalares.',
                'data_categories': 'Nome, CPF, data de nascimento, endereço, telefone, dados de saúde',
                'legal_basis': 'Art. 11º, II, a da LGPD (procedimentos médicos)',
                'retention_period': '20 anos após última consulta (Resolução CFM 1.821/2007)',
                'recipients': 'Equipe médica autorizada, enfermagem, administração hospitalar',
                'rights_summary': 'Você tem direito a acessar, corrigir, excluir e portar seus dados conforme LGPD',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'modal'
            },
            {
                'notice_id': 'PHOTO_VIDEO_CAPTURE',
                'context': 'photo_video_capture',
                'title': 'Aviso - Captura de Imagens Médicas',
                'purpose_description': 'Capturamos fotos e vídeos para documentação médica, diagnóstico e acompanhamento do tratamento.',
                'data_categories': 'Imagens fotográficas e vídeos com conteúdo médico',
                'legal_basis': 'Art. 7º, I da LGPD (consentimento) + Art. 11º, II, a (procedimentos médicos)',
                'retention_period': '20 anos conforme prontuário médico',
                'recipients': 'Médicos responsáveis, especialistas consultados',
                'rights_summary': 'Você pode retirar o consentimento a qualquer momento, solicitar acesso ou exclusão das imagens',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'modal'
            },
            {
                'notice_id': 'EMERGENCY_TREATMENT',
                'context': 'emergency_treatment',
                'title': 'Processamento em Emergência',
                'purpose_description': 'Em situações de emergência, processamos seus dados para proteção da vida e prestação de cuidados urgentes.',
                'data_categories': 'Dados de identificação, histórico médico, dados de emergência',
                'legal_basis': 'Art. 11º, II, e da LGPD (proteção da vida)',
                'retention_period': '20 anos conforme legislação médica',
                'recipients': 'Equipe de emergência, médicos plantonistas',
                'rights_summary': 'Após estabilização, você poderá exercer todos os direitos previstos na LGPD',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'banner'
            }
        ]
        
        created_count = 0
        for notice_data in notices:
            notice, created = DataProcessingNotice.objects.get_or_create(
                notice_id=notice_data['notice_id'],
                defaults=notice_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {notice}")
            else:
                self.stdout.write(f"- Exists: {notice}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} processing notices')
        )
```

## Testing and Validation

### Step 9: Validation Commands

**File**: `apps/core/management/commands/validate_privacy_compliance.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import PrivacyPolicy, DataProcessingNotice, LGPDComplianceSettings

class Command(BaseCommand):
    help = 'Validates privacy transparency compliance'
    
    def handle(self, *args, **options):
        self.stdout.write("Validating privacy transparency compliance...")
        
        # Check LGPD settings
        lgpd_settings = LGPDComplianceSettings.objects.first()
        if not lgpd_settings:
            self.stdout.write(self.style.ERROR("❌ LGPD settings not configured"))
            return
        
        # Check active privacy policy
        active_policy = PrivacyPolicy.objects.filter(is_active=True, policy_type='main').first()
        if not active_policy:
            self.stdout.write(self.style.ERROR("❌ No active privacy policy"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Active privacy policy: v{active_policy.version}"))
        
        # Check legal review
        if active_policy and not active_policy.legal_review_completed:
            self.stdout.write(self.style.WARNING("⚠️  Privacy policy needs legal review"))
        
        # Check processing notices
        required_contexts = ['patient_registration', 'photo_video_capture', 'emergency_treatment']
        missing_notices = []
        
        for context in required_contexts:
            if not DataProcessingNotice.objects.filter(context=context, is_active=True).exists():
                missing_notices.append(context)
        
        if missing_notices:
            self.stdout.write(self.style.ERROR(f"❌ Missing processing notices: {', '.join(missing_notices)}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All required processing notices present"))
        
        # Check DPO information
        if not lgpd_settings.dpo_email or '[' in lgpd_settings.dpo_email:
            self.stdout.write(self.style.ERROR("❌ DPO contact information incomplete"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ DPO contact information configured"))
        
        # Statistics
        total_policies = PrivacyPolicy.objects.count()
        total_notices = DataProcessingNotice.objects.filter(is_active=True).count()
        
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"- Privacy policies: {total_policies}")
        self.stdout.write(f"- Active processing notices: {total_notices}")
        self.stdout.write(f"- DPO configured: {'Yes' if lgpd_settings.dpo_email else 'No'}")
```

## Deliverable Summary

### Files Created
1. **Models**: `PrivacyPolicy`, `DataProcessingNotice`, `ConsentRecord`, `MinorConsentRecord`
2. **Forms**: `PatientConsentForm`, `MinorConsentForm`
3. **Views**: Privacy policy display, data processing notices
4. **Templates**: Privacy policy page with table of contents
5. **Commands**: Privacy policy creation, processing notices setup, validation
6. **Admin**: Complete admin interfaces for all models

### URLs Added
- `/privacidade/` - Main privacy policy
- `/privacidade/<type>/` - Specific policy types
- `/aviso-processamento/<context>/` - Data processing notices

### Database Changes
- New tables: `core_privacypolicy`, `core_dataprocessingnotice`, `core_consentrecord`, `core_minorconsentrecord`, `core_consentwithdrawal`
- Indexes for performance
- File upload fields for consent documentation

## Next Phase

After completing Phase 3, proceed to **Phase 4: Data Lifecycle Management** to implement retention policies, deletion procedures, and automated data cleanup systems.

---

**Phase 3 Completion Criteria**:
- [ ] Privacy policy system functional with version control
- [ ] Data processing notices created for key contexts
- [ ] Consent management system operational
- [ ] Minor consent handling implemented
- [ ] DPO contact information configured
- [ ] Legal review process established
- [ ] Privacy policy accessible to users
- [ ] Validation command shows full compliance