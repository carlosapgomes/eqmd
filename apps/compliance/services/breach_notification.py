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
Status Atual: {incident.get_status_display()}"""

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

Escrevemos para informá-lo sobre um incidente de segurança que pode ter afetado alguns dos seus dados pessoais em nossos sistemas.

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