from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.compliance.services.retention_management import DataRetentionService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process data retention schedules and deletions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force execution without confirmation'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Process only specific data category'
        )
        parser.add_argument(
            '--warning-only',
            action='store_true',
            help='Only send warnings, do not delete'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Data Retention Processing - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'EXECUTION'}")
        self.stdout.write(f"{'='*60}")
        
        if not dry_run and not force:
            confirm = input("\nThis will process deletions. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("Operation cancelled.")
                return
        
        # Initialize retention service
        retention_service = DataRetentionService()
        
        # Get initial statistics
        initial_stats = retention_service.get_retention_statistics()
        self.stdout.write(f"\nInitial Statistics:")
        for key, value in initial_stats.items():
            self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Process retention
        try:
            if options['warning_only']:
                retention_service.send_deletion_warnings(dry_run=dry_run)
                stats = {'warnings_sent': retention_service.deletion_stats['warnings_sent']}
            else:
                stats = retention_service.process_retention_schedules(dry_run=dry_run)
            
            # Display results
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write("Processing Results:")
            self.stdout.write(f"{'='*60}")
            
            for key, value in stats.items():
                self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
            
            if stats['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  {stats['errors']} errors occurred. Check logs for details.")
                )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS("\n✓ Dry run completed. No changes were made.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Processing completed successfully.")
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error during processing: {e}")
            )
            logger.error(f"Retention processing error: {e}", exc_info=True)