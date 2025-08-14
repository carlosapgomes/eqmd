from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.compliance.models import SecurityIncident, IncidentAction
from apps.compliance.services.breach_notification import BreachNotificationService

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
            from apps.compliance.services.breach_detection import BreachDetectionService
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