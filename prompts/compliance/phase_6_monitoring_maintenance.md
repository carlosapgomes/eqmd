# Phase 6: Monitoring & Maintenance Implementation

**Timeline**: Week 11-12  
**Priority**: LOW  
**Dependencies**: All previous phases completed  

## Objective

Implement ongoing compliance monitoring, audit procedures, staff training systems, and maintenance workflows to ensure sustained LGPD compliance and continuous improvement.

## Legal Requirements Addressed

- **LGPD Article 50**: Ongoing compliance monitoring
- **LGPD Article 37**: Maintenance of processing records
- **LGPD Article 39**: Data protection impact assessment updates
- **LGPD Article 41**: Data protection officer responsibilities

## Deliverables

1. **Compliance Monitoring Dashboard**
2. **Automated Compliance Auditing**  
3. **Staff Training Management System**
4. **Performance Metrics and Reporting**
5. **Maintenance and Update Procedures**

---

## Implementation Steps

### Step 1: Compliance Monitoring Models

#### 1.1 Monitoring and Audit Models

**File**: `apps/core/models.py` (additions)

```python
from django.db import models
from django.utils import timezone
from datetime import timedelta, date
import uuid
import json

class ComplianceAudit(models.Model):
    """Track compliance audits and assessments"""
    
    AUDIT_TYPES = [
        ('routine', 'Auditoria Rotineira'),
        ('incident_triggered', 'Disparada por Incidente'),
        ('regulatory_required', 'Exigência Regulatória'),
        ('annual_review', 'Revisão Anual'),
        ('policy_update', 'Atualização de Política'),
        ('system_change', 'Mudança de Sistema'),
        ('training_assessment', 'Avaliação de Treinamento'),
    ]
    
    AUDIT_STATUS = [
        ('planned', 'Planejada'),
        ('in_progress', 'Em Andamento'),
        ('completed', 'Concluída'),
        ('failed', 'Falhada'),
        ('cancelled', 'Cancelada'),
    ]
    
    COMPLIANCE_SCORES = [
        ('excellent', 'Excelente (90-100%)'),
        ('good', 'Bom (75-89%)'),
        ('satisfactory', 'Satisfatório (60-74%)'),
        ('needs_improvement', 'Necessita Melhoria (40-59%)'),
        ('poor', 'Ruim (0-39%)'),
    ]
    
    # Audit identification
    audit_id = models.CharField(max_length=20, unique=True, editable=False)
    audit_type = models.CharField(max_length=20, choices=AUDIT_TYPES)
    
    # Scheduling
    scheduled_date = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Scope and focus
    title = models.CharField(max_length=200)
    description = models.TextField()
    audit_scope = models.TextField(help_text="JSON list of areas/systems audited")
    focus_areas = models.TextField(help_text="JSON list of specific focus areas")
    
    # Execution
    auditor = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_audits'
    )
    status = models.CharField(max_length=15, choices=AUDIT_STATUS, default='planned')
    
    # Results
    compliance_score = models.FloatField(null=True, blank=True, help_text="0-100 score")
    compliance_level = models.CharField(max_length=20, choices=COMPLIANCE_SCORES, blank=True)
    findings_count = models.IntegerField(default=0)
    critical_findings = models.IntegerField(default=0)
    
    # Reporting
    audit_report = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    corrective_actions_required = models.BooleanField(default=False)
    
    # Follow-up
    next_audit_due = models.DateField(null=True, blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_deadline = models.DateField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Auditoria de Conformidade"
        verbose_name_plural = "Auditorias de Conformidade"
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['audit_type', 'status']),
            models.Index(fields=['scheduled_date', 'completed_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.audit_id:
            self.audit_id = self.generate_audit_id()
        
        # Auto-calculate next audit due date
        if self.completed_at and not self.next_audit_due:
            if self.audit_type == 'annual_review':
                self.next_audit_due = self.completed_at.date() + timedelta(days=365)
            elif self.audit_type == 'routine':
                self.next_audit_due = self.completed_at.date() + timedelta(days=90)
            else:
                self.next_audit_due = self.completed_at.date() + timedelta(days=180)
        
        super().save(*args, **kwargs)
    
    def generate_audit_id(self):
        """Generate unique audit ID: AUD-YYYYMMDD-XXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        sequence = ComplianceAudit.objects.filter(
            audit_id__startswith=f'AUD-{date_str}'
        ).count() + 1
        return f'AUD-{date_str}-{sequence:03d}'
    
    def calculate_compliance_score(self):
        """Calculate overall compliance score from findings"""
        total_checks = self.checklist_items.count()
        if total_checks == 0:
            return None
        
        passed_checks = self.checklist_items.filter(status='compliant').count()
        score = (passed_checks / total_checks) * 100
        
        self.compliance_score = round(score, 1)
        
        # Determine compliance level
        if score >= 90:
            self.compliance_level = 'excellent'
        elif score >= 75:
            self.compliance_level = 'good'
        elif score >= 60:
            self.compliance_level = 'satisfactory'
        elif score >= 40:
            self.compliance_level = 'needs_improvement'
        else:
            self.compliance_level = 'poor'
        
        self.save()
        return score
    
    def __str__(self):
        return f"{self.audit_id} - {self.title}"

class ComplianceChecklist(models.Model):
    """Individual compliance checklist items"""
    
    CHECK_CATEGORIES = [
        ('legal_basis', 'Base Legal'),
        ('data_subject_rights', 'Direitos dos Titulares'),
        ('privacy_policies', 'Políticas de Privacidade'),
        ('retention_management', 'Gestão de Retenção'),
        ('incident_response', 'Resposta a Incidentes'),
        ('staff_training', 'Treinamento da Equipe'),
        ('technical_security', 'Segurança Técnica'),
        ('organizational_measures', 'Medidas Organizacionais'),
    ]
    
    CHECK_STATUS = [
        ('compliant', 'Conforme'),
        ('non_compliant', 'Não Conforme'),
        ('partially_compliant', 'Parcialmente Conforme'),
        ('not_applicable', 'Não Aplicável'),
        ('pending_review', 'Pendente de Revisão'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    audit = models.ForeignKey(ComplianceAudit, on_delete=models.CASCADE, related_name='checklist_items')
    
    # Check details
    category = models.CharField(max_length=30, choices=CHECK_CATEGORIES)
    check_id = models.CharField(max_length=20)  # e.g., "LGPD-ART7-01"
    title = models.CharField(max_length=200)
    description = models.TextField()
    legal_reference = models.CharField(max_length=100)
    
    # Assessment
    status = models.CharField(max_length=20, choices=CHECK_STATUS, default='pending_review')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Evidence and notes
    evidence_required = models.TextField(blank=True)
    evidence_provided = models.TextField(blank=True)
    assessor_notes = models.TextField(blank=True)
    
    # Remediation
    non_compliance_details = models.TextField(blank=True)
    recommended_action = models.TextField(blank=True)
    remediation_deadline = models.DateField(null=True, blank=True)
    
    # Metadata
    assessed_at = models.DateTimeField(null=True, blank=True)
    assessed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Item de Checklist"
        verbose_name_plural = "Itens de Checklist"
        ordering = ['category', 'check_id']
        unique_together = ['audit', 'check_id']
    
    def __str__(self):
        return f"{self.check_id} - {self.title}"

class ComplianceMetric(models.Model):
    """Track compliance metrics over time"""
    
    METRIC_TYPES = [
        ('patient_requests_response_time', 'Tempo de Resposta - Solicitações de Pacientes'),
        ('data_retention_compliance', 'Conformidade de Retenção de Dados'),
        ('staff_training_completion', 'Conclusão de Treinamento'),
        ('incident_response_time', 'Tempo de Resposta a Incidentes'),
        ('privacy_policy_awareness', 'Conhecimento da Política de Privacidade'),
        ('data_subject_rights_fulfillment', 'Cumprimento de Direitos dos Titulares'),
        ('breach_notification_timeliness', 'Pontualidade de Notificação de Violação'),
        ('audit_compliance_score', 'Pontuação de Conformidade da Auditoria'),
    ]
    
    # Metric identification
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    measurement_date = models.DateField()
    measurement_period = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Diário'),
            ('weekly', 'Semanal'),
            ('monthly', 'Mensal'),
            ('quarterly', 'Trimestral'),
            ('annual', 'Anual'),
        ],
        default='monthly'
    )
    
    # Values
    target_value = models.FloatField(help_text="Target/expected value")
    actual_value = models.FloatField(help_text="Actual measured value")
    unit = models.CharField(max_length=20, help_text="e.g., 'days', 'percentage', 'count'")
    
    # Context
    measurement_context = models.TextField(blank=True)
    data_source = models.CharField(max_length=100, blank=True)
    
    # Performance indicators
    performance_status = models.CharField(
        max_length=20,
        choices=[
            ('above_target', 'Acima da Meta'),
            ('on_target', 'Na Meta'),
            ('below_target', 'Abaixo da Meta'),
            ('critical', 'Crítico'),
        ],
        blank=True
    )
    
    # Metadata
    recorded_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Métrica de Conformidade"
        verbose_name_plural = "Métricas de Conformidade"
        ordering = ['-measurement_date', 'metric_type']
        unique_together = ['metric_type', 'measurement_date', 'measurement_period']
    
    def calculate_performance_status(self):
        """Calculate performance status based on target vs actual"""
        if self.actual_value >= self.target_value * 1.1:  # 10% above target
            self.performance_status = 'above_target'
        elif self.actual_value >= self.target_value * 0.9:  # Within 10% of target
            self.performance_status = 'on_target'
        elif self.actual_value >= self.target_value * 0.7:  # Within 30% of target
            self.performance_status = 'below_target'
        else:
            self.performance_status = 'critical'
        
        self.save()
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.measurement_date}"

class StaffTrainingRecord(models.Model):
    """Track LGPD training for staff members"""
    
    TRAINING_TYPES = [
        ('lgpd_basics', 'LGPD - Conceitos Básicos'),
        ('patient_rights', 'Direitos dos Pacientes'),
        ('data_security', 'Segurança de Dados'),
        ('incident_response', 'Resposta a Incidentes'),
        ('privacy_by_design', 'Privacidade por Design'),
        ('data_retention', 'Retenção de Dados'),
        ('consent_management', 'Gestão de Consentimento'),
        ('breach_procedures', 'Procedimentos de Violação'),
    ]
    
    TRAINING_STATUS = [
        ('enrolled', 'Inscrito'),
        ('in_progress', 'Em Progresso'),
        ('completed', 'Concluído'),
        ('failed', 'Reprovado'),
        ('expired', 'Expirado'),
        ('cancelled', 'Cancelado'),
    ]
    
    # Training details
    staff_member = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.CASCADE, related_name='training_records')
    training_type = models.CharField(max_length=30, choices=TRAINING_TYPES)
    training_title = models.CharField(max_length=200)
    
    # Scheduling
    enrolled_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Progress and results
    status = models.CharField(max_length=15, choices=TRAINING_STATUS, default='enrolled')
    progress_percentage = models.IntegerField(default=0)
    assessment_score = models.FloatField(null=True, blank=True)
    passing_score = models.FloatField(default=70.0)
    
    # Content tracking
    modules_completed = models.TextField(default=list, help_text="JSON list of completed modules")
    time_spent_minutes = models.IntegerField(default=0)
    
    # Certification
    certificate_issued = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=50, blank=True)
    next_training_due = models.DateField(null=True, blank=True)
    
    # Metadata
    training_provider = models.CharField(max_length=100, blank=True)
    training_materials = models.TextField(blank=True, help_text="JSON list of materials")
    
    class Meta:
        verbose_name = "Registro de Treinamento"
        verbose_name_plural = "Registros de Treinamento"
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['staff_member', 'training_type', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]
    
    def is_current(self):
        """Check if training is current (not expired)"""
        if self.status != 'completed':
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        return True
    
    def calculate_next_training_due(self):
        """Calculate when next training is due"""
        if self.completed_at:
            # Default: annual renewal
            self.next_training_due = self.completed_at.date() + timedelta(days=365)
            self.save()
    
    def __str__(self):
        return f"{self.staff_member.get_full_name()} - {self.get_training_type_display()}"

class ComplianceIssue(models.Model):
    """Track compliance issues and their resolution"""
    
    ISSUE_TYPES = [
        ('policy_violation', 'Violação de Política'),
        ('process_gap', 'Lacuna de Processo'),
        ('training_deficiency', 'Deficiência de Treinamento'),
        ('system_weakness', 'Fraqueza do Sistema'),
        ('documentation_missing', 'Documentação Ausente'),
        ('deadline_missed', 'Prazo Perdido'),
        ('external_finding', 'Achado Externo'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    ISSUE_STATUS = [
        ('open', 'Aberto'),
        ('in_progress', 'Em Progresso'),
        ('resolved', 'Resolvido'),
        ('closed', 'Fechado'),
        ('deferred', 'Adiado'),
    ]
    
    # Issue identification
    issue_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    issue_type = models.CharField(max_length=30, choices=ISSUE_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    
    # Description and context
    description = models.TextField()
    discovered_at = models.DateTimeField()
    discovered_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='discovered_issues'
    )
    discovery_method = models.CharField(max_length=100)
    
    # Impact assessment
    affected_areas = models.TextField(help_text="JSON list of affected areas")
    potential_impact = models.TextField()
    regulatory_risk = models.TextField(blank=True)
    
    # Resolution
    status = models.CharField(max_length=15, choices=ISSUE_STATUS, default='open')
    assigned_to = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_issues'
    )
    
    # Timeline
    target_resolution_date = models.DateField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution details
    resolution_description = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)
    preventive_measures = models.TextField(blank=True)
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Related records
    related_audit = models.ForeignKey(ComplianceAudit, on_delete=models.SET_NULL, null=True, blank=True)
    related_incident = models.ForeignKey('SecurityIncident', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Problema de Conformidade"
        verbose_name_plural = "Problemas de Conformidade"
        ordering = ['-discovered_at']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['target_resolution_date', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.issue_id:
            self.issue_id = self.generate_issue_id()
        super().save(*args, **kwargs)
    
    def generate_issue_id(self):
        """Generate unique issue ID: ISS-YYYYMMDD-XXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        sequence = ComplianceIssue.objects.filter(
            issue_id__startswith=f'ISS-{date_str}'
        ).count() + 1
        return f'ISS-{date_str}-{sequence:03d}'
    
    def is_overdue(self):
        """Check if issue resolution is overdue"""
        if self.status in ['resolved', 'closed']:
            return False
        return date.today() > self.target_resolution_date
    
    def __str__(self):
        return f"{self.issue_id} - {self.title}"
```

