from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import json
from apps.compliance.models import ComplianceAudit, ComplianceChecklist

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