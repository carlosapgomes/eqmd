# Phase 5: Breach Response System Implementation

**Timeline**: Week 9-10  
**Priority**: MEDIUM  
**Dependencies**: Phases 1-4 completed  

## Objective

Implement comprehensive security incident detection, breach response procedures, and notification systems as required by LGPD Article 48 (security incident communication).

## Legal Requirements Addressed

- **LGPD Article 48**: Communication of security incidents to ANPD and data subjects
- **LGPD Article 46**: Security measures and incident response
- **LGPD Article 52**: Administrative sanctions for non-compliance
- **LGPD Article 6, VII**: Security principle

## Deliverables

1. **Incident Detection System**
2. **Breach Classification and Assessment**  
3. **ANPD Notification Procedures**
4. **Data Subject Notification System**
5. **Incident Response Dashboard**

---

## Implementation Steps

### Step 1: Security Incident Models

#### 1.1 Core Incident Models

**File**: `apps/core/models.py` (additions)

```python
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid
import json

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
```

### Step 2: Incident Detection Service

#### 2.1 Breach Detection Service

**File**: `apps/core/services/breach_detection.py`

```python
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from datetime import timedelta, datetime
from typing import List, Dict, Any
import logging
import json

from ..models import SecurityIncident, IncidentAction
from apps.patients.models import Patient

logger = logging.getLogger(__name__)
User = get_user_model()

class BreachDetectionService:
    """Service for detecting and assessing security incidents"""
    
    def __init__(self):
        self.detection_rules = {
            'failed_login_threshold': 10,  # Failed logins in 15 minutes
            'bulk_access_threshold': 50,   # Patient records accessed in 1 hour
            'off_hours_access_threshold': 5,  # Accesses between 22:00-06:00
            'geographic_anomaly_threshold': 100,  # km from usual location
            'data_export_threshold': 100,  # Records exported in 1 hour
        }
        
        self.risk_matrix = {
            ('unauthorized_access', 'high'): 'high',
            ('data_breach', 'medium'): 'high',
            ('data_loss', 'low'): 'medium',
            # Add more combinations as needed
        }
    
    def run_detection_scan(self):
        """Run all detection rules and create incidents for matches"""
        
        incidents_created = []
        
        # Detect suspicious login patterns
        login_incidents = self.detect_suspicious_logins()
        incidents_created.extend(login_incidents)
        
        # Detect bulk data access
        bulk_access_incidents = self.detect_bulk_data_access()
        incidents_created.extend(bulk_access_incidents)
        
        # Detect off-hours access
        off_hours_incidents = self.detect_off_hours_access()
        incidents_created.extend(off_hours_incidents)
        
        # Detect data export anomalies
        export_incidents = self.detect_export_anomalies()
        incidents_created.extend(export_incidents)
        
        return incidents_created
    
    def detect_suspicious_logins(self):
        """Detect suspicious login patterns"""
        incidents = []
        
        # This would integrate with your authentication logging
        # For now, we'll create a placeholder detection
        
        # Check for excessive failed logins (if you have auth logs)
        # suspicious_users = self.get_users_with_failed_logins()
        
        # Example incident creation
        # if suspicious_users:
        #     incident = self.create_incident(
        #         incident_type='unauthorized_access',
        #         title='Excessive Failed Login Attempts Detected',
        #         description=f'Multiple failed login attempts detected for users: {suspicious_users}',
        #         severity='medium'
        #     )
        #     incidents.append(incident)
        
        return incidents
    
    def detect_bulk_data_access(self):
        """Detect unusual bulk access to patient data"""
        incidents = []
        
        # Look for users accessing many patient records in short time
        cutoff_time = timezone.now() - timedelta(hours=1)
        
        # This would require audit logging of patient access
        # For now, simulate detection based on recent patient updates
        recent_updates = Patient.objects.filter(
            updated_at__gte=cutoff_time
        ).values('updated_by').annotate(
            update_count=Count('id')
        ).filter(
            update_count__gte=self.detection_rules['bulk_access_threshold']
        )
        
        for update_stat in recent_updates:
            if update_stat['updated_by']:
                try:
                    user = User.objects.get(id=update_stat['updated_by'])
                    incident = self.create_incident(
                        incident_type='unauthorized_access',
                        title=f'Bulk Patient Data Access by {user.get_full_name()}',
                        description=f'User {user.username} accessed {update_stat["update_count"]} patient records in the last hour.',
                        severity='high',
                        detected_by=None,  # Automated detection
                        affected_records=update_stat['update_count']
                    )
                    incidents.append(incident)
                except User.DoesNotExist:
                    continue
        
        return incidents
    
    def detect_off_hours_access(self):
        """Detect access during unusual hours"""
        incidents = []
        
        # Define off-hours (22:00 to 06:00)
        now = timezone.now()
        current_hour = now.hour
        
        if 22 <= current_hour or current_hour <= 6:
            # Check for significant activity during off-hours
            cutoff_time = now - timedelta(hours=1)
            
            off_hours_updates = Patient.objects.filter(
                updated_at__gte=cutoff_time
            ).count()
            
            if off_hours_updates >= self.detection_rules['off_hours_access_threshold']:
                incident = self.create_incident(
                    incident_type='unauthorized_access',
                    title='Unusual Off-Hours System Activity',
                    description=f'{off_hours_updates} patient record updates detected during off-hours ({current_hour}:00).',
                    severity='medium',
                    affected_records=off_hours_updates
                )
                incidents.append(incident)
        
        return incidents
    
    def detect_export_anomalies(self):
        """Detect unusual data export activities"""
        incidents = []
        
        # This would integrate with data export logging
        # Check for large exports or unusual export patterns
        
        # Placeholder: Check if many patient data requests were created recently
        from apps.patients.models import PatientDataRequest
        
        cutoff_time = timezone.now() - timedelta(hours=1)
        recent_exports = PatientDataRequest.objects.filter(
            requested_at__gte=cutoff_time,
            request_type='access'
        ).count()
        
        if recent_exports >= self.detection_rules['data_export_threshold']:
            incident = self.create_incident(
                incident_type='data_breach',
                title='Unusual Data Export Activity',
                description=f'{recent_exports} data access requests created in the last hour.',
                severity='high',
                affected_records=recent_exports
            )
            incidents.append(incident)
        
        return incidents
    
    def create_incident(self, incident_type: str, title: str, description: str, 
                       severity: str, detected_by=None, affected_records=0):
        """Create a new security incident"""
        
        # Assess risk level
        risk_level = self.assess_risk_level(incident_type, severity)
        
        # Determine notification requirements
        anpd_required, subject_required = self.assess_notification_requirements(
            incident_type, severity, affected_records
        )
        
        incident = SecurityIncident.objects.create(
            incident_type=incident_type,
            title=title,
            description=description,
            severity=severity,
            detected_at=timezone.now(),
            detected_by=detected_by,
            detection_method='automated_monitoring',
            estimated_records_affected=affected_records,
            risk_level=risk_level,
            initial_assessment=f'Automatically detected incident of type {incident_type}',
            affected_systems=json.dumps(['patient_management_system']),
            affected_data_categories=json.dumps(['patient_medical_records']),
            anpd_notification_required=anpd_required,
            data_subject_notification_required=subject_required,
        )
        
        # Create initial investigation action
        IncidentAction.objects.create(
            incident=incident,
            action_type='investigation',
            title='Initial Automated Assessment',
            description='Incident detected by automated monitoring system. Manual investigation required.',
            performed_by=None,
            performed_at=timezone.now(),
            completed=False
        )
        
        logger.warning(f"Security incident created: {incident.incident_id} - {title}")
        
        # Send alerts to security team
        self.send_incident_alerts(incident)
        
        return incident
    
    def assess_risk_level(self, incident_type: str, severity: str) -> str:
        """Assess risk level based on incident type and severity"""
        
        risk_key = (incident_type, severity)
        
        if risk_key in self.risk_matrix:
            return self.risk_matrix[risk_key]
        
        # Default risk assessment
        if severity == 'critical':
            return 'severe'
        elif severity == 'high':
            return 'high'
        elif severity == 'medium':
            return 'moderate'
        else:
            return 'low'
    
    def assess_notification_requirements(self, incident_type: str, severity: str, 
                                       affected_records: int) -> tuple:
        """Assess ANPD and data subject notification requirements"""
        
        # ANPD notification criteria
        anpd_required = False
        subject_required = False
        
        # High severity incidents always require ANPD notification
        if severity in ['high', 'critical']:
            anpd_required = True
        
        # Large number of affected records
        if affected_records >= 100:
            anpd_required = True
            subject_required = True
        
        # Specific incident types
        if incident_type in ['data_breach', 'data_loss']:
            anpd_required = True
            if affected_records > 0:
                subject_required = True
        
        # Unauthorized access to sensitive data
        if incident_type == 'unauthorized_access' and severity in ['medium', 'high', 'critical']:
            anpd_required = True
            if affected_records >= 10:
                subject_required = True
        
        return anpd_required, subject_required
    
    def send_incident_alerts(self, incident: SecurityIncident):
        """Send alerts to security team about new incident"""
        
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.core.models import LGPDComplianceSettings
        
        try:
            lgpd_settings = LGPDComplianceSettings.objects.first()
            if not lgpd_settings or not lgpd_settings.breach_notification_email:
                logger.warning("No breach notification email configured")
                return
            
            subject = f'🚨 INCIDENTE DE SEGURANÇA: {incident.incident_id}'
            message = f"""
ALERTA DE INCIDENTE DE SEGURANÇA

Incidente: {incident.incident_id}
Tipo: {incident.get_incident_type_display()}
Severidade: {incident.get_severity_display()}
Status: {incident.get_status_display()}

Descrição:
{incident.description}

Avaliação Inicial:
- Nível de Risco: {incident.get_risk_level_display()}
- Registros Afetados: {incident.estimated_records_affected}
- Notificação ANPD Necessária: {'Sim' if incident.anpd_notification_required else 'Não'}
- Notificação Titulares Necessária: {'Sim' if incident.data_subject_notification_required else 'Não'}

Horário de Detecção: {incident.detected_at.strftime('%d/%m/%Y %H:%M:%S')}
Método de Detecção: {incident.get_detection_method_display()}

AÇÃO REQUERIDA:
1. Revisar e investigar o incidente imediatamente
2. Atualizar status conforme progresso da resposta
3. Preparar notificações se necessário

Acesse o sistema para mais detalhes e ações de resposta.

Sistema de Monitoramento LGPD
EquipeMed
"""
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [lgpd_settings.breach_notification_email],
                fail_silently=True
            )
            
            logger.info(f"Incident alert sent for {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to send incident alert: {e}")
    
    def escalate_incident(self, incident: SecurityIncident, escalation_reason: str):
        """Escalate incident severity or status"""
        
        # Increase severity if not already at maximum
        severity_order = ['low', 'medium', 'high', 'critical']
        current_index = severity_order.index(incident.severity)
        
        if current_index < len(severity_order) - 1:
            new_severity = severity_order[current_index + 1]
            incident.severity = new_severity
            
            # Re-assess notification requirements
            anpd_required, subject_required = self.assess_notification_requirements(
                incident.incident_type, new_severity, incident.estimated_records_affected
            )
            
            incident.anpd_notification_required = anpd_required
            incident.data_subject_notification_required = subject_required
            incident.save()
            
            # Create escalation action
            IncidentAction.objects.create(
                incident=incident,
                action_type='investigation',
                title='Incident Escalated',
                description=f'Incident escalated to {new_severity} severity. Reason: {escalation_reason}',
                performed_by=None,
                performed_at=timezone.now(),
                completed=True
            )
            
            # Send escalation alert
            self.send_incident_alerts(incident)
            
            logger.warning(f"Incident {incident.incident_id} escalated to {new_severity}")
```