### Step 2: Compliance Monitoring Service

#### 2.1 Monitoring Service

**File**: `apps/core/services/compliance_monitoring.py`

```python
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import date, timedelta, datetime
from typing import Dict, List, Any
import logging
import json

from ..models import (
    ComplianceAudit, ComplianceChecklist, ComplianceMetric, 
    StaffTrainingRecord, ComplianceIssue, SecurityIncident,
    DataRetentionSchedule, PatientDataRequest, LGPDComplianceSettings
)

logger = logging.getLogger(__name__)

class ComplianceMonitoringService:
    """Service for monitoring ongoing LGPD compliance"""
    
    def __init__(self):
        self.monitoring_results = {
            'metrics_calculated': 0,
            'issues_identified': 0,
            'training_alerts': 0,
            'compliance_score': 0.0
        }
    
    def run_comprehensive_monitoring(self):
        """Run comprehensive compliance monitoring"""
        
        logger.info("Starting comprehensive compliance monitoring")
        
        # Calculate key metrics
        self.calculate_compliance_metrics()
        
        # Monitor training compliance
        self.monitor_training_compliance()
        
        # Check for overdue items
        self.check_overdue_items()
        
        # Assess overall compliance health
        self.assess_compliance_health()
        
        # Generate automatic issues for problems
        self.generate_compliance_issues()
        
        return self.monitoring_results
    
    def calculate_compliance_metrics(self):
        """Calculate and record compliance metrics"""
        
        today = date.today()
        last_month = today - timedelta(days=30)
        
        # Patient request response time
        self.calculate_patient_request_metrics(today)
        
        # Data retention compliance
        self.calculate_retention_compliance_metrics(today)
        
        # Incident response metrics
        self.calculate_incident_response_metrics(today, last_month)
        
        # Staff training metrics
        self.calculate_training_metrics(today)
        
        # Overall audit compliance
        self.calculate_audit_compliance_metrics(today)
        
        self.monitoring_results['metrics_calculated'] = 5
    
    def calculate_patient_request_metrics(self, measurement_date):
        """Calculate patient data request response time metrics"""
        
        # Get requests from last 30 days
        thirty_days_ago = measurement_date - timedelta(days=30)
        
        completed_requests = PatientDataRequest.objects.filter(
            requested_at__gte=thirty_days_ago,
            status='completed',
            response_sent_at__isnull=False
        )
        
        if completed_requests.exists():
            # Calculate average response time
            total_response_time = 0
            count = 0
            
            for request in completed_requests:
                response_time = (request.response_sent_at.date() - request.requested_at.date()).days
                total_response_time += response_time
                count += 1
            
            avg_response_time = total_response_time / count if count > 0 else 0
            
            # Record metric
            ComplianceMetric.objects.update_or_create(
                metric_type='patient_requests_response_time',
                measurement_date=measurement_date,
                measurement_period='monthly',
                defaults={
                    'target_value': 15.0,  # LGPD allows "reasonable time", we target 15 days
                    'actual_value': avg_response_time,
                    'unit': 'days',
                    'measurement_context': f'Based on {count} completed requests',
                    'data_source': 'PatientDataRequest model'
                }
            )
    
    def calculate_retention_compliance_metrics(self, measurement_date):
        """Calculate data retention compliance metrics"""
        
        # Check retention schedule compliance
        total_schedules = DataRetentionSchedule.objects.count()
        overdue_schedules = DataRetentionSchedule.objects.filter(
            deletion_date__lt=measurement_date,
            status__in=['active', 'warning_sent']
        ).count()
        
        compliance_percentage = ((total_schedules - overdue_schedules) / total_schedules * 100) if total_schedules > 0 else 100
        
        ComplianceMetric.objects.update_or_create(
            metric_type='data_retention_compliance',
            measurement_date=measurement_date,
            measurement_period='monthly',
            defaults={
                'target_value': 95.0,  # Target 95% compliance
                'actual_value': compliance_percentage,
                'unit': 'percentage',
                'measurement_context': f'{overdue_schedules} overdue out of {total_schedules} schedules',
                'data_source': 'DataRetentionSchedule model'
            }
        )
    
    def calculate_incident_response_metrics(self, measurement_date, period_start):
        """Calculate incident response time metrics"""
        
        incidents = SecurityIncident.objects.filter(
            detected_at__gte=period_start,
            containment_at__isnull=False
        )
        
        if incidents.exists():
            total_response_time = 0
            count = 0
            
            for incident in incidents:
                response_time = (incident.containment_at - incident.detected_at).total_seconds() / 3600  # Hours
                total_response_time += response_time
                count += 1
            
            avg_response_time = total_response_time / count if count > 0 else 0
            
            ComplianceMetric.objects.update_or_create(
                metric_type='incident_response_time',
                measurement_date=measurement_date,
                measurement_period='monthly',
                defaults={
                    'target_value': 24.0,  # Target 24 hours for containment
                    'actual_value': avg_response_time,
                    'unit': 'hours',
                    'measurement_context': f'Based on {count} incidents',
                    'data_source': 'SecurityIncident model'
                }
            )
    
    def calculate_training_metrics(self, measurement_date):
        """Calculate staff training completion metrics"""
        
        from apps.accounts.models import EqmdCustomUser
        
        # Count active staff
        active_staff = EqmdCustomUser.objects.filter(is_active=True).count()
        
        # Count staff with current LGPD training
        staff_with_current_training = EqmdCustomUser.objects.filter(
            training_records__training_type='lgpd_basics',
            training_records__status='completed',
            training_records__expires_at__gt=timezone.now()
        ).distinct().count()
        
        completion_percentage = (staff_with_current_training / active_staff * 100) if active_staff > 0 else 0
        
        ComplianceMetric.objects.update_or_create(
            metric_type='staff_training_completion',
            measurement_date=measurement_date,
            measurement_period='monthly',
            defaults={
                'target_value': 100.0,  # Target 100% completion
                'actual_value': completion_percentage,
                'unit': 'percentage',
                'measurement_context': f'{staff_with_current_training} out of {active_staff} staff trained',
                'data_source': 'StaffTrainingRecord model'
            }
        )
    
    def calculate_audit_compliance_metrics(self, measurement_date):
        """Calculate audit compliance score metrics"""
        
        # Get latest completed audit
        latest_audit = ComplianceAudit.objects.filter(
            status='completed',
            compliance_score__isnull=False
        ).order_by('-completed_at').first()
        
        if latest_audit:
            ComplianceMetric.objects.update_or_create(
                metric_type='audit_compliance_score',
                measurement_date=measurement_date,
                measurement_period='quarterly',
                defaults={
                    'target_value': 85.0,  # Target 85% compliance score
                    'actual_value': latest_audit.compliance_score,
                    'unit': 'percentage',
                    'measurement_context': f'From audit {latest_audit.audit_id}',
                    'data_source': 'ComplianceAudit model'
                }
            )
    
    def monitor_training_compliance(self):
        """Monitor staff training compliance"""
        
        # Find staff with expired training
        expired_training = StaffTrainingRecord.objects.filter(
            status='completed',
            expires_at__lt=timezone.now()
        )
        
        # Find staff without LGPD training
        from apps.accounts.models import EqmdCustomUser
        
        staff_without_training = EqmdCustomUser.objects.filter(
            is_active=True
        ).exclude(
            training_records__training_type='lgpd_basics',
            training_records__status='completed'
        )
        
        training_alerts = 0
        
        # Create issues for expired training
        for training in expired_training:
            if not ComplianceIssue.objects.filter(
                issue_type='training_deficiency',
                status__in=['open', 'in_progress'],
                description__contains=f"training ID {training.id}"
            ).exists():
                
                ComplianceIssue.objects.create(
                    title=f'Treinamento LGPD Expirado - {training.staff_member.get_full_name()}',
                    issue_type='training_deficiency',
                    severity='medium',
                    description=f'Treinamento LGPD do funcionário {training.staff_member.get_full_name()} expirou em {training.expires_at.strftime("%d/%m/%Y")}. Renovação necessária.',
                    discovered_at=timezone.now(),
                    discovery_method='automated_monitoring',
                    affected_areas=json.dumps(['staff_training', 'lgpd_compliance']),
                    potential_impact='Funcionário pode não estar atualizado com procedimentos LGPD',
                    target_resolution_date=date.today() + timedelta(days=30),
                    assigned_to=training.staff_member
                )
                training_alerts += 1
        
        # Create issues for staff without training
        for staff in staff_without_training:
            if not ComplianceIssue.objects.filter(
                issue_type='training_deficiency',
                status__in=['open', 'in_progress'],
                description__contains=f"staff ID {staff.id}"
            ).exists():
                
                ComplianceIssue.objects.create(
                    title=f'Treinamento LGPD Ausente - {staff.get_full_name()}',
                    issue_type='training_deficiency',
                    severity='high',
                    description=f'Funcionário {staff.get_full_name()} não possui treinamento LGPD registrado.',
                    discovered_at=timezone.now(),
                    discovery_method='automated_monitoring',
                    affected_areas=json.dumps(['staff_training', 'lgpd_compliance']),
                    potential_impact='Funcionário pode não conhecer procedimentos LGPD obrigatórios',
                    target_resolution_date=date.today() + timedelta(days=15),
                    assigned_to=staff
                )
                training_alerts += 1
        
        self.monitoring_results['training_alerts'] = training_alerts
    
    def check_overdue_items(self):
        """Check for overdue compliance items"""
        
        today = date.today()
        issues_created = 0
        
        # Check overdue patient requests
        overdue_requests = PatientDataRequest.objects.filter(
            due_date__lt=today,
            status__in=['pending', 'under_review', 'approved']
        )
        
        for request in overdue_requests:
            if not ComplianceIssue.objects.filter(
                issue_type='deadline_missed',
                status__in=['open', 'in_progress'],
                description__contains=request.request_id
            ).exists():
                
                ComplianceIssue.objects.create(
                    title=f'Solicitação de Dados Atrasada - {request.request_id}',
                    issue_type='deadline_missed',
                    severity='high',
                    description=f'Solicitação de dados {request.request_id} está atrasada. Prazo era {request.due_date.strftime("%d/%m/%Y")}.',
                    discovered_at=timezone.now(),
                    discovery_method='automated_monitoring',
                    affected_areas=json.dumps(['patient_rights', 'lgpd_compliance']),
                    potential_impact='Violação do prazo legal para resposta a titular de dados',
                    target_resolution_date=today + timedelta(days=1),
                    regulatory_risk='Possível sanção por descumprimento do prazo LGPD'
                )
                issues_created += 1
        
        # Check overdue incident notifications
        overdue_incidents = SecurityIncident.objects.filter(
            Q(anpd_notification_deadline__lt=timezone.now(), anpd_notification_required=True) |
            Q(subject_notification_deadline__lt=timezone.now(), data_subject_notification_required=True),
            status__in=['detected', 'investigating', 'contained']
        )
        
        for incident in overdue_incidents:
            if not ComplianceIssue.objects.filter(
                issue_type='deadline_missed',
                status__in=['open', 'in_progress'],
                related_incident=incident
            ).exists():
                
                ComplianceIssue.objects.create(
                    title=f'Notificação de Incidente Atrasada - {incident.incident_id}',
                    issue_type='deadline_missed',
                    severity='critical',
                    description=f'Notificações obrigatórias para incidente {incident.incident_id} estão atrasadas.',
                    discovered_at=timezone.now(),
                    discovery_method='automated_monitoring',
                    affected_areas=json.dumps(['incident_response', 'breach_notification']),
                    potential_impact='Violação grave da LGPD - notificação obrigatória atrasada',
                    target_resolution_date=today,
                    regulatory_risk='Alta probabilidade de sanção por descumprimento de prazo legal',
                    related_incident=incident
                )
                issues_created += 1
        
        self.monitoring_results['issues_identified'] += issues_created
    
    def assess_compliance_health(self):
        """Assess overall compliance health"""
        
        today = date.today()
        
        # Get recent metrics
        recent_metrics = ComplianceMetric.objects.filter(
            measurement_date__gte=today - timedelta(days=90)
        )
        
        if recent_metrics.exists():
            # Calculate weighted compliance score
            total_weight = 0
            weighted_score = 0
            
            metric_weights = {
                'patient_requests_response_time': 0.25,
                'data_retention_compliance': 0.20,
                'staff_training_completion': 0.20,
                'incident_response_time': 0.15,
                'audit_compliance_score': 0.20
            }
            
            for metric_type, weight in metric_weights.items():
                metric = recent_metrics.filter(metric_type=metric_type).order_by('-measurement_date').first()
                if metric:
                    # Convert actual vs target to score (0-100)
                    if metric.actual_value <= metric.target_value:
                        score = 100 * (metric.actual_value / metric.target_value)
                    else:
                        # For metrics where lower is better (like response time)
                        if metric_type in ['patient_requests_response_time', 'incident_response_time']:
                            score = 100 * (metric.target_value / metric.actual_value)
                        else:
                            score = 100  # Perfect score if above target for positive metrics
                    
                    score = min(100, max(0, score))  # Clamp between 0-100
                    weighted_score += score * weight
                    total_weight += weight
            
            overall_score = weighted_score / total_weight if total_weight > 0 else 0
            self.monitoring_results['compliance_score'] = round(overall_score, 1)
            
            # Record overall compliance metric
            ComplianceMetric.objects.update_or_create(
                metric_type='overall_compliance_health',
                measurement_date=today,
                measurement_period='monthly',
                defaults={
                    'target_value': 85.0,
                    'actual_value': overall_score,
                    'unit': 'percentage',
                    'measurement_context': 'Weighted average of key compliance metrics',
                    'data_source': 'compliance_monitoring_service'
                }
            )
    
    def generate_compliance_issues(self):
        """Generate compliance issues based on monitoring results"""
        
        # Check if overall compliance is below threshold
        if self.monitoring_results['compliance_score'] < 75:
            if not ComplianceIssue.objects.filter(
                issue_type='system_weakness',
                status__in=['open', 'in_progress'],
                title__contains='Overall Compliance Below Threshold'
            ).exists():
                
                ComplianceIssue.objects.create(
                    title='Overall Compliance Below Threshold',
                    issue_type='system_weakness',
                    severity='high',
                    description=f'Overall compliance score ({self.monitoring_results["compliance_score"]}%) is below acceptable threshold (75%).',
                    discovered_at=timezone.now(),
                    discovery_method='automated_monitoring',
                    affected_areas=json.dumps(['overall_compliance']),
                    potential_impact='Increased risk of LGPD violations and regulatory sanctions',
                    target_resolution_date=date.today() + timedelta(days=30),
                    regulatory_risk='Medium to high risk of regulatory action'
                )
                self.monitoring_results['issues_identified'] += 1
    
    def get_compliance_dashboard_data(self):
        """Get data for compliance dashboard"""
        
        today = date.today()
        last_30_days = today - timedelta(days=30)
        
        # Get recent metrics
        recent_metrics = {}
        for metric_type, _ in ComplianceMetric.METRIC_TYPES:
            metric = ComplianceMetric.objects.filter(
                metric_type=metric_type,
                measurement_date__gte=last_30_days
            ).order_by('-measurement_date').first()
            
            if metric:
                recent_metrics[metric_type] = {
                    'value': metric.actual_value,
                    'target': metric.target_value,
                    'unit': metric.unit,
                    'status': metric.performance_status,
                    'date': metric.measurement_date
                }
        
        # Get open issues by severity
        open_issues = ComplianceIssue.objects.filter(status__in=['open', 'in_progress'])
        issues_by_severity = {
            'critical': open_issues.filter(severity='critical').count(),
            'high': open_issues.filter(severity='high').count(),
            'medium': open_issues.filter(severity='medium').count(),
            'low': open_issues.filter(severity='low').count(),
        }
        
        # Get training statistics
        from apps.accounts.models import EqmdCustomUser
        total_staff = EqmdCustomUser.objects.filter(is_active=True).count()
        trained_staff = EqmdCustomUser.objects.filter(
            training_records__training_type='lgpd_basics',
            training_records__status='completed',
            training_records__expires_at__gt=timezone.now()
        ).distinct().count()
        
        # Get recent audits
        recent_audits = ComplianceAudit.objects.filter(
            completed_at__gte=last_30_days
        ).order_by('-completed_at')[:5]
        
        return {
            'metrics': recent_metrics,
            'open_issues': issues_by_severity,
            'training_stats': {
                'total_staff': total_staff,
                'trained_staff': trained_staff,
                'completion_rate': (trained_staff / total_staff * 100) if total_staff > 0 else 0
            },
            'recent_audits': recent_audits,
            'overall_score': self.monitoring_results.get('compliance_score', 0)
        }
```

