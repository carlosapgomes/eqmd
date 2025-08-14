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
        # Load configurable thresholds from LGPDComplianceSettings (Architectural Suggestion #4)
        self.settings = self._get_compliance_settings()
        self.detection_rules = {
            'failed_login_threshold': self.settings.breach_detection_failed_login_threshold,
            'bulk_access_threshold': self.settings.breach_detection_bulk_access_threshold,
            'off_hours_access_threshold': self.settings.breach_detection_off_hours_threshold,
            'geographic_anomaly_threshold': self.settings.breach_detection_geographic_anomaly_km,
            'data_export_threshold': self.settings.breach_detection_data_export_threshold,
        }
        
        self.risk_matrix = {
            ('unauthorized_access', 'high'): 'high',
            ('data_breach', 'medium'): 'high',
            ('data_loss', 'low'): 'medium',
            # Add more combinations as needed
        }
    
    def _get_compliance_settings(self):
        """Get LGPD compliance settings with configurable thresholds"""
        from ..models import LGPDComplianceSettings
        
        try:
            return LGPDComplianceSettings.objects.first()
        except LGPDComplianceSettings.DoesNotExist:
            # Return default instance if no settings exist
            return LGPDComplianceSettings()
    
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
        from ..models import PatientDataRequest
        
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
        
        try:
            lgpd_settings = self.settings
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