### Step 3: Notification Management

#### 3.1 Notification Service

**File**: `apps/core/services/breach_notification.py`

```python
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
import logging
import json

from ..models import SecurityIncident, BreachNotification, LGPDComplianceSettings

logger = logging.getLogger(__name__)

class BreachNotificationService:
    """Service for managing breach notifications"""
    
    def __init__(self):
        self.anpd_contact = {
            'email': 'notificacao@anpd.gov.br',  # Example - use actual ANPD contact
            'portal': 'https://www.gov.br/anpd/pt-br',
            'phone': '+55 61 2025-3600'  # Example
        }
    
    def process_notification_requirements(self, incident: SecurityIncident):
        """Process notification requirements for an incident"""
        
        notifications_created = []
        
        # ANPD notification
        if incident.anpd_notification_required:
            anpd_notification = self.create_anpd_notification(incident)
            notifications_created.append(anpd_notification)
        
        # Data subject notification
        if incident.data_subject_notification_required:
            subject_notifications = self.create_data_subject_notifications(incident)
            notifications_created.extend(subject_notifications)
        
        # Internal stakeholder notifications
        internal_notifications = self.create_internal_notifications(incident)
        notifications_created.extend(internal_notifications)
        
        return notifications_created
    
    def create_anpd_notification(self, incident: SecurityIncident):
        """Create ANPD notification"""
        
        lgpd_settings = LGPDComplianceSettings.objects.first()
        
        # Generate notification content
        subject = f"Comunicação de Incidente de Segurança - {incident.incident_id}"
        content = self.generate_anpd_notification_content(incident, lgpd_settings)
        
        notification = BreachNotification.objects.create(
            incident=incident,
            notification_type='anpd',
            recipient_name='ANPD - Autoridade Nacional de Proteção de Dados',
            recipient_contact=self.anpd_contact['email'],
            delivery_method='email',
            subject=subject,
            content=content,
            scheduled_at=timezone.now() + timedelta(hours=1),  # Give time for review
            legal_basis='LGPD Art. 48 - Comunicação de incidente de segurança',
            created_by=None  # System generated
        )
        
        logger.info(f"ANPD notification created: {notification.notification_id}")
        return notification
    
    def generate_anpd_notification_content(self, incident: SecurityIncident, lgpd_settings):
        """Generate content for ANPD notification"""
        
        template_content = f"""
COMUNICAÇÃO DE INCIDENTE DE SEGURANÇA À ANPD

Em conformidade com o Art. 48 da Lei Geral de Proteção de Dados (LGPD), comunicamos a ocorrência de incidente de segurança que pode acarretar risco ou dano relevante aos titulares de dados pessoais.

== INFORMAÇÕES DO CONTROLADOR ==
Razão Social: {lgpd_settings.controller_name if lgpd_settings else '[NOME_CONTROLADOR]'}
CNPJ: {lgpd_settings.controller_cnpj if lgpd_settings else '[CNPJ]'}
Endereço: {lgpd_settings.controller_address if lgpd_settings else '[ENDEREÇO]'}

Encarregado de Proteção de Dados:
Nome: {lgpd_settings.dpo_name if lgpd_settings else '[NOME_DPO]'}
Email: {lgpd_settings.dpo_email if lgpd_settings else '[EMAIL_DPO]'}
Telefone: {lgpd_settings.dpo_phone if lgpd_settings else '[TELEFONE_DPO]'}

== INFORMAÇÕES DO INCIDENTE ==
Identificação: {incident.incident_id}
Tipo: {incident.get_incident_type_display()}
Data/Hora de Detecção: {incident.detected_at.strftime('%d/%m/%Y às %H:%M:%S')}
Método de Detecção: {incident.get_detection_method_display()}

== DESCRIÇÃO DO INCIDENTE ==
{incident.description}

Avaliação Inicial: {incident.initial_assessment}

== DADOS AFETADOS ==
Categorias de Dados: {', '.join(json.loads(incident.affected_data_categories) if incident.affected_data_categories else [])}
Número Estimado de Titulares Afetados: {incident.estimated_records_affected}
Sistemas Afetados: {', '.join(json.loads(incident.affected_systems) if incident.affected_systems else [])}

== AVALIAÇÃO DE RISCOS ==
Nível de Risco: {incident.get_risk_level_display()}
Impacto Potencial: {incident.potential_impact or 'Em avaliação'}

== MEDIDAS ADOTADAS ==
Status Atual: {incident.get_status_display()}
"""

        # Add response actions
        actions = incident.actions.all().order_by('performed_at')
        if actions:
            template_content += "\nAções de Resposta Implementadas:\n"
            for action in actions:
                template_content += f"- {action.title} ({action.performed_at.strftime('%d/%m/%Y %H:%M')})\n"
                if action.description:
                    template_content += f"  {action.description}\n"

        # Add timeline if available
        template_content += f"""
== CRONOLOGIA ==
Detecção: {incident.detected_at.strftime('%d/%m/%Y %H:%M')}
"""
        if incident.containment_at:
            template_content += f"Contenção: {incident.containment_at.strftime('%d/%m/%Y %H:%M')}\n"
        if incident.eradication_at:
            template_content += f"Erradicação: {incident.eradication_at.strftime('%d/%m/%Y %H:%M')}\n"
        if incident.recovery_at:
            template_content += f"Recuperação: {incident.recovery_at.strftime('%d/%m/%Y %H:%M')}\n"

        template_content += f"""
== COMUNICAÇÃO AOS TITULARES ==
Notificação aos Titulares Necessária: {'Sim' if incident.data_subject_notification_required else 'Não'}
"""
        
        if incident.data_subject_notification_required:
            template_content += f"Prazo para Notificação: {incident.subject_notification_deadline.strftime('%d/%m/%Y %H:%M') if incident.subject_notification_deadline else 'A definir'}\n"

        template_content += f"""
== CONTATO PARA ESCLARECIMENTOS ==
Este comunicado foi gerado automaticamente pelo sistema de conformidade LGPD.
Para esclarecimentos adicionais, favor entrar em contato:

Email: {lgpd_settings.dpo_email if lgpd_settings else '[EMAIL_DPO]'}
Telefone: {lgpd_settings.dpo_phone if lgpd_settings else '[TELEFONE_DPO]'}

Data da Comunicação: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        
        return template_content
    
    def create_data_subject_notifications(self, incident: SecurityIncident):
        """Create notifications for affected data subjects"""
        
        notifications = []
        
        # For this implementation, we'll create a generic notification
        # In practice, you'd identify specific affected patients and create individual notifications
        
        # Get affected patients (this would be more sophisticated in practice)
        from apps.patients.models import Patient
        
        # For now, create a general notification template
        subject = f"Importante: Comunicação sobre Segurança dos Seus Dados - {incident.incident_id}"
        content = self.generate_subject_notification_content(incident)
        
        # Create a generic notification record (in practice, you'd create individual ones)
        notification = BreachNotification.objects.create(
            incident=incident,
            notification_type='data_subject',
            recipient_name='Titulares de Dados Afetados',
            recipient_contact='[LISTA_DE_CONTATOS]',
            delivery_method='email',
            subject=subject,
            content=content,
            scheduled_at=timezone.now() + timedelta(hours=24),  # Give time to prepare proper notifications
            legal_basis='LGPD Art. 48 - Comunicação aos titulares afetados',
            created_by=None
        )
        
        notifications.append(notification)
        logger.info(f"Data subject notification template created: {notification.notification_id}")
        
        return notifications
    
    def generate_subject_notification_content(self, incident: SecurityIncident):
        """Generate content for data subject notification"""
        
        lgpd_settings = LGPDComplianceSettings.objects.first()
        
        template_content = f"""
Prezado(a) Paciente,

Escribimos para informá-lo sobre um incidente de segurança que pode ter afetado alguns dos seus dados pessoais em nossos sistemas.

== O QUE ACONTECEU ==
{incident.description}

== QUANDO ACONTECEU ==
O incidente foi detectado em {incident.detected_at.strftime('%d/%m/%Y às %H:%M')}.

== QUAIS DADOS PODEM TER SIDO AFETADOS ==
Os seguintes tipos de dados podem ter sido envolvidos:
{', '.join(json.loads(incident.affected_data_categories) if incident.affected_data_categories else ['Dados de identificação e médicos'])}

== O QUE ESTAMOS FAZENDO ==
Tomamos as seguintes medidas imediatas:
- Investigação completa do incidente
- Implementação de medidas de contenção
- Fortalecimento dos controles de segurança
- Comunicação às autoridades competentes (ANPD)

Status atual: {incident.get_status_display()}

== O QUE VOCÊ PODE FAZER ==
Recomendamos que você:
- Monitore suas informações pessoais e médicas
- Entre em contato conosco se notar algo suspeito
- Mantenha seus dados de contato atualizados

== SEUS DIREITOS ==
Conforme a LGPD, você tem direito a:
- Obter informações sobre o tratamento dos seus dados
- Solicitar correção de dados incorretos
- Solicitar exclusão de dados desnecessários
- Solicitar portabilidade dos seus dados

== CONTATO ==
Para dúvidas ou exercer seus direitos:

Encarregado de Proteção de Dados:
Email: {lgpd_settings.dpo_email if lgpd_settings else '[EMAIL_DPO]'}
Telefone: {lgpd_settings.dpo_phone if lgpd_settings else '[TELEFONE_DPO]'}

Hospital:
Telefone: [TELEFONE_HOSPITAL]
Email: [EMAIL_HOSPITAL]

== COMPROMISSO COM A PRIVACIDADE ==
Levamos a proteção dos seus dados muito a sério. Este incidente não altera nosso compromisso em proteger sua privacidade e manter a segurança das suas informações.

Pedimos desculpas por este incidente e pelo transtorno causado.

Atenciosamente,
Equipe de Proteção de Dados
{lgpd_settings.controller_name if lgpd_settings else '[NOME_HOSPITAL]'}

Data: {timezone.now().strftime('%d/%m/%Y')}
Referência: {incident.incident_id}
"""
        
        return template_content
    
    def create_internal_notifications(self, incident: SecurityIncident):
        """Create internal stakeholder notifications"""
        
        notifications = []
        
        # Notification to hospital administration
        admin_notification = BreachNotification.objects.create(
            incident=incident,
            notification_type='business_partner',
            recipient_name='Administração Hospitalar',
            recipient_contact='[EMAIL_ADMINISTRACAO]',
            delivery_method='email',
            subject=f'Incidente de Segurança Requer Atenção - {incident.incident_id}',
            content=self.generate_internal_notification_content(incident),
            scheduled_at=timezone.now() + timedelta(minutes=30),
            legal_basis='Comunicação interna de incidente',
            created_by=None
        )
        
        notifications.append(admin_notification)
        
        return notifications
    
    def generate_internal_notification_content(self, incident: SecurityIncident):
        """Generate content for internal notifications"""
        
        return f"""
NOTIFICAÇÃO INTERNA - INCIDENTE DE SEGURANÇA

Incidente: {incident.incident_id}
Severidade: {incident.get_severity_display()}
Status: {incident.get_status_display()}

== RESUMO ==
{incident.description}

== IMPACTO ==
- Registros afetados: {incident.estimated_records_affected}
- Nível de risco: {incident.get_risk_level_display()}
- Notificação ANPD necessária: {'Sim' if incident.anpd_notification_required else 'Não'}
- Notificação pacientes necessária: {'Sim' if incident.data_subject_notification_required else 'Não'}

== AÇÕES NECESSÁRIAS ==
1. Revisar resposta ao incidente
2. Avaliar impacto nos negócios
3. Considerar comunicação externa adicional
4. Implementar melhorias de segurança

== CRONOLOGIA ==
Detecção: {incident.detected_at.strftime('%d/%m/%Y %H:%M')}
Status atual: {incident.get_status_display()}

Para mais informações, acessar o sistema de gestão de incidentes.
"""
    
    def send_notification(self, notification: BreachNotification):
        """Send a notification"""
        
        try:
            if notification.delivery_method == 'email':
                success = self.send_email_notification(notification)
            else:
                # Handle other delivery methods
                success = False
                notification.failure_reason = f"Delivery method {notification.delivery_method} not implemented"
            
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
            
            notification.save()
            return success
            
        except Exception as e:
            notification.status = 'failed'
            notification.failure_reason = str(e)
            notification.save()
            logger.error(f"Failed to send notification {notification.notification_id}: {e}")
            return False
    
    def send_email_notification(self, notification: BreachNotification):
        """Send email notification"""
        
        try:
            send_mail(
                notification.subject,
                notification.content,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient_contact],
                fail_silently=False
            )
            
            notification.delivery_confirmation = f"Email sent successfully to {notification.recipient_contact}"
            logger.info(f"Email notification sent: {notification.notification_id}")
            return True
            
        except Exception as e:
            notification.failure_reason = f"Email delivery failed: {str(e)}"
            logger.error(f"Email notification failed: {notification.notification_id} - {e}")
            return False
    
    def process_pending_notifications(self):
        """Process all pending notifications"""
        
        pending_notifications = BreachNotification.objects.filter(
            status='pending',
            scheduled_at__lte=timezone.now()
        )
        
        results = {'sent': 0, 'failed': 0}
        
        for notification in pending_notifications:
            if self.send_notification(notification):
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        return results
```

