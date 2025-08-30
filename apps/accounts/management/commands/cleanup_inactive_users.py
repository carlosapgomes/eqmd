# apps/accounts/management/commands/cleanup_inactive_users.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Report on inactive users (simplified - no automatic changes)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--inactivity-days',
            type=int,
            default=90,
            help='Days of inactivity to report on'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'csv'],
            default='table',
            help='Output format'
        )
    
    def handle(self, *args, **options):
        self.inactivity_threshold = options['inactivity_days']
        self.format = options['format']
        
        self.stdout.write(self.style.SUCCESS(
            f'Generating inactive user report (simplified - no auto-changes)'
        ))
        
        # Find inactive users (report only)
        inactive_users = self._find_inactive_users()
        
        self.stdout.write(f'Found {inactive_users.count()} inactive users')
        
        if self.format == 'csv':
            self._output_csv(inactive_users)
        else:
            self._output_table(inactive_users)
    
    def _find_inactive_users(self):
        """Find users who appear inactive (for reporting only)"""
        from apps.accounts.models import EqmdCustomUser
        
        cutoff_date = timezone.now() - timedelta(days=self.inactivity_threshold)
        
        return EqmdCustomUser.objects.filter(
            is_active=True,
            account_status='active',
            last_meaningful_activity__lt=cutoff_date
        ).exclude(
            profession_type__in=[0, 2]  # Don't report on doctors and nurses
        ).order_by('last_meaningful_activity')
    
    def _output_table(self, users):
        """Output inactive users as table"""
        self.stdout.write("\nINACTIVE USER REPORT")
        self.stdout.write("-" * 60)
        self.stdout.write(f"{'Username':<20} {'Profession':<15} {'Last Activity':<12} {'Days':<5}")
        self.stdout.write("-" * 60)
        
        for user in users:
            if user.last_meaningful_activity:
                days_inactive = (timezone.now().date() - user.last_meaningful_activity.date()).days
                last_activity_str = user.last_meaningful_activity.strftime('%d/%m/%Y')
            else:
                days_inactive = 'N/A'
                last_activity_str = 'Never'
                
            profession_display = user.get_profession_type_display() or 'Unknown'
            
            self.stdout.write(
                f"{user.username:<20} "
                f"{profession_display:<15} "
                f"{last_activity_str:<12} "
                f"{str(days_inactive):<5}"
            )
        
        self.stdout.write("\nRECOMMENDATION: Review these users for potential status updates")
    
    def _output_csv(self, users):
        """Output inactive users as CSV"""
        import csv
        import sys
        
        writer = csv.writer(sys.stdout)
        writer.writerow(['Username', 'Profession', 'Last_Activity', 'Days_Inactive', 'Email'])
        
        for user in users:
            if user.last_meaningful_activity:
                days_inactive = (timezone.now().date() - user.last_meaningful_activity.date()).days
                last_activity_str = user.last_meaningful_activity.strftime('%d/%m/%Y')
            else:
                days_inactive = 'N/A'
                last_activity_str = 'Never'
                
            profession_display = user.get_profession_type_display() or 'Unknown'
            
            writer.writerow([
                user.username,
                profession_display,
                last_activity_str,
                days_inactive,
                user.email
            ])