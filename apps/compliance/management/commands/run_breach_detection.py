from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.compliance.services.breach_detection import BreachDetectionService
from apps.compliance.services.breach_notification import BreachNotificationService

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
            from apps.compliance.models import BreachNotification
            pending_count = BreachNotification.objects.filter(
                status='pending',
                scheduled_at__lte=timezone.now()
            ).count()
            self.stdout.write(f"DRY RUN: {pending_count} notifications would be processed")
        
        self.stdout.write("\n✅ Breach detection and notification processing complete")