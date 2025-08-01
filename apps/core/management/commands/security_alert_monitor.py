from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.db import models
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event

User = get_user_model()


class Command(BaseCommand):
    help = 'Real-time security alert monitoring for critical database events'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='Number of minutes to look back for alerts (default: 5)'
        )
        parser.add_argument(
            '--critical-only',
            action='store_true',
            help='Show only critical severity alerts'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, checking every --minutes interval'
        )
    
    def handle(self, *args, **options):
        minutes_back = options['minutes']
        critical_only = options['critical_only']
        continuous = options['continuous']
        
        if continuous:
            self.stdout.write(
                self.style.SUCCESS(f'🚨 Starting continuous security monitoring (checking every {minutes_back} minutes)...')
            )
            self.stdout.write('Press Ctrl+C to stop')
            
            import time
            try:
                while True:
                    self.check_security_alerts(minutes_back, critical_only)
                    time.sleep(minutes_back * 60)
            except KeyboardInterrupt:
                self.stdout.write('\n⏹️  Monitoring stopped')
                return
        else:
            self.check_security_alerts(minutes_back, critical_only)
    
    def check_security_alerts(self, minutes_back, critical_only):
        """Check for security alerts in the specified time window."""
        since_time = datetime.now() - timedelta(minutes=minutes_back)
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'🔍 Security Alert Check - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        )
        self.stdout.write(f'Scanning last {minutes_back} minute(s)...')
        
        alerts = []
        
        # Critical Alert: Any deletion attempts
        deletion_alerts = self.check_deletion_attempts(since_time)
        alerts.extend(deletion_alerts)
        
        # Critical Alert: Privilege escalations
        privilege_alerts = self.check_privilege_escalations(since_time)
        alerts.extend(privilege_alerts)
        
        # Critical Alert: After-hours admin activity
        admin_alerts = self.check_after_hours_admin_activity(since_time)
        alerts.extend(admin_alerts)
        
        # High Alert: Rapid bulk changes
        bulk_alerts = self.check_rapid_bulk_changes(since_time)
        alerts.extend(bulk_alerts)
        
        # High Alert: Status changes to deceased
        deceased_alerts = self.check_deceased_status_changes(since_time)
        alerts.extend(deceased_alerts)
        
        if not critical_only:
            # Medium Alert: System configuration changes
            config_alerts = self.check_system_config_changes(since_time)
            alerts.extend(config_alerts)
            
            # Medium Alert: Multiple failed attempts (simulated)
            failure_alerts = self.check_suspicious_patterns(since_time)
            alerts.extend(failure_alerts)
        
        # Display alerts
        if not alerts:
            self.stdout.write(self.style.SUCCESS('✅ No security alerts detected'))
        else:
            self.display_alerts(alerts, critical_only)
    
    def check_deletion_attempts(self, since_time):
        """Check for any deletion attempts (critical alert)."""
        alerts = []
        
        # Patient deletions
        patient_deletions = Patient.history.filter(
            history_date__gte=since_time,
            history_type='-'
        )
        
        for deletion in patient_deletions:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'PATIENT_DELETION',
                'message': f'Patient deletion attempted by {deletion.history_user}',
                'timestamp': deletion.history_date,
                'user': deletion.history_user,
                'details': f'Patient: {deletion.name}'
            })
        
        # Event deletions
        event_deletions = Event.history.filter(
            history_date__gte=since_time,
            history_type='-'
        )
        
        for deletion in event_deletions:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'EVENT_DELETION',
                'message': f'Medical event deletion attempted by {deletion.history_user}',
                'timestamp': deletion.history_date,
                'user': deletion.history_user,
                'details': f'Event: {deletion.description[:50]}...'
            })
        
        return alerts
    
    def check_privilege_escalations(self, since_time):
        """Check for privilege escalation attempts."""
        alerts = []
        
        privilege_changes = User.history.filter(
            history_date__gte=since_time,
            history_type='~'
        ).filter(
            models.Q(is_staff=True) | 
            models.Q(is_superuser=True) |
            models.Q(profession_type__in=['doctor', 'resident'])
        )
        
        for change in privilege_changes:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'PRIVILEGE_ESCALATION',
                'message': f'Privilege escalation detected for user {change.username}',
                'timestamp': change.history_date,
                'user': change.history_user,
                'details': f'New privileges: staff={change.is_staff}, super={change.is_superuser}, profession={change.profession_type}'
            })
        
        return alerts
    
    def check_after_hours_admin_activity(self, since_time):
        """Check for administrative activity after hours."""
        alerts = []
        
        # Define after-hours (outside 7 AM - 9 PM)
        for history_record in User.history.filter(
            history_date__gte=since_time,
            history_type__in=['~', '+', '-']
        ):
            hour = history_record.history_date.hour
            if hour < 7 or hour > 21:  # Before 7 AM or after 9 PM
                alerts.append({
                    'severity': 'CRITICAL',
                    'type': 'AFTER_HOURS_ADMIN',
                    'message': f'After-hours administrative activity by {history_record.history_user}',
                    'timestamp': history_record.history_date,
                    'user': history_record.history_user,
                    'details': f'User account modification: {history_record.username}'
                })
        
        return alerts
    
    def check_rapid_bulk_changes(self, since_time):
        """Check for rapid bulk changes (high alert)."""
        alerts = []
        
        # Check for users making more than 5 changes in the time window
        bulk_patient_changes = (
            Patient.history
            .filter(history_date__gte=since_time)
            .values('history_user__username')
            .annotate(change_count=models.Count('id'))
            .filter(change_count__gt=5)
        )
        
        for user_data in bulk_patient_changes:
            username = user_data['history_user__username'] or 'Unknown User'
            count = user_data['change_count']
            
            alerts.append({
                'severity': 'HIGH',
                'type': 'BULK_PATIENT_CHANGES',
                'message': f'Rapid bulk patient changes by {username}',
                'timestamp': datetime.now(),
                'user': username,
                'details': f'{count} patient changes in {(datetime.now() - since_time).total_seconds() / 60:.1f} minutes'
            })
        
        return alerts
    
    def check_deceased_status_changes(self, since_time):
        """Check for status changes to deceased."""
        alerts = []
        
        deceased_changes = Patient.history.filter(
            history_date__gte=since_time,
            status='deceased',
            history_type='~'
        )
        
        for change in deceased_changes:
            alerts.append({
                'severity': 'HIGH',
                'type': 'DECEASED_STATUS',
                'message': f'Patient marked as deceased by {change.history_user}',
                'timestamp': change.history_date,
                'user': change.history_user,
                'details': f'Patient: {change.name}'
            })
        
        return alerts
    
    def check_system_config_changes(self, since_time):
        """Check for system configuration changes."""
        alerts = []
        
        config_changes = AllowedTag.history.filter(
            history_date__gte=since_time,
            history_type__in=['~', '+', '-']
        )
        
        for change in config_changes:
            change_type = {'~': 'modified', '+': 'created', '-': 'deleted'}[change.history_type]
            
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'CONFIG_CHANGE',
                'message': f'System configuration {change_type} by {change.history_user}',
                'timestamp': change.history_date,
                'user': change.history_user,
                'details': f'Tag: {change.name}'
            })
        
        return alerts
    
    def check_suspicious_patterns(self, since_time):
        """Check for other suspicious patterns."""
        alerts = []
        
        # Check for same user modifying many different record types
        user_activity = {}
        
        # Collect activity across different models
        for record in Patient.history.filter(history_date__gte=since_time):
            user = record.history_user
            if user:
                if user not in user_activity:
                    user_activity[user] = {'patient': 0, 'event': 0, 'user': 0}
                user_activity[user]['patient'] += 1
        
        for record in Event.history.filter(history_date__gte=since_time):
            user = record.history_user
            if user:
                if user not in user_activity:
                    user_activity[user] = {'patient': 0, 'event': 0, 'user': 0}
                user_activity[user]['event'] += 1
        
        for record in User.history.filter(history_date__gte=since_time):
            user = record.history_user
            if user:
                if user not in user_activity:
                    user_activity[user] = {'patient': 0, 'event': 0, 'user': 0}
                user_activity[user]['user'] += 1
        
        # Alert on users with activity across multiple record types
        for user, activity in user_activity.items():
            active_types = sum(1 for count in activity.values() if count > 0)
            total_changes = sum(activity.values())
            
            if active_types >= 3 and total_changes > 3:  # Active in all 3 types with significant changes
                alerts.append({
                    'severity': 'MEDIUM',
                    'type': 'MULTI_TYPE_ACTIVITY',
                    'message': f'User active across multiple record types: {user}',
                    'timestamp': datetime.now(),
                    'user': user,
                    'details': f'Patient: {activity["patient"]}, Events: {activity["event"]}, Users: {activity["user"]}'
                })
        
        return alerts
    
    def display_alerts(self, alerts, critical_only):
        """Display security alerts with appropriate styling."""
        # Sort by severity and timestamp
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 3), x['timestamp']), reverse=True)
        
        critical_count = sum(1 for alert in alerts if alert['severity'] == 'CRITICAL')
        high_count = sum(1 for alert in alerts if alert['severity'] == 'HIGH')
        medium_count = sum(1 for alert in alerts if alert['severity'] == 'MEDIUM')
        
        self.stdout.write('')
        self.stdout.write(
            self.style.ERROR(f'🚨 SECURITY ALERTS DETECTED: {len(alerts)} total')
        )
        self.stdout.write(
            f'Critical: {critical_count} | High: {high_count} | Medium: {medium_count}'
        )
        self.stdout.write('')
        
        for alert in alerts:
            # Style based on severity
            if alert['severity'] == 'CRITICAL':
                style = self.style.ERROR
                icon = '🔴'
            elif alert['severity'] == 'HIGH':
                style = self.style.WARNING
                icon = '🟡'
            else:
                style = self.style.NOTICE
                icon = '🔵'
            
            timestamp_str = alert['timestamp'].strftime('%H:%M:%S')
            
            self.stdout.write(
                style(f'{icon} [{alert["severity"]}] {timestamp_str} - {alert["message"]}')
            )
            self.stdout.write(f'    👤 User: {alert["user"]}')
            self.stdout.write(f'    📋 Details: {alert["details"]}')
            self.stdout.write('')