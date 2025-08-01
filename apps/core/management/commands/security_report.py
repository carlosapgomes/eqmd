from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.db import models
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate comprehensive security audit reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to include in report (default: 7)'
        )
        parser.add_argument(
            '--format',
            choices=['text', 'json', 'csv'],
            default='text',
            help='Output format for the report'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (prints to stdout if not specified)'
        )
        parser.add_argument(
            '--include-users',
            action='store_true',
            help='Include detailed user activity breakdown'
        )
        parser.add_argument(
            '--summary-only',
            action='store_true',
            help='Generate summary report only'
        )
    
    def handle(self, *args, **options):
        days_back = options['days']
        output_format = options['format']
        output_file = options['output']
        include_users = options['include_users']
        summary_only = options['summary_only']
        
        since_date = datetime.now() - timedelta(days=days_back)
        
        # Generate comprehensive report data
        report_data = self.generate_report_data(since_date, include_users, summary_only)
        
        # Format and output report
        if output_format == 'json':
            self.output_json_report(report_data, output_file)
        elif output_format == 'csv':
            self.output_csv_report(report_data, output_file)
        else:
            self.output_text_report(report_data, output_file, days_back)
    
    def generate_report_data(self, since_date, include_users, summary_only):
        """Generate comprehensive security report data."""
        report_data = {
            'report_timestamp': datetime.now().isoformat(),
            'period_start': since_date.isoformat(),
            'period_end': datetime.now().isoformat(),
            'summary': {},
            'security_events': {},
            'user_activity': {},
            'risk_assessment': {}
        }
        
        # Summary statistics
        report_data['summary'] = {
            'total_patient_changes': Patient.history.filter(history_date__gte=since_date).count(),
            'total_event_changes': Event.history.filter(history_date__gte=since_date).count(),
            'total_user_changes': User.history.filter(history_date__gte=since_date).count(),
            'total_config_changes': AllowedTag.history.filter(history_date__gte=since_date).count(),
            'unique_users_active': self.get_unique_active_users(since_date),
            'deletion_attempts': self.get_deletion_attempts(since_date),
            'privilege_escalations': self.get_privilege_escalations(since_date)
        }
        
        # Security events
        report_data['security_events'] = {
            'patient_deletions': self.get_patient_deletions(since_date),
            'event_deletions': self.get_event_deletions(since_date),
            'user_deletions': self.get_user_deletions(since_date),
            'deceased_status_changes': self.get_deceased_status_changes(since_date),
            'privilege_changes': self.get_privilege_changes(since_date),
            'after_hours_activity': self.get_after_hours_activity(since_date),
            'bulk_operations': self.get_bulk_operations(since_date)
        }
        
        # User activity (if requested)
        if include_users:
            report_data['user_activity'] = self.get_detailed_user_activity(since_date)
        
        # Risk assessment
        report_data['risk_assessment'] = self.generate_risk_assessment(report_data)
        
        return report_data
    
    def get_unique_active_users(self, since_date):
        """Get count of unique users who made changes."""
        users = set()
        
        for model_history in [Patient.history, Event.history, User.history, AllowedTag.history]:
            for record in model_history.filter(history_date__gte=since_date):
                if record.history_user:
                    users.add(record.history_user.username)
        
        return len(users)
    
    def get_deletion_attempts(self, since_date):
        """Get total deletion attempts across all models."""
        deletions = 0
        for model_history in [Patient.history, Event.history, User.history, AllowedTag.history]:
            deletions += model_history.filter(history_date__gte=since_date, history_type='-').count()
        return deletions
    
    def get_privilege_escalations(self, since_date):
        """Get privilege escalation count."""
        return User.history.filter(
            history_date__gte=since_date,
            history_type='~'
        ).filter(
            models.Q(is_staff=True) | 
            models.Q(is_superuser=True) |
            models.Q(profession_type__in=['doctor', 'resident'])
        ).count()
    
    def get_patient_deletions(self, since_date):
        """Get patient deletion details."""
        deletions = []
        for deletion in Patient.history.filter(history_date__gte=since_date, history_type='-'):
            deletions.append({
                'timestamp': deletion.history_date.isoformat(),
                'user': deletion.history_user.username if deletion.history_user else 'Unknown',
                'patient_name': deletion.name,
                'reason': deletion.history_change_reason or 'No reason provided'
            })
        return deletions
    
    def get_event_deletions(self, since_date):
        """Get event deletion details."""
        deletions = []
        for deletion in Event.history.filter(history_date__gte=since_date, history_type='-'):
            deletions.append({
                'timestamp': deletion.history_date.isoformat(),
                'user': deletion.history_user.username if deletion.history_user else 'Unknown',
                'event_type': deletion.get_event_type_display(),
                'description': deletion.description[:100],
                'reason': deletion.history_change_reason or 'No reason provided'
            })
        return deletions
    
    def get_user_deletions(self, since_date):
        """Get user deletion details."""
        deletions = []
        for deletion in User.history.filter(history_date__gte=since_date, history_type='-'):
            deletions.append({
                'timestamp': deletion.history_date.isoformat(),
                'user': deletion.history_user.username if deletion.history_user else 'Unknown',
                'deleted_user': deletion.username,
                'profession': deletion.profession_type,
                'reason': deletion.history_change_reason or 'No reason provided'
            })
        return deletions
    
    def get_deceased_status_changes(self, since_date):
        """Get deceased status changes."""
        changes = []
        for change in Patient.history.filter(
            history_date__gte=since_date,
            status='deceased',
            history_type='~'
        ):
            changes.append({
                'timestamp': change.history_date.isoformat(),
                'user': change.history_user.username if change.history_user else 'Unknown',
                'patient_name': change.name,
                'reason': change.history_change_reason or 'No reason provided'
            })
        return changes
    
    def get_privilege_changes(self, since_date):
        """Get privilege escalation details."""
        changes = []
        for change in User.history.filter(
            history_date__gte=since_date,
            history_type='~'
        ).filter(
            models.Q(is_staff=True) | 
            models.Q(is_superuser=True) |
            models.Q(profession_type__in=['doctor', 'resident'])
        ):
            changes.append({
                'timestamp': change.history_date.isoformat(),
                'changed_by': change.history_user.username if change.history_user else 'Unknown',
                'target_user': change.username,
                'new_profession': change.profession_type,
                'is_staff': change.is_staff,
                'is_superuser': change.is_superuser,
                'reason': change.history_change_reason or 'No reason provided'
            })
        return changes
    
    def get_after_hours_activity(self, since_date):
        """Get after-hours activity."""
        after_hours = []
        
        for model_history in [Patient.history, Event.history, User.history]:
            for record in model_history.filter(history_date__gte=since_date):
                hour = record.history_date.hour
                if hour < 6 or hour > 22:  # Before 6 AM or after 10 PM
                    after_hours.append({
                        'timestamp': record.history_date.isoformat(),
                        'user': record.history_user.username if record.history_user else 'Unknown',
                        'model': record.__class__.__name__.replace('Historical', ''),
                        'action': {'~': 'Modified', '+': 'Created', '-': 'Deleted'}[record.history_type]
                    })
        
        return after_hours
    
    def get_bulk_operations(self, since_date):
        """Get bulk operations (more than 10 changes by same user)."""
        bulk_ops = []
        
        for model_history in [Patient.history, Event.history, User.history]:
            model_name = model_history.model.__name__.replace('Historical', '')
            
            bulk_users = (
                model_history
                .filter(history_date__gte=since_date)
                .values('history_user__username')
                .annotate(change_count=models.Count('id'))
                .filter(change_count__gt=10)
                .order_by('-change_count')
            )
            
            for user_data in bulk_users:
                bulk_ops.append({
                    'user': user_data['history_user__username'] or 'Unknown',
                    'model': model_name,
                    'change_count': user_data['change_count']
                })
        
        return bulk_ops
    
    def get_detailed_user_activity(self, since_date):
        """Get detailed user activity breakdown."""
        user_activity = {}
        
        # Collect activity for each user
        all_users = set()
        for model_history in [Patient.history, Event.history, User.history, AllowedTag.history]:
            for record in model_history.filter(history_date__gte=since_date):
                if record.history_user:
                    all_users.add(record.history_user)
        
        for user in all_users:
            username = user.username
            user_activity[username] = {
                'patient_changes': Patient.history.filter(
                    history_date__gte=since_date, history_user=user
                ).count(),
                'event_changes': Event.history.filter(
                    history_date__gte=since_date, history_user=user
                ).count(),
                'user_changes': User.history.filter(
                    history_date__gte=since_date, history_user=user
                ).count(),
                'config_changes': AllowedTag.history.filter(
                    history_date__gte=since_date, history_user=user
                ).count(),
                'profession': user.profession_type,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
        
        return user_activity
    
    def generate_risk_assessment(self, report_data):
        """Generate risk assessment based on report data."""
        risk_score = 0
        risk_factors = []
        
        # Critical risk factors
        if report_data['summary']['deletion_attempts'] > 0:
            risk_score += 50
            risk_factors.append(f"Deletion attempts detected: {report_data['summary']['deletion_attempts']}")
        
        if report_data['summary']['privilege_escalations'] > 0:
            risk_score += 40
            risk_factors.append(f"Privilege escalations: {report_data['summary']['privilege_escalations']}")
        
        # High risk factors
        if len(report_data['security_events']['after_hours_activity']) > 5:
            risk_score += 30
            risk_factors.append(f"High after-hours activity: {len(report_data['security_events']['after_hours_activity'])} events")
        
        if len(report_data['security_events']['bulk_operations']) > 0:
            risk_score += 25
            risk_factors.append(f"Bulk operations detected: {len(report_data['security_events']['bulk_operations'])}")
        
        # Medium risk factors
        if len(report_data['security_events']['deceased_status_changes']) > 3:
            risk_score += 15
            risk_factors.append(f"Multiple deceased status changes: {len(report_data['security_events']['deceased_status_changes'])}")
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = 'CRITICAL'
        elif risk_score >= 50:
            risk_level = 'HIGH'
        elif risk_score >= 25:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendations': self.get_risk_recommendations(risk_level, risk_factors)
        }
    
    def get_risk_recommendations(self, risk_level, risk_factors):
        """Get security recommendations based on risk level."""
        recommendations = []
        
        if risk_level == 'CRITICAL':
            recommendations.extend([
                'Immediately review all deletion attempts and privilege escalations',
                'Consider temporarily restricting administrative access',
                'Conduct emergency security audit',
                'Review user access permissions'
            ])
        elif risk_level == 'HIGH':
            recommendations.extend([
                'Review recent administrative changes',
                'Audit user permissions and access levels',
                'Implement additional monitoring for suspicious activity'
            ])
        elif risk_level == 'MEDIUM':
            recommendations.extend([
                'Monitor bulk operations more closely',
                'Review after-hours access policies',
                'Consider implementing additional access controls'
            ])
        else:
            recommendations.append('Continue regular security monitoring')
        
        return recommendations
    
    def output_text_report(self, report_data, output_file, days_back):
        """Output report in text format."""
        output = []
        
        # Header
        output.append('=' * 80)
        output.append('SECURITY AUDIT REPORT')
        output.append('=' * 80)
        output.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Period: Last {days_back} days")
        output.append('')
        
        # Summary
        summary = report_data['summary']
        output.append('SUMMARY')
        output.append('-' * 40)
        output.append(f"Patient Changes: {summary['total_patient_changes']}")
        output.append(f"Event Changes: {summary['total_event_changes']}")
        output.append(f"User Changes: {summary['total_user_changes']}")
        output.append(f"Config Changes: {summary['total_config_changes']}")
        output.append(f"Active Users: {summary['unique_users_active']}")
        output.append(f"Deletion Attempts: {summary['deletion_attempts']}")
        output.append(f"Privilege Escalations: {summary['privilege_escalations']}")
        output.append('')
        
        # Risk Assessment
        risk = report_data['risk_assessment']
        output.append('RISK ASSESSMENT')
        output.append('-' * 40)
        output.append(f"Risk Level: {risk['risk_level']} (Score: {risk['risk_score']}/100)")
        if risk['risk_factors']:
            output.append('Risk Factors:')
            for factor in risk['risk_factors']:
                output.append(f"  • {factor}")
        output.append('')
        output.append('Recommendations:')
        for rec in risk['recommendations']:
            output.append(f"  • {rec}")
        output.append('')
        
        # Security Events
        events = report_data['security_events']
        if any(events.values()):
            output.append('SECURITY EVENTS')
            output.append('-' * 40)
            
            if events['patient_deletions']:
                output.append(f"Patient Deletions ({len(events['patient_deletions'])}):")
                for deletion in events['patient_deletions']:
                    output.append(f"  • {deletion['timestamp']} - {deletion['user']} deleted {deletion['patient_name']}")
            
            if events['privilege_changes']:
                output.append(f"Privilege Changes ({len(events['privilege_changes'])}):")
                for change in events['privilege_changes']:
                    output.append(f"  • {change['timestamp']} - {change['changed_by']} elevated {change['target_user']}")
            
            if events['bulk_operations']:
                output.append(f"Bulk Operations ({len(events['bulk_operations'])}):")
                for op in events['bulk_operations']:
                    output.append(f"  • {op['user']}: {op['change_count']} {op['model']} changes")
        
        # Output to file or stdout
        report_text = '\n'.join(output)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            self.stdout.write(self.style.SUCCESS(f'Report saved to: {output_file}'))
        else:
            self.stdout.write(report_text)
    
    def output_json_report(self, report_data, output_file):
        """Output report in JSON format."""
        json_output = json.dumps(report_data, indent=2, default=str)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_output)
            self.stdout.write(self.style.SUCCESS(f'JSON report saved to: {output_file}'))
        else:
            self.stdout.write(json_output)
    
    def output_csv_report(self, report_data, output_file):
        """Output report in CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write summary data
        writer.writerow(['Section', 'Metric', 'Value'])
        summary = report_data['summary']
        for key, value in summary.items():
            writer.writerow(['Summary', key.replace('_', ' ').title(), value])
        
        # Write risk assessment
        risk = report_data['risk_assessment']
        writer.writerow(['Risk Assessment', 'Risk Level', risk['risk_level']])
        writer.writerow(['Risk Assessment', 'Risk Score', risk['risk_score']])
        
        csv_content = output.getvalue()
        output.close()
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(csv_content)
            self.stdout.write(self.style.SUCCESS(f'CSV report saved to: {output_file}'))
        else:
            self.stdout.write(csv_content)