### Step 4: Management Commands

#### 4.1 Breach Detection Command

**File**: `apps/core/management/commands/run_breach_detection.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.services.breach_detection import BreachDetectionService
from apps.core.services.breach_notification import BreachNotificationService

class Command(BaseCommand):
    help = 'Run breach detection and notification processing'
    
    def add_arguments(self, parser):
        parser.add_argument('--detection-only', action='store_true', help='Run only detection, no notifications')
        parser.add_argument('--notifications-only', action='store_true', help='Process only pending notifications')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    def handle(self, *args, **options):
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Breach Detection and Notification - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"{'='*60}")
        
        if options['notifications_only']:
            self.process_notifications(options['dry_run'])
        elif options['detection_only']:
            self.run_detection(options['dry_run'])
        else:
            self.run_detection(options['dry_run'])
            self.process_notifications(options['dry_run'])
    
    def run_detection(self, dry_run=False):
        """Run breach detection"""
        self.stdout.write("\n🔍 Running Breach Detection...")
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No incidents will be created")
        
        detection_service = BreachDetectionService()
        
        if not dry_run:
            incidents = detection_service.run_detection_scan()
            
            if incidents:
                self.stdout.write(f"✓ {len(incidents)} incidents detected:")
                for incident in incidents:
                    self.stdout.write(f"  • {incident.incident_id}: {incident.title}")
                    self.stdout.write(f"    Severity: {incident.get_severity_display()}")
                    self.stdout.write(f"    ANPD Notification: {'Required' if incident.anpd_notification_required else 'Not Required'}")
            else:
                self.stdout.write("✓ No incidents detected")
        else:
            self.stdout.write("DRY RUN: Detection rules would be evaluated")
    
    def process_notifications(self, dry_run=False):
        """Process pending notifications"""
        self.stdout.write("\n📧 Processing Notifications...")
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No notifications will be sent")
        
        notification_service = BreachNotificationService()
        
        if not dry_run:
            results = notification_service.process_pending_notifications()
            
            self.stdout.write(f"✓ Notification processing complete:")
            self.stdout.write(f"  • Sent: {results['sent']}")
            self.stdout.write(f"  • Failed: {results['failed']}")
            
            if results['failed'] > 0:
                self.stdout.write(self.style.WARNING("⚠️  Some notifications failed. Check logs for details."))
        else:
            from apps.core.models import BreachNotification
            pending_count = BreachNotification.objects.filter(
                status='pending',
                scheduled_at__lte=timezone.now()
            ).count()
            self.stdout.write(f"DRY RUN: {pending_count} notifications would be processed")
        
        self.stdout.write("\n✅ Breach detection and notification processing complete")
```