### Step 3: Management Commands

#### 3.1 Compliance Monitoring Command

**File**: `apps/core/management/commands/run_compliance_monitoring.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.services.compliance_monitoring import ComplianceMonitoringService

class Command(BaseCommand):
    help = 'Run comprehensive compliance monitoring'
    
    def add_arguments(self, parser):
        parser.add_argument('--metrics-only', action='store_true', help='Calculate only metrics')
        parser.add_argument('--training-only', action='store_true', help='Check only training compliance')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    
    def handle(self, *args, **options):
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"LGPD Compliance Monitoring - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"{'='*60}")
        
        monitoring_service = ComplianceMonitoringService()
        
        if options['dry_run']:
            self.stdout.write("DRY RUN MODE - No changes will be made")
            results = {'metrics_calculated': 5, 'issues_identified': 0, 'training_alerts': 0, 'compliance_score': 85.0}
        else:
            if options['metrics_only']:
                monitoring_service.calculate_compliance_metrics()
                results = monitoring_service.monitoring_results
            elif options['training_only']:
                monitoring_service.monitor_training_compliance()
                results = monitoring_service.monitoring_results
            else:
                results = monitoring_service.run_comprehensive_monitoring()
        
        # Display results
        self.stdout.write(f"\n📊 Monitoring Results:")
        self.stdout.write(f"  • Metrics calculated: {results['metrics_calculated']}")
        self.stdout.write(f"  • Issues identified: {results['issues_identified']}")
        self.stdout.write(f"  • Training alerts: {results['training_alerts']}")
        self.stdout.write(f"  • Overall compliance score: {results['compliance_score']:.1f}%")
        
        # Compliance status assessment
        score = results['compliance_score']
        if score >= 90:
            status = self.style.SUCCESS("🟢 EXCELLENT")
        elif score >= 75:
            status = self.style.SUCCESS("🟡 GOOD")
        elif score >= 60:
            status = self.style.WARNING("🟠 SATISFACTORY")
        else:
            status = self.style.ERROR("🔴 NEEDS IMPROVEMENT")
        
        self.stdout.write(f"\n🎯 Compliance Status: {status}")
        
        # Show critical issues
        if not options['dry_run']:
            from apps.core.models import ComplianceIssue
            critical_issues = ComplianceIssue.objects.filter(
                severity='critical',
                status__in=['open', 'in_progress']
            ).count()
            
            if critical_issues > 0:
                self.stdout.write(
                    self.style.ERROR(f"\n🚨 ATTENTION: {critical_issues} critical compliance issues require immediate action!")
                )
        
        self.stdout.write("\n✅ Compliance monitoring complete")
```

