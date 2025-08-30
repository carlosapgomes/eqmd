# apps/accounts/management/commands/lifecycle_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
import csv
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generate simple user lifecycle report (CSV format only)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            help='Output CSV file path (default: lifecycle_report_YYYYMMDD.csv)'
        )
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=90,
            help='Look ahead days for expiration analysis'
        )
    
    def handle(self, *args, **options):
        self.days_ahead = options['days_ahead']
        
        output_file = options['output_file'] or f"lifecycle_report_{timezone.now().strftime('%Y%m%d')}.csv"
        
        # Generate simple report data
        report_data = self._generate_simple_report()
        
        # Write CSV report
        self._write_csv_report(report_data, output_file)
        
        self.stdout.write(self.style.SUCCESS(f'Report written to {output_file}'))
    
    def _generate_simple_report(self):
        """Generate simplified report data"""
        from apps.accounts.models import EqmdCustomUser
        
        now = timezone.now()
        future_date = now + timedelta(days=self.days_ahead)
        
        # Get all active users with expiration info
        users = EqmdCustomUser.objects.filter(
            is_active=True
        ).order_by('access_expires_at', 'username')
        
        user_data = []
        for user in users:
            days_left = user.days_until_expiration
            days_inactive = user.days_since_last_activity
            
            user_data.append({
                'username': user.username,
                'full_name': user.get_full_name(),
                'email': user.email,
                'profession': user.get_profession_type_display(),
                'account_status': user.get_account_status_display(),
                'expiration_date': user.access_expires_at.strftime('%d/%m/%Y') if user.access_expires_at else 'Never',
                'days_until_expiration': days_left if days_left is not None else 'N/A',
                'last_activity': user.last_meaningful_activity.strftime('%d/%m/%Y') if user.last_meaningful_activity else 'Unknown',
                'days_since_activity': days_inactive if days_inactive is not None else 'N/A',
                'supervisor': user.supervisor.username if user.supervisor else 'None',
            })
        
        return user_data
    
    def _write_csv_report(self, user_data, output_file):
        """Write report data to CSV file"""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if not user_data:
                csvfile.write('No users found\n')
                return
            
            fieldnames = user_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(user_data)