#### 4.2 Incident Response Command

**File**: `apps/core/management/commands/manage_incident.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import SecurityIncident, IncidentAction
from apps.core.services.breach_notification import BreachNotificationService

class Command(BaseCommand):
    help = 'Manage security incidents'
    
    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true', help='List active incidents')
        parser.add_argument('--incident-id', type=str, help='Incident ID to manage')
        parser.add_argument('--status', type=str, help='Update incident status')
        parser.add_argument('--create-notifications', action='store_true', help='Create notifications for incident')
        parser.add_argument('--escalate', action='store_true', help='Escalate incident')
    
    def handle(self, *args, **options):
        if options['list']:
            self.list_incidents()
        elif options['incident_id']:
            self.manage_specific_incident(options)
        else:
            self.show_dashboard()
    
    def list_incidents(self):
        """List all active incidents"""
        incidents = SecurityIncident.objects.exclude(status='closed').order_by('-detected_at')
        
        self.stdout.write(f"\nActive Security Incidents ({incidents.count()}):")
        self.stdout.write("-" * 80)
        
        for incident in incidents:
            age = timezone.now() - incident.detected_at
            age_str = f"{age.days}d {age.seconds//3600}h" if age.days > 0 else f"{age.seconds//3600}h {(age.seconds%3600)//60}m"
            
            self.stdout.write(f"{incident.incident_id} | {incident.get_severity_display():<8} | {incident.get_status_display():<12} | {age_str:<8} | {incident.title}")
            
            if incident.anpd_notification_required:
                if incident.is_anpd_notification_overdue():
                    self.stdout.write(f"  🚨 ANPD notification OVERDUE!")
                else:
                    self.stdout.write(f"  ⚠️  ANPD notification required")
            
            if incident.data_subject_notification_required:
                if incident.is_subject_notification_overdue():
                    self.stdout.write(f"  🚨 Subject notification OVERDUE!")
                else:
                    self.stdout.write(f"  ⚠️  Subject notification required")
    
    def manage_specific_incident(self, options):
        """Manage a specific incident"""
        incident_id = options['incident_id']
        
        try:
            incident = SecurityIncident.objects.get(incident_id=incident_id)
        except SecurityIncident.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Incident {incident_id} not found"))
            return
        
        self.stdout.write(f"\n📋 Incident Details: {incident.incident_id}")
        self.stdout.write("-" * 50)
        self.stdout.write(f"Title: {incident.title}")
        self.stdout.write(f"Type: {incident.get_incident_type_display()}")
        self.stdout.write(f"Severity: {incident.get_severity_display()}")
        self.stdout.write(f"Status: {incident.get_status_display()}")
        self.stdout.write(f"Risk Level: {incident.get_risk_level_display()}")
        self.stdout.write(f"Detected: {incident.detected_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Records Affected: {incident.estimated_records_affected}")
        
        # Handle status update
        if options['status']:
            old_status = incident.status
            incident.status = options['status']
            
            # Update timeline fields based on status
            if options['status'] == 'contained' and not incident.containment_at:
                incident.containment_at = timezone.now()
            elif options['status'] == 'eradicated' and not incident.eradication_at:
                incident.eradication_at = timezone.now()
            elif options['status'] == 'resolved' and not incident.resolution_at:
                incident.resolution_at = timezone.now()
            
            incident.save()
            
            # Create action record
            IncidentAction.objects.create(
                incident=incident,
                action_type='investigation',
                title=f'Status Updated: {old_status} → {options["status"]}',
                description=f'Incident status updated via management command',
                performed_by=None,
                performed_at=timezone.now(),
                completed=True
            )
            
            self.stdout.write(f"✓ Status updated: {old_status} → {options['status']}")
        
        # Handle notification creation
        if options['create_notifications']:
            notification_service = BreachNotificationService()
            notifications = notification_service.process_notification_requirements(incident)
            
            self.stdout.write(f"✓ Created {len(notifications)} notifications:")
            for notification in notifications:
                self.stdout.write(f"  • {notification.notification_id}: {notification.get_notification_type_display()}")
        
        # Handle escalation
        if options['escalate']:
            from apps.core.services.breach_detection import BreachDetectionService
            detection_service = BreachDetectionService()
            detection_service.escalate_incident(incident, "Manual escalation via command")
            self.stdout.write(f"✓ Incident escalated to {incident.get_severity_display()}")
    
    def show_dashboard(self):
        """Show incident dashboard"""
        self.stdout.write("\n🛡️  Security Incident Dashboard")
        self.stdout.write("=" * 50)
        
        # Statistics
        total_incidents = SecurityIncident.objects.count()
        active_incidents = SecurityIncident.objects.exclude(status='closed').count()
        critical_incidents = SecurityIncident.objects.filter(severity='critical', status__in=['detected', 'investigating']).count()
        overdue_anpd = SecurityIncident.objects.filter(
            anpd_notification_required=True,
            anpd_notification_deadline__lt=timezone.now(),
            status__in=['detected', 'investigating', 'contained']
        ).count()
        
        self.stdout.write(f"\n📊 Statistics:")
        self.stdout.write(f"  • Total incidents: {total_incidents}")
        self.stdout.write(f"  • Active incidents: {active_incidents}")
        self.stdout.write(f"  • Critical incidents: {critical_incidents}")
        self.stdout.write(f"  • Overdue ANPD notifications: {overdue_anpd}")
        
        if critical_incidents > 0 or overdue_anpd > 0:
            self.stdout.write(self.style.ERROR("\n🚨 ATTENTION REQUIRED:"))
            if critical_incidents > 0:
                self.stdout.write(f"  • {critical_incidents} critical incidents need immediate attention")
            if overdue_anpd > 0:
                self.stdout.write(f"  • {overdue_anpd} ANPD notifications are overdue")
        
        # Recent incidents
        recent_incidents = SecurityIncident.objects.order_by('-detected_at')[:5]
        if recent_incidents:
            self.stdout.write(f"\n📋 Recent Incidents:")
            for incident in recent_incidents:
                age = timezone.now() - incident.detected_at
                age_str = f"{age.days}d" if age.days > 0 else f"{age.seconds//3600}h"
                self.stdout.write(f"  • {incident.incident_id} ({age_str} ago) - {incident.get_severity_display()} - {incident.title[:50]}...")
        
        self.stdout.write(f"\nUse --list to see all active incidents")
        self.stdout.write(f"Use --incident-id <ID> to manage specific incident")
```