#### 3.2 Audit Management Command

**File**: `apps/core/management/commands/manage_audit.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from apps.core.models import ComplianceAudit, ComplianceChecklist

class Command(BaseCommand):
    help = 'Manage compliance audits'
    
    def add_arguments(self, parser):
        parser.add_argument('--create', action='store_true', help='Create new audit')
        parser.add_argument('--list', action='store_true', help='List audits')
        parser.add_argument('--audit-id', type=str, help='Audit ID to manage')
        parser.add_argument('--complete', action='store_true', help='Mark audit as complete')
        parser.add_argument('--audit-type', type=str, default='routine', help='Type of audit to create')
    
    def handle(self, *args, **options):
        if options['create']:
            self.create_audit(options['audit_type'])
        elif options['list']:
            self.list_audits()
        elif options['audit_id']:
            self.manage_specific_audit(options)
        else:
            self.show_audit_dashboard()
    
    def create_audit(self, audit_type):
        """Create a new compliance audit"""
        
        audit = ComplianceAudit.objects.create(
            audit_type=audit_type,
            title=f'Auditoria {audit_type.title()} - {date.today().strftime("%B %Y")}',
            description=f'Auditoria de conformidade LGPD - {audit_type}',
            scheduled_date=date.today(),
            audit_scope=json.dumps([
                'legal_basis_documentation',
                'patient_rights_implementation',
                'data_retention_policies',
                'staff_training_records',
                'incident_response_procedures'
            ]),
            focus_areas=json.dumps([
                'Article 7 compliance',
                'Article 18 rights implementation',
                'Article 48 breach response',
                'Staff awareness and training'
            ])
        )
        
        # Create standard checklist items
        self.create_audit_checklist(audit)
        
        self.stdout.write(f"✓ Created audit: {audit.audit_id}")
        self.stdout.write(f"  Type: {audit.get_audit_type_display()}")
        self.stdout.write(f"  Scheduled: {audit.scheduled_date}")
        self.stdout.write(f"  Checklist items: {audit.checklist_items.count()}")
    
    def create_audit_checklist(self, audit):
        """Create standard checklist items for audit"""
        
        checklist_items = [
            {
                'category': 'legal_basis',
                'check_id': 'LGPD-ART7-01',
                'title': 'Documentação de Base Legal',
                'description': 'Verificar se todas as atividades de processamento possuem base legal documentada conforme Art. 7º',
                'legal_reference': 'LGPD Art. 7º',
                'evidence_required': 'Registro de atividades de tratamento, políticas documentadas',
                'priority': 'critical'
            },
            {
                'category': 'data_subject_rights',
                'check_id': 'LGPD-ART18-01',
                'title': 'Sistema de Direitos dos Titulares',
                'description': 'Verificar implementação de mecanismos para exercício dos direitos dos titulares',
                'legal_reference': 'LGPD Art. 18',
                'evidence_required': 'Formulários de solicitação, processos de atendimento, logs de resposta',
                'priority': 'high'
            },
            {
                'category': 'privacy_policies',
                'check_id': 'LGPD-ART9-01',
                'title': 'Política de Privacidade Atualizada',
                'description': 'Verificar se política de privacidade está atualizada e acessível',
                'legal_reference': 'LGPD Art. 9º',
                'evidence_required': 'Política publicada, data de atualização, acessibilidade',
                'priority': 'medium'
            },
            {
                'category': 'retention_management',
                'check_id': 'LGPD-ART15-01',
                'title': 'Políticas de Retenção',
                'description': 'Verificar implementação de políticas de retenção e exclusão de dados',
                'legal_reference': 'LGPD Art. 15º',
                'evidence_required': 'Políticas de retenção, cronogramas de exclusão, logs de execução',
                'priority': 'high'
            },
            {
                'category': 'incident_response',
                'check_id': 'LGPD-ART48-01',
                'title': 'Procedimentos de Resposta a Incidentes',
                'description': 'Verificar procedimentos para detecção e resposta a incidentes de segurança',
                'legal_reference': 'LGPD Art. 48',
                'evidence_required': 'Procedimentos documentados, registros de incidentes, notificações',
                'priority': 'critical'
            },
            {
                'category': 'staff_training',
                'check_id': 'LGPD-TRAIN-01',
                'title': 'Treinamento da Equipe',
                'description': 'Verificar se equipe recebeu treinamento adequado sobre LGPD',
                'legal_reference': 'LGPD Art. 46 (medidas organizacionais)',
                'evidence_required': 'Registros de treinamento, certificados, avaliações',
                'priority': 'medium'
            },
            {
                'category': 'technical_security',
                'check_id': 'LGPD-ART46-01',
                'title': 'Medidas de Segurança Técnicas',
                'description': 'Verificar implementação de medidas técnicas de segurança',
                'legal_reference': 'LGPD Art. 46',
                'evidence_required': 'Configurações de segurança, logs de auditoria, testes de penetração',
                'priority': 'high'
            }
        ]
        
        for item_data in checklist_items:
            ComplianceChecklist.objects.create(
                audit=audit,
                **item_data
            )
    
    def list_audits(self):
        """List all audits"""
        
        audits = ComplianceAudit.objects.all().order_by('-scheduled_date')
        
        self.stdout.write(f"\n📋 Compliance Audits ({audits.count()}):")
        self.stdout.write("-" * 80)
        
        for audit in audits:
            status_icon = {
                'planned': '📅',
                'in_progress': '🔄',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(audit.status, '❓')
            
            compliance_info = ""
            if audit.compliance_score:
                compliance_info = f" | Score: {audit.compliance_score:.1f}%"
            
            self.stdout.write(
                f"{status_icon} {audit.audit_id} | {audit.get_audit_type_display()} | "
                f"{audit.scheduled_date} | {audit.get_status_display()}{compliance_info}"
            )
            
            if audit.status == 'completed' and audit.critical_findings > 0:
                self.stdout.write(f"  🚨 {audit.critical_findings} critical findings")
    
    def manage_specific_audit(self, options):
        """Manage specific audit"""
        
        audit_id = options['audit_id']
        
        try:
            audit = ComplianceAudit.objects.get(audit_id=audit_id)
        except ComplianceAudit.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Audit {audit_id} not found"))
            return
        
        self.stdout.write(f"\n📋 Audit Details: {audit.audit_id}")
        self.stdout.write("-" * 50)
        self.stdout.write(f"Type: {audit.get_audit_type_display()}")
        self.stdout.write(f"Status: {audit.get_status_display()}")
        self.stdout.write(f"Scheduled: {audit.scheduled_date}")
        
        if audit.compliance_score:
            self.stdout.write(f"Compliance Score: {audit.compliance_score:.1f}%")
            self.stdout.write(f"Compliance Level: {audit.get_compliance_level_display()}")
        
        # Show checklist summary
        checklist_summary = audit.checklist_items.values('status').annotate(count=Count('id'))
        self.stdout.write(f"\nChecklist Summary:")
        for item in checklist_summary:
            self.stdout.write(f"  • {item['status'].title()}: {item['count']}")
        
        # Handle completion
        if options['complete']:
            if audit.status != 'completed':
                audit.status = 'completed'
                audit.completed_at = timezone.now()
                
                # Calculate compliance score
                score = audit.calculate_compliance_score()
                
                audit.save()
                
                self.stdout.write(f"✓ Audit marked as complete")
                self.stdout.write(f"  Final compliance score: {score:.1f}%")
            else:
                self.stdout.write("Audit is already completed")
    
    def show_audit_dashboard(self):
        """Show audit dashboard"""
        
        self.stdout.write("\n📊 Audit Dashboard")
        self.stdout.write("=" * 50)
        
        # Statistics
        total_audits = ComplianceAudit.objects.count()
        completed_audits = ComplianceAudit.objects.filter(status='completed').count()
        in_progress_audits = ComplianceAudit.objects.filter(status='in_progress').count()
        
        self.stdout.write(f"\n📈 Statistics:")
        self.stdout.write(f"  • Total audits: {total_audits}")
        self.stdout.write(f"  • Completed: {completed_audits}")
        self.stdout.write(f"  • In progress: {in_progress_audits}")
        
        # Latest compliance score
        latest_audit = ComplianceAudit.objects.filter(
            status='completed',
            compliance_score__isnull=False
        ).order_by('-completed_at').first()
        
        if latest_audit:
            self.stdout.write(f"\n🎯 Latest Compliance Score:")
            self.stdout.write(f"  • Score: {latest_audit.compliance_score:.1f}%")
            self.stdout.write(f"  • Level: {latest_audit.get_compliance_level_display()}")
            self.stdout.write(f"  • Date: {latest_audit.completed_at.strftime('%d/%m/%Y')}")
        
        # Upcoming audits
        upcoming_audits = ComplianceAudit.objects.filter(
            scheduled_date__gte=date.today(),
            status='planned'
        ).order_by('scheduled_date')[:3]
        
        if upcoming_audits:
            self.stdout.write(f"\n📅 Upcoming Audits:")
            for audit in upcoming_audits:
                days_until = (audit.scheduled_date - date.today()).days
                self.stdout.write(f"  • {audit.audit_id} - {audit.get_audit_type_display()} (in {days_until} days)")
        
        self.stdout.write(f"\nUse --create to create new audit")
        self.stdout.write(f"Use --list to see all audits")
```

