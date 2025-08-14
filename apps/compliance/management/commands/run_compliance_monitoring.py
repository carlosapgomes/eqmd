from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.compliance.services.compliance_monitoring import ComplianceMonitoringService

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
            from apps.compliance.models import ComplianceIssue
            critical_issues = ComplianceIssue.objects.filter(
                severity='critical',
                status__in=['open', 'in_progress']
            ).count()
            
            if critical_issues > 0:
                self.stdout.write(
                    self.style.ERROR(f"\n🚨 ATTENTION: {critical_issues} critical compliance issues require immediate action!")
                )
        
        self.stdout.write("\n✅ Compliance monitoring complete")