### Step 5: Admin Interface

#### 5.1 Incident Admin

**File**: `apps/core/admin.py` (additions)

```python
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import SecurityIncident, IncidentAction, BreachNotification, IncidentEvidence

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
        from apps.core.services.breach_notification import BreachNotificationService
        
        notification_service = BreachNotificationService()
        total_notifications = 0
        
        for incident in queryset:
            notifications = notification_service.process_notification_requirements(incident)
            total_notifications += len(notifications)
        
        self.message_user(request, f'{total_notifications} notifications created for {queryset.count()} incidents.')
    create_notifications.short_description = 'Create required notifications'
    
    def escalate_severity(self, request, queryset):
        from apps.core.services.breach_detection import BreachDetectionService
        
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
        from apps.core.services.breach_notification import BreachNotificationService
        
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
```

## Migration and Setup

### Step 6: Database Migration and Configuration

```bash
# Create and run migrations
python manage.py makemigrations core --name "add_breach_response_models"
python manage.py migrate

# Set up scheduled detection (add to crontab)
# */15 * * * * cd /path/to/project && python manage.py run_breach_detection
# 0 */6 * * * cd /path/to/project && python manage.py run_breach_detection --notifications-only
```

### Step 7: Testing and Validation

```bash
# Test breach detection
python manage.py run_breach_detection --dry-run

# Test incident management
python manage.py manage_incident --list

# Create test incident for validation
python manage.py shell -c "
from apps.core.services.breach_detection import BreachDetectionService
service = BreachDetectionService()
incident = service.create_incident(
    'data_breach', 
    'Test Security Incident', 
    'Test incident for validation', 
    'high',
    affected_records=150
)
print(f'Test incident created: {incident.incident_id}')
"
```