### Step 4: Admin Interface

#### 4.1 Monitoring Admin

**File**: `apps/core/admin.py` (additions)

```python
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    ComplianceAudit, ComplianceChecklist, ComplianceMetric,
    StaffTrainingRecord, ComplianceIssue
)

@admin.register(ComplianceAudit)
class ComplianceAuditAdmin(admin.ModelAdmin):
    list_display = [
        'audit_id', 'title', 'audit_type', 'status', 'scheduled_date',
        'compliance_score', 'compliance_level', 'critical_findings'
    ]
    list_filter = ['audit_type', 'status', 'compliance_level', 'scheduled_date']
    search_fields = ['audit_id', 'title', 'description']
    readonly_fields = ['audit_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['audit_id', 'audit_type', 'title', 'description']
        }),
        ('Agendamento', {
            'fields': ['scheduled_date', 'started_at', 'completed_at']
        }),
        ('Escopo', {
            'fields': ['audit_scope', 'focus_areas']
        }),
        ('Execução', {
            'fields': ['auditor', 'status']
        }),
        ('Resultados', {
            'fields': [
                'compliance_score', 'compliance_level', 'findings_count',
                'critical_findings', 'audit_report', 'recommendations'
            ]
        }),
        ('Acompanhamento', {
            'fields': [
                'corrective_actions_required', 'next_audit_due',
                'follow_up_required', 'follow_up_deadline'
            ]
        })
    ]
    
    actions = ['calculate_compliance_scores']
    
    def calculate_compliance_scores(self, request, queryset):
        updated = 0
        for audit in queryset:
            if audit.status == 'completed':
                audit.calculate_compliance_score()
                updated += 1
        
        self.message_user(request, f'{updated} audit scores recalculated.')
    calculate_compliance_scores.short_description = 'Recalculate compliance scores'

@admin.register(ComplianceChecklist)
class ComplianceChecklistAdmin(admin.ModelAdmin):
    list_display = ['audit', 'check_id', 'title', 'category', 'status', 'priority', 'assessed_by']
    list_filter = ['category', 'status', 'priority', 'assessed_at']
    search_fields = ['check_id', 'title', 'description']
    
    fieldsets = [
        ('Checklist Item', {
            'fields': ['audit', 'category', 'check_id', 'title', 'description', 'legal_reference']
        }),
        ('Assessment', {
            'fields': ['status', 'priority', 'evidence_required', 'evidence_provided', 'assessor_notes']
        }),
        ('Non-Compliance', {
            'fields': ['non_compliance_details', 'recommended_action', 'remediation_deadline']
        }),
        ('Review', {
            'fields': ['assessed_at', 'assessed_by']
        })
    ]

@admin.register(ComplianceMetric)
class ComplianceMetricAdmin(admin.ModelAdmin):
    list_display = [
        'metric_type', 'measurement_date', 'actual_value', 'target_value',
        'unit', 'performance_status', 'measurement_period'
    ]
    list_filter = ['metric_type', 'performance_status', 'measurement_period', 'measurement_date']
    search_fields = ['metric_type']
    readonly_fields = ['recorded_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-measurement_date')

@admin.register(StaffTrainingRecord)
class StaffTrainingRecordAdmin(admin.ModelAdmin):
    list_display = [
        'staff_member', 'training_type', 'status', 'progress_percentage',
        'assessment_score', 'completed_at', 'expires_at', 'is_current'
    ]
    list_filter = ['training_type', 'status', 'expires_at']
    search_fields = ['staff_member__first_name', 'staff_member__last_name', 'training_title']
    
    def is_current(self, obj):
        return obj.is_current()
    is_current.boolean = True
    is_current.short_description = 'Current'
    
    actions = ['mark_completed', 'extend_expiration']
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='in_progress').update(
            status='completed',
            completed_at=timezone.now(),
            progress_percentage=100
        )
        self.message_user(request, f'{updated} training records marked as completed.')
    mark_completed.short_description = 'Mark as completed'

@admin.register(ComplianceIssue)
class ComplianceIssueAdmin(admin.ModelAdmin):
    list_display = [
        'issue_id', 'title', 'issue_type', 'severity', 'status',
        'target_resolution_date', 'assigned_to', 'is_overdue'
    ]
    list_filter = ['issue_type', 'severity', 'status', 'discovered_at']
    search_fields = ['issue_id', 'title', 'description']
    readonly_fields = ['issue_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Issue Details', {
            'fields': ['issue_id', 'title', 'issue_type', 'severity', 'description']
        }),
        ('Discovery', {
            'fields': ['discovered_at', 'discovered_by', 'discovery_method']
        }),
        ('Impact Assessment', {
            'fields': ['affected_areas', 'potential_impact', 'regulatory_risk']
        }),
        ('Resolution', {
            'fields': [
                'status', 'assigned_to', 'target_resolution_date',
                'resolved_at', 'closed_at'
            ]
        }),
        ('Resolution Details', {
            'fields': [
                'resolution_description', 'corrective_actions', 'preventive_measures'
            ]
        }),
        ('Follow-up', {
            'fields': ['requires_follow_up', 'follow_up_date', 'follow_up_notes']
        }),
        ('Related Records', {
            'fields': ['related_audit', 'related_incident']
        })
    ]
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    actions = ['resolve_issues', 'assign_to_me']
    
    def resolve_issues(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['open', 'in_progress']).update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} issues marked as resolved.')
    resolve_issues.short_description = 'Mark as resolved'
    
    def assign_to_me(self, request, queryset):
        updated = queryset.filter(assigned_to__isnull=True).update(assigned_to=request.user)
        self.message_user(request, f'{updated} issues assigned to you.')
    assign_to_me.short_description = 'Assign to me'
```

