from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.db import models
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event

User = get_user_model()


class Command(BaseCommand):
    help = 'Detect suspicious database activity'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to look back for suspicious activity (default: 1)'
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=10,
            help='Number of changes per day to consider suspicious (default: 10)'
        )
        parser.add_argument(
            '--comprehensive',
            action='store_true',
            help='Run comprehensive analysis including all models and advanced patterns'
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export results to file (CSV format)'
        )
    
    def handle(self, *args, **options):
        days_back = options['days']
        threshold = options['threshold']
        comprehensive = options['comprehensive']
        export_file = options['export']
        since_date = datetime.now() - timedelta(days=days_back)
        
        self.stdout.write(
            self.style.SUCCESS(f'🔍 Scanning for suspicious activity in the last {days_back} day(s)...')
        )
        
        # Collect all findings for potential export
        findings = []
        
        # Check patient-related suspicious activity
        patient_findings = self.check_patient_suspicious_activity(since_date, threshold)
        findings.extend(patient_findings)
        
        # Additional checks for other suspicious patterns
        self.stdout.write('')
        deletion_findings = self.check_unusual_deletion_attempts(since_date)
        findings.extend(deletion_findings)
        
        deceased_findings = self.check_status_changes_to_deceased(since_date)
        findings.extend(deceased_findings)
        
        if comprehensive:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('🔍 Running comprehensive analysis...'))
            
            # Check user account modifications
            user_findings = self.check_user_account_modifications(since_date, threshold)
            findings.extend(user_findings)
            
            # Check event modifications
            event_findings = self.check_event_modifications(since_date, threshold)
            findings.extend(event_findings)
            
            # Check system configuration changes
            config_findings = self.check_system_configuration_changes(since_date)
            findings.extend(config_findings)
            
            # Check privilege escalation patterns
            escalation_findings = self.check_privilege_escalation_patterns(since_date)
            findings.extend(escalation_findings)
            
            # Check after-hours activity
            afterhours_findings = self.check_after_hours_activity(since_date)
            findings.extend(afterhours_findings)
        
        # Export findings if requested
        if export_file and findings:
            self.export_findings(findings, export_file)
            
        if not findings:
            self.stdout.write(
                self.style.SUCCESS('✅ No suspicious activity detected.')
            )
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(f'📊 Total suspicious findings: {len(findings)}')
            )
    
    def check_patient_suspicious_activity(self, since_date, threshold):
        """Check for suspicious patient-related activity."""
        findings = []
        
        # Detect bulk changes by same user
        suspicious_users = (
            Patient.history
            .filter(history_date__gte=since_date)
            .values('history_user__username')
            .annotate(change_count=models.Count('id'))
            .filter(change_count__gt=threshold)
            .order_by('-change_count')
        )
        
        if not suspicious_users:
            return findings
        
        self.stdout.write(
            self.style.WARNING(f'⚠️  Found {len(suspicious_users)} user(s) with suspicious patient activity:')
        )
        
        for user_data in suspicious_users:
            username = user_data['history_user__username'] or 'Unknown User'
            change_count = user_data['change_count']
            
            self.stdout.write(
                f"   • User '{username}' made {change_count} patient changes"
            )
            
            # Get detailed breakdown of changes
            user_changes = (
                Patient.history
                .filter(
                    history_date__gte=since_date,
                    history_user__username=username
                )
                .values('history_type')
                .annotate(count=models.Count('id'))
            )
            
            for change in user_changes:
                change_type_map = {
                    '+': 'Created',
                    '~': 'Modified', 
                    '-': 'Deleted'
                }
                change_type = change_type_map.get(change['history_type'], 'Unknown')
                self.stdout.write(f"     - {change_type}: {change['count']} patients")
                
                findings.append({
                    'type': 'bulk_patient_changes',
                    'username': username,
                    'change_type': change_type,
                    'count': change['count'],
                    'severity': 'high' if change['count'] > threshold * 2 else 'medium'
                })
        
        return findings
    
    def check_unusual_deletion_attempts(self, since_date):
        """Check for deletion attempts (which should be rare)."""
        findings = []
        
        deletions = (
            Patient.history
            .filter(history_date__gte=since_date, history_type='-')
            .count()
        )
        
        if deletions > 0:
            self.stdout.write(
                self.style.ERROR(f'🚨 ALERT: {deletions} patient deletion attempt(s) detected!')
            )
            
            deletion_users = (
                Patient.history
                .filter(history_date__gte=since_date, history_type='-')
                .values('history_user__username')
                .annotate(count=models.Count('id'))
            )
            
            for user_data in deletion_users:
                username = user_data['history_user__username'] or 'Unknown User'
                count = user_data['count']
                self.stdout.write(f"   • User '{username}' attempted {count} deletion(s)")
                
                findings.append({
                    'type': 'deletion_attempt',
                    'username': username,
                    'count': count,
                    'severity': 'critical'
                })
        
        return findings
    
    def check_status_changes_to_deceased(self, since_date):
        """Check for status changes to deceased."""
        findings = []
        
        deceased_changes = (
            Patient.history
            .filter(
                history_date__gte=since_date,
                status='deceased'
            )
            .count()
        )
        
        if deceased_changes > 0:
            self.stdout.write(
                self.style.WARNING(f'📋 INFO: {deceased_changes} patient(s) marked as deceased')
            )
            
            deceased_users = (
                Patient.history
                .filter(
                    history_date__gte=since_date,
                    status='deceased'
                )
                .values('history_user__username')
                .annotate(count=models.Count('id'))
            )
            
            for user_data in deceased_users:
                username = user_data['history_user__username'] or 'Unknown User'
                count = user_data['count']
                self.stdout.write(f"   • User '{username}' marked {count} patient(s) as deceased")
                
                findings.append({
                    'type': 'deceased_status_change',
                    'username': username,
                    'count': count,
                    'severity': 'medium'
                })
        
        return findings
    
    def check_user_account_modifications(self, since_date, threshold):
        """Check for suspicious user account modifications."""
        findings = []
        
        # Check for bulk user modifications
        user_modifications = (
            User.history
            .filter(history_date__gte=since_date, history_type='~')
            .values('history_user__username')
            .annotate(change_count=models.Count('id'))
            .filter(change_count__gt=threshold // 2)  # Lower threshold for user changes
            .order_by('-change_count')
        )
        
        if user_modifications:
            self.stdout.write(
                self.style.WARNING(f'👤 User Account Modifications: {len(user_modifications)} user(s) with bulk changes')
            )
            
            for user_data in user_modifications:
                username = user_data['history_user__username'] or 'Unknown User'
                change_count = user_data['change_count']
                
                self.stdout.write(f"   • User '{username}' modified {change_count} user accounts")
                
                findings.append({
                    'type': 'bulk_user_modifications',
                    'username': username,
                    'count': change_count,
                    'severity': 'high'
                })
        
        # Check for privilege escalations
        privilege_escalations = (
            User.history
            .filter(
                history_date__gte=since_date,
                history_type='~'
            )
            .filter(
                models.Q(is_staff=True) | 
                models.Q(is_superuser=True) |
                models.Q(profession_type__in=['doctor', 'resident'])
            )
            .count()
        )
        
        if privilege_escalations > 0:
            self.stdout.write(
                self.style.ERROR(f'🔐 PRIVILEGE ESCALATION: {privilege_escalations} privilege elevation(s) detected')
            )
            
            findings.append({
                'type': 'privilege_escalation',
                'count': privilege_escalations,
                'severity': 'critical'
            })
        
        return findings
    
    def check_event_modifications(self, since_date, threshold):
        """Check for suspicious event modifications."""
        findings = []
        
        # Check for bulk event modifications
        event_modifications = (
            Event.history
            .filter(history_date__gte=since_date, history_type='~')
            .values('history_user__username')
            .annotate(change_count=models.Count('id'))
            .filter(change_count__gt=threshold)
            .order_by('-change_count')
        )
        
        if event_modifications:
            self.stdout.write(
                self.style.WARNING(f'📝 Event Modifications: {len(event_modifications)} user(s) with bulk changes')
            )
            
            for user_data in event_modifications:
                username = user_data['history_user__username'] or 'Unknown User'
                change_count = user_data['change_count']
                
                self.stdout.write(f"   • User '{username}' modified {change_count} medical events")
                
                findings.append({
                    'type': 'bulk_event_modifications',
                    'username': username,
                    'count': change_count,
                    'severity': 'high'
                })
        
        # Check for event deletions
        event_deletions = (
            Event.history
            .filter(history_date__gte=since_date, history_type='-')
            .count()
        )
        
        if event_deletions > 0:
            self.stdout.write(
                self.style.ERROR(f'🗑️  EVENT DELETIONS: {event_deletions} medical event deletion(s) detected')
            )
            
            findings.append({
                'type': 'event_deletions',
                'count': event_deletions,
                'severity': 'critical'
            })
        
        return findings
    
    def check_system_configuration_changes(self, since_date):
        """Check for system configuration changes."""
        findings = []
        
        # Check AllowedTag modifications
        tag_modifications = (
            AllowedTag.history
            .filter(history_date__gte=since_date)
            .count()
        )
        
        if tag_modifications > 0:
            self.stdout.write(
                self.style.WARNING(f'⚙️  System Configuration: {tag_modifications} tag configuration change(s)')
            )
            
            findings.append({
                'type': 'system_config_changes',
                'count': tag_modifications,
                'severity': 'medium'
            })
        
        return findings
    
    def check_privilege_escalation_patterns(self, since_date):
        """Check for privilege escalation patterns."""
        findings = []
        
        # Look for rapid privilege changes in user accounts
        rapid_changes = (
            User.history
            .filter(history_date__gte=since_date)
            .values('id')
            .annotate(change_count=models.Count('history_id'))
            .filter(change_count__gt=3)  # More than 3 changes to same user
        )
        
        if rapid_changes:
            self.stdout.write(
                self.style.ERROR(f'⚡ RAPID PRIVILEGE CHANGES: {len(rapid_changes)} user(s) with rapid changes')
            )
            
            findings.append({
                'type': 'rapid_privilege_changes',
                'count': len(rapid_changes),
                'severity': 'critical'
            })
        
        return findings
    
    def check_after_hours_activity(self, since_date):
        """Check for suspicious after-hours activity."""
        findings = []
        
        # Define after-hours (outside 6 AM - 10 PM)
        after_hours_activity = 0
        
        # Check patient changes after hours
        for history_record in Patient.history.filter(history_date__gte=since_date):
            hour = history_record.history_date.hour
            if hour < 6 or hour > 22:  # Before 6 AM or after 10 PM
                after_hours_activity += 1
        
        if after_hours_activity > 0:
            self.stdout.write(
                self.style.WARNING(f'🌙 After-Hours Activity: {after_hours_activity} change(s) outside normal hours')
            )
            
            findings.append({
                'type': 'after_hours_activity',
                'count': after_hours_activity,
                'severity': 'medium'
            })
        
        return findings
    
    def export_findings(self, findings, filename):
        """Export findings to CSV file."""
        import csv
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'type', 'username', 'count', 'severity', 'change_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for finding in findings:
                    row = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'type': finding.get('type', ''),
                        'username': finding.get('username', ''),
                        'count': finding.get('count', ''),
                        'severity': finding.get('severity', ''),
                        'change_type': finding.get('change_type', '')
                    }
                    writer.writerow(row)
            
            self.stdout.write(
                self.style.SUCCESS(f'📄 Findings exported to: {filename}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to export findings: {e}')
            )