## Deliverable Summary

### Files Created
1. **Models**: `SecurityIncident`, `IncidentAction`, `BreachNotification`, `IncidentEvidence`
2. **Services**: `BreachDetectionService`, `BreachNotificationService`
3. **Commands**: Breach detection, incident management, notification processing
4. **Admin**: Complete incident management interface
5. **Templates**: ANPD and data subject notification templates

### Key Features Implemented
- **Automated incident detection** based on suspicious patterns
- **Risk assessment and classification** of security incidents
- **ANPD notification automation** with deadline tracking
- **Data subject notification management** with templates
- **Incident response workflow** with action tracking
- **Evidence collection and chain of custody**
- **Notification delivery tracking** and failure handling
- **Compliance deadline monitoring** with alerts

### Database Changes
- New tables: `core_securityincident`, `core_incidentaction`, `core_breachnotification`, `core_incidentevidence`
- Indexes for performance on date and status queries
- File upload fields for evidence storage

## Next Phase

After completing Phase 5, proceed to **Phase 6: Monitoring & Maintenance** to implement ongoing compliance monitoring, audit procedures, and staff training systems.

---

**Phase 5 Completion Criteria**:
- [ ] Incident detection system operational
- [ ] Breach classification and risk assessment functional
- [ ] ANPD notification procedures implemented
- [ ] Data subject notification system working
- [ ] Incident response dashboard accessible
- [ ] Evidence collection system functional
- [ ] Management commands operational
- [ ] Admin interface complete with actions
- [ ] Notification templates created and tested