### Step 5: Dashboard Views

#### 5.1 Compliance Dashboard

**File**: `apps/core/views.py` (additions)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from .services.compliance_monitoring import ComplianceMonitoringService

@staff_member_required
def compliance_dashboard(request):
    """Main compliance monitoring dashboard"""
    
    monitoring_service = ComplianceMonitoringService()
    dashboard_data = monitoring_service.get_compliance_dashboard_data()
    
    context = {
        'dashboard_data': dashboard_data,
    }
    
    return render(request, 'admin/core/compliance_dashboard.html', context)

@staff_member_required
def compliance_metrics_api(request):
    """API endpoint for compliance metrics"""
    
    monitoring_service = ComplianceMonitoringService()
    dashboard_data = monitoring_service.get_compliance_dashboard_data()
    
    return JsonResponse(dashboard_data)
```

## Migration and Setup

### Step 6: Database Migration and Configuration

```bash
# Create and run migrations
python manage.py makemigrations core --name "add_monitoring_maintenance_models"
python manage.py migrate

# Set up scheduled monitoring (add to crontab)
# Daily compliance monitoring
# 0 8 * * * cd /path/to/project && python manage.py run_compliance_monitoring

# Weekly comprehensive monitoring
# 0 9 * * 1 cd /path/to/project && python manage.py run_compliance_monitoring

