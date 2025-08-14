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