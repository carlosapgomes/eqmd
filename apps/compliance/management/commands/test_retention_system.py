from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.compliance.models import DataRetentionPolicy, DataRetentionSchedule, DataDeletionLog
from apps.compliance.services.retention_management import DataRetentionService
from apps.patients.models import Patient

User = get_user_model()

class Command(BaseCommand):
    help = 'Test data retention system with sample data'
    
    def add_arguments(self, parser):
        parser.add_argument('--create-test-data', action='store_true', help='Create test data')
        parser.add_argument('--run-retention', action='store_true', help='Run retention processing')
    
    def handle(self, *args, **options):
        if options['create_test_data']:
            self.create_test_data()
        
        if options['run_retention']:
            self.test_retention_processing()
        
        self.show_retention_overview()
    
    def create_test_data(self):
        """Create test patients with different retention scenarios"""
        
        self.stdout.write("Creating test data...")
        
        # Get or create a test user
        test_user, created = User.objects.get_or_create(
            username='test_retention_user',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Patient with old data (should trigger warning)
        old_patient = Patient.objects.create(
            name="Paciente Teste - Antigo",
            birthday=timezone.now().date() - timedelta(days=365*40),
            status=4,  # DISCHARGED
            created_by=test_user,
            updated_by=test_user
        )
        old_patient.last_interaction_date = timezone.now() - timedelta(days=7200)  # ~19.7 years ago
        old_patient.save()
        
        # Patient with recent data
        recent_patient = Patient.objects.create(
            name="Paciente Teste - Recente",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status=1,  # OUTPATIENT
            created_by=test_user,
            updated_by=test_user
        )
        
        # Patient with protection
        protected_patient = Patient.objects.create(
            name="Paciente Teste - Protegido",
            birthday=timezone.now().date() - timedelta(days=365*50),
            status=4,  # DISCHARGED
            deletion_protected=True,
            protection_reason="Participação em estudo longitudinal",
            created_by=test_user,
            updated_by=test_user
        )
        protected_patient.last_interaction_date = timezone.now() - timedelta(days=7300)  # Exactly 20 years
        protected_patient.save()
        
        self.stdout.write("✓ Test patients created")
    
    def test_retention_processing(self):
        """Test retention processing"""
        
        self.stdout.write("Testing retention processing...")
        
        retention_service = DataRetentionService()
        
        # Process with dry run first
        stats_dry = retention_service.process_retention_schedules(dry_run=True)
        self.stdout.write("Dry run results:")
        for key, value in stats_dry.items():
            self.stdout.write(f"  {key}: {value}")
        
        # Confirm before actual processing
        if stats_dry['deletions_executed'] > 0:
            confirm = input(f"\nWould process {stats_dry['deletions_executed']} deletions. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                stats_real = retention_service.process_retention_schedules(dry_run=False)
                self.stdout.write("Actual processing results:")
                for key, value in stats_real.items():
                    self.stdout.write(f"  {key}: {value}")
    
    def show_retention_overview(self):
        """Show retention system overview"""
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Data Retention System Overview")
        self.stdout.write(f"{'='*60}")
        
        # Policies
        policies = DataRetentionPolicy.objects.filter(is_active=True)
        self.stdout.write(f"\nActive Retention Policies: {policies.count()}")
        for policy in policies:
            years = policy.retention_period_days / 365.25
            self.stdout.write(f"  • {policy.name}: {years:.1f} years")
        
        # Schedules by status
        schedules = DataRetentionSchedule.objects.all()
        self.stdout.write(f"\nRetention Schedules by Status:")
        for status, label in DataRetentionSchedule.STATUS_CHOICES:
            count = schedules.filter(status=status).count()
            if count > 0:
                self.stdout.write(f"  • {label}: {count}")
        
        # Upcoming actions
        today = timezone.now().date()
        warnings_due = schedules.filter(
            warning_date__lte=today,
            status='active'
        ).count()
        deletions_due = schedules.filter(
            deletion_date__lte=today,
            status='warning_sent'
        ).count()
        
        self.stdout.write(f"\nUpcoming Actions:")
        self.stdout.write(f"  • Warnings due: {warnings_due}")
        self.stdout.write(f"  • Deletions due: {deletions_due}")
        
        # Recent activity
        recent_deletions = DataDeletionLog.objects.filter(
            executed_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        self.stdout.write(f"\nRecent Activity (last 30 days):")
        self.stdout.write(f"  • Deletions executed: {recent_deletions}")