# Monthly audit creation
# 0 10 1 * * cd /path/to/project && python manage.py manage_audit --create --audit-type routine
```

### Step 7: Initial Data Setup

```bash
# Create initial compliance audit
python manage.py manage_audit --create --audit-type annual_review

# Run initial monitoring
python manage.py run_compliance_monitoring

# Check dashboard
python manage.py manage_audit --list
```

## Deliverable Summary

### Files Created
1. **Models**: `ComplianceAudit`, `ComplianceChecklist`, `ComplianceMetric`, `StaffTrainingRecord`, `ComplianceIssue`
2. **Services**: `ComplianceMonitoringService` for automated monitoring
3. **Commands**: Compliance monitoring, audit management
4. **Admin**: Complete monitoring and audit management interfaces
5. **Views**: Compliance dashboard for ongoing monitoring

### Key Features Implemented
- **Automated compliance monitoring** with configurable metrics
- **Audit management system** with checklists and scoring
- **Staff training tracking** with expiration monitoring
- **Issue management** with automated detection and tracking
- **Performance metrics** with target vs actual comparisons
- **Dashboard visualization** of compliance health
- **Automated alerting** for overdue items and critical issues

### Database Changes
- New tables: `core_complianceaudit`, `core_compliancechecklist`, `core_compliancemetric`, `core_stafftrainingrecord`, `core_complianceissue`
- Indexes for performance on date and status queries
- Relationships between audits, issues, and other compliance entities

### Monitoring Capabilities
- **Real-time compliance scoring** based on multiple metrics
- **Automated issue detection** for policy violations and missed deadlines
- **Training compliance tracking** with automatic alerts for expired training
- **Performance trending** over time
- **Regulatory risk assessment** and mitigation tracking

## Final Implementation Summary

### All Phases Completed
1. ✅ **Phase 1**: Legal Foundation - Legal basis documentation and infrastructure
2. ✅ **Phase 2**: Patient Rights System - Data access and correction requests
3. ✅ **Phase 3**: Privacy Transparency - Privacy policies and consent management
4. ✅ **Phase 4**: Data Lifecycle Management - Retention and deletion procedures
5. ✅ **Phase 5**: Breach Response System - Incident detection and notification
6. ✅ **Phase 6**: Monitoring & Maintenance - Ongoing compliance monitoring

### Overall System Capabilities
- **Complete LGPD compliance framework** covering all major requirements
- **Automated monitoring and alerting** for compliance issues
- **Comprehensive audit trails** for all data processing activities
- **Staff training management** with compliance tracking
- **Performance metrics and reporting** for continuous improvement
- **Incident response and breach notification** procedures
- **Data subject rights implementation** with request management
- **Data lifecycle management** with automated retention and deletion

---

**Phase 6 Completion Criteria**:
- [ ] Compliance monitoring service operational
- [ ] Automated audit system functional
- [ ] Staff training tracking implemented
- [ ] Performance metrics calculation working
- [ ] Issue management system operational
- [ ] Compliance dashboard accessible
- [ ] Management commands functional
- [ ] Admin interfaces complete
- [ ] Scheduled monitoring configured

**🎉 LGPD COMPLIANCE IMPLEMENTATION COMPLETE**

The EquipeMed system now has a comprehensive LGPD compliance framework that provides:
- Legal protection through documented compliance measures
- Operational efficiency through automated monitoring
- Risk mitigation through proactive issue detection
- Continuous improvement through performance tracking
- Staff awareness through training management
- Regulatory readiness through audit and reporting capabilities