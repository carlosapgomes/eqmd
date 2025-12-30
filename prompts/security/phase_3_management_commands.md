# Phase 3: Management Commands and Automation

## Overview

**Timeline: 1-2 weeks**
**Priority: Medium**

Implement automated maintenance tasks, administrative tools, and scheduled operations for user lifecycle management. This phase provides the operational foundation for day-to-day lifecycle management and long-term system maintenance.

## Command Architecture

### Command Categories

1. **Daily Automated Tasks**: Scheduled operations for status updates and notifications
2. **Administrative Tools**: Interactive commands for user management
3. **Reporting Commands**: Generate lifecycle reports and analytics
4. **Maintenance Operations**: System health checks and data cleanup

### Command Structure

```
apps/accounts/management/commands/
├── lifecycle/
│   ├── __init__.py
│   ├── check_user_expiration.py          # Daily expiration checks
│   ├── update_user_statuses.py           # Status synchronization
│   ├── send_expiration_notifications.py  # Automated notifications
│   ├── cleanup_inactive_users.py         # Inactive user management
│   └── process_renewal_requests.py       # Renewal workflow automation
├── reporting/
│   ├── __init__.py
│   ├── lifecycle_report.py               # Comprehensive reporting
│   ├── activity_analytics.py             # User activity analysis
│   └── compliance_audit.py               # Audit trail verification
└── admin/
    ├── __init__.py
    ├── extend_user_access.py              # Manual access extension
    ├── bulk_user_operations.py            # Bulk management operations
    └── emergency_access_restore.py        # Emergency procedures
```

## Daily Automated Tasks

### 1. User Expiration Checker

```python
# apps/accounts/management/commands/lifecycle/check_user_expiration.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

class Command(BaseCommand):
    help = 'Check and update user expiration statuses (run daily)'
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('lifecycle.expiration_checker')
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recently run'
        )
        parser.add_argument(
            '--role',
            choices=['resident', 'student', 'all'],
            default='all',
            help='Check specific user roles only'
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.role_filter = options['role']
        
        self.stdout.write(self.style.SUCCESS(
            f'Starting expiration check (dry_run={self.dry_run})'
        ))
        
        # Check if command was recently run (prevent multiple daily runs)
        if not self.force and self._was_recently_run():
            self.stdout.write(self.style.WARNING(
                'Expiration check was already run today. Use --force to override.'
            ))
            return
        
        # Get users to check
        users_to_check = self._get_users_to_check()
        
        self.stdout.write(f'Found {users_to_check.count()} users to check')
        
        # Process expiration updates
        results = self._process_expirations(users_to_check)
        
        # Display results
        self._display_results(results)
        
        # Record command execution
        if not self.dry_run:
            self._record_execution()
    
    def _was_recently_run(self):
        """Check if command was run in last 23 hours"""
        from django.core.cache import cache
        last_run = cache.get('expiration_checker_last_run')
        
        if last_run:
            time_diff = timezone.now() - last_run
            return time_diff < timedelta(hours=23)
        
        return False
    
    def _get_users_to_check(self):
        """Get users that need expiration checking"""
        from apps.accounts.models import EqmdCustomUser
        
        queryset = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__isnull=False
        ).select_related('supervisor', 'reviewed_by')
        
        # Apply role filtering
        if self.role_filter == 'resident':
            queryset = queryset.filter(profession_type=1)
        elif self.role_filter == 'student':
            queryset = queryset.filter(profession_type=4)
        
        return queryset
    
    def _process_expirations(self, users):
        """Process expiration status updates for users"""
        results = {
            'newly_expired': [],
            'expiring_soon': [],
            'status_updated': [],
            'errors': [],
        }
        
        now = timezone.now()
        
        for user in users:
            try:
                old_status = user.account_status
                new_status = self._calculate_new_status(user, now)
                
                if new_status != old_status:
                    if not self.dry_run:
                        with transaction.atomic():
                            user.account_status = new_status
                            user._change_reason = f'Auto-updated by expiration checker: {old_status} -> {new_status}'
                            user.save(update_fields=['account_status'])
                    
                    # Track changes
                    if new_status == 'expired':
                        results['newly_expired'].append(user)
                    elif new_status == 'expiring_soon':
                        results['expiring_soon'].append(user)
                    else:
                        results['status_updated'].append((user, old_status, new_status))
                    
                    self.logger.info(
                        f'User {user.username} status updated: {old_status} -> {new_status}'
                    )
                
            except Exception as e:
                results['errors'].append((user, str(e)))
                self.logger.error(f'Error processing user {user.username}: {e}')
        
        return results
    
    def _calculate_new_status(self, user, now):
        """Calculate appropriate status based on expiration date"""
        if not user.access_expires_at:
            return user.account_status
        
        days_until_expiration = (user.access_expires_at.date() - now.date()).days
        
        if days_until_expiration < 0:
            return 'expired'
        elif days_until_expiration <= 30 and user.account_status == 'active':
            return 'expiring_soon'
        elif days_until_expiration > 30 and user.account_status == 'expiring_soon':
            return 'active'  # Expiration was extended
        
        return user.account_status
    
    def _display_results(self, results):
        """Display command execution results"""
        if results['newly_expired']:
            self.stdout.write(self.style.ERROR(
                f"\n{len(results['newly_expired'])} users newly expired:"
            ))
            for user in results['newly_expired']:
                self.stdout.write(f"  - {user.username} ({user.get_profession_type_display()}) - Expired: {user.access_expires_at.strftime('%d/%m/%Y')}")
        
        if results['expiring_soon']:
            self.stdout.write(self.style.WARNING(
                f"\n{len(results['expiring_soon'])} users expiring soon:"
            ))
            for user in results['expiring_soon']:
                days_left = (user.access_expires_at.date() - timezone.now().date()).days
                self.stdout.write(f"  - {user.username} ({user.get_profession_type_display()}) - {days_left} days left")
        
        if results['status_updated']:
            self.stdout.write(self.style.SUCCESS(
                f"\n{len(results['status_updated'])} status updates:"
            ))
            for user, old_status, new_status in results['status_updated']:
                self.stdout.write(f"  - {user.username}: {old_status} -> {new_status}")
        
        if results['errors']:
            self.stdout.write(self.style.ERROR(
                f"\n{len(results['errors'])} errors occurred:"
            ))
            for user, error in results['errors']:
                self.stdout.write(f"  - {user.username}: {error}")
    
    def _record_execution(self):
        """Record command execution time"""
        from django.core.cache import cache
        cache.set('expiration_checker_last_run', timezone.now(), timeout=86400)  # 24 hours
```

### 2. Expiration Notification Sender

```python
# apps/accounts/management/commands/lifecycle/send_expiration_notifications.py

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send expiration notifications to users (run daily)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show notifications that would be sent without sending them'
        )
        parser.add_argument(
            '--warning-days',
            type=int,
            nargs='+',
            default=[30, 14, 7, 3, 1],
            help='Days before expiration to send warnings'
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.warning_days = options['warning_days']
        
        self.stdout.write(self.style.SUCCESS(
            f'Sending expiration notifications (dry_run={self.dry_run})'
        ))
        
        results = {
            'notifications_sent': 0,
            'errors': [],
            'by_warning_days': {days: 0 for days in self.warning_days}
        }
        
        for warning_days in self.warning_days:
            users_to_notify = self._get_users_to_notify(warning_days)
            
            self.stdout.write(f'Found {users_to_notify.count()} users to notify ({warning_days} days)')
            
            for user in users_to_notify:
                try:
                    if self._should_send_notification(user, warning_days):
                        if not self.dry_run:
                            self._send_notification(user, warning_days)
                            self._update_notification_tracking(user)
                        
                        results['notifications_sent'] += 1
                        results['by_warning_days'][warning_days] += 1
                        
                        self.stdout.write(f"  Notification sent to {user.username}")
                
                except Exception as e:
                    results['errors'].append((user, str(e)))
                    self.logger.error(f'Error sending notification to {user.username}: {e}')
        
        self._display_notification_results(results)
    
    def _get_users_to_notify(self, warning_days):
        """Get users who should receive expiration warnings"""
        from apps.accounts.models import EqmdCustomUser
        
        target_date = timezone.now() + timedelta(days=warning_days)
        
        return EqmdCustomUser.objects.filter(
            is_active=True,
            account_status__in=['active', 'expiring_soon'],
            access_expires_at__date=target_date.date()
        ).select_related('supervisor')
    
    def _should_send_notification(self, user, warning_days):
        """Check if notification should be sent to user"""
        # Check if notification was recently sent for this warning period
        if user.expiration_warning_sent:
            days_since_warning = (timezone.now() - user.expiration_warning_sent).days
            
            # Don't send same warning twice within 7 days
            if days_since_warning < 7:
                return False
        
        return True
    
    def _send_notification(self, user, warning_days):
        """Send expiration notification email"""
        context = {
            'user': user,
            'warning_days': warning_days,
            'expiration_date': user.access_expires_at,
            'renewal_url': f"{settings.SITE_URL}/account/renewal-required/",
            'contact_email': getattr(settings, 'ADMIN_EMAIL', 'admin@equipemd.com'),
        }
        
        # Render email templates
        subject = f'EquipeMed: Seu acesso expira em {warning_days} dias'
        text_message = render_to_string('emails/expiration_warning.txt', context)
        html_message = render_to_string('emails/expiration_warning.html', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Also notify supervisor if exists
        if user.supervisor and user.supervisor.email:
            supervisor_context = context.copy()
            supervisor_context['is_supervisor_notification'] = True
            
            supervisor_subject = f'EquipeMed: Acesso de {user.get_full_name()} expira em {warning_days} dias'
            supervisor_text = render_to_string('emails/supervisor_expiration_warning.txt', supervisor_context)
            
            send_mail(
                subject=supervisor_subject,
                message=supervisor_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.supervisor.email],
                fail_silently=True  # Don't fail if supervisor email fails
            )
    
    def _update_notification_tracking(self, user):
        """Update user notification tracking"""
        user.expiration_warning_sent = timezone.now()
        user.save(update_fields=['expiration_warning_sent'])
```

### 3. Inactive User Cleanup

```python
# apps/accounts/management/commands/lifecycle/cleanup_inactive_users.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

class Command(BaseCommand):
    help = 'Identify and handle inactive users (run weekly)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--inactivity-days',
            type=int,
            default=90,
            help='Days of inactivity before marking user as inactive'
        )
        parser.add_argument(
            '--auto-suspend-days',
            type=int,
            default=180,
            help='Days of inactivity before auto-suspension'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show actions that would be taken without executing them'
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.inactivity_threshold = options['inactivity_days']
        self.suspension_threshold = options['auto_suspend_days']
        
        self.logger = logging.getLogger('lifecycle.inactive_cleanup')
        
        self.stdout.write(self.style.SUCCESS(
            f'Starting inactive user cleanup (dry_run={self.dry_run})'
        ))
        
        results = {
            'marked_inactive': [],
            'auto_suspended': [],
            'notifications_sent': 0,
            'errors': []
        }
        
        # Process inactive users
        inactive_users = self._find_inactive_users()
        results['marked_inactive'] = self._process_inactive_users(inactive_users)
        
        # Process users for auto-suspension
        suspension_candidates = self._find_suspension_candidates()
        results['auto_suspended'] = self._process_auto_suspensions(suspension_candidates)
        
        self._display_cleanup_results(results)
    
    def _find_inactive_users(self):
        """Find users who should be marked as inactive"""
        from apps.accounts.models import EqmdCustomUser
        
        cutoff_date = timezone.now() - timedelta(days=self.inactivity_threshold)
        
        return EqmdCustomUser.objects.filter(
            is_active=True,
            account_status='active',
            last_meaningful_activity__lt=cutoff_date
        ).exclude(
            profession_type__in=[0, 2]  # Don't auto-inactivate doctors and nurses
        )
    
    def _process_inactive_users(self, users):
        """Mark users as inactive and send notifications"""
        processed = []
        
        for user in users:
            try:
                if not self.dry_run:
                    user.account_status = 'inactive'
                    user._change_reason = f'Auto-marked inactive: no activity for {self.inactivity_threshold} days'
                    user.save(update_fields=['account_status'])
                    
                    # Send inactivity notification
                    self._send_inactivity_notification(user)
                
                processed.append(user)
                self.logger.info(f'User {user.username} marked as inactive')
                
            except Exception as e:
                self.logger.error(f'Error processing inactive user {user.username}: {e}')
        
        return processed
    
    def _find_suspension_candidates(self):
        """Find users who should be auto-suspended"""
        from apps.accounts.models import EqmdCustomUser
        
        cutoff_date = timezone.now() - timedelta(days=self.suspension_threshold)
        
        return EqmdCustomUser.objects.filter(
            is_active=True,
            account_status='inactive',
            last_meaningful_activity__lt=cutoff_date
        ).exclude(
            is_staff=True  # Never auto-suspend staff users
        )
    
    def _send_inactivity_notification(self, user):
        """Send notification about inactivity status"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        context = {
            'user': user,
            'inactivity_days': self.inactivity_threshold,
            'login_url': f"{settings.SITE_URL}/account/login/",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@equipemd.com'),
        }
        
        subject = 'EquipeMed: Conta marcada como inativa'
        message = render_to_string('emails/account_inactive.txt', context)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
```

## Administrative Tools

### 1. User Access Extension Tool

```python
# apps/accounts/management/commands/admin/extend_user_access.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import argparse

class Command(BaseCommand):
    help = 'Extend user access expiration date'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            help='Username of user to extend access'
        )
        parser.add_argument(
            '--days',
            type=int,
            required=True,
            help='Number of days to extend access'
        )
        parser.add_argument(
            '--reason',
            required=True,
            help='Reason for access extension'
        )
        parser.add_argument(
            '--extended-by',
            help='Username of administrator extending access (defaults to system)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force extension even if user is already expired'
        )
    
    def handle(self, *args, **options):
        from apps.accounts.models import EqmdCustomUser
        
        username = options['username']
        days = options['days']
        reason = options['reason']
        extended_by_username = options['extended_by']
        force = options['force']
        
        # Get target user
        try:
            user = EqmdCustomUser.objects.get(username=username)
        except EqmdCustomUser.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Get extending user if specified
        extended_by_user = None
        if extended_by_username:
            try:
                extended_by_user = EqmdCustomUser.objects.get(username=extended_by_username)
            except EqmdCustomUser.DoesNotExist:
                raise CommandError(f'Administrator "{extended_by_username}" does not exist')
        
        # Validate extension
        if not force and user.account_status == 'departed':
            raise CommandError(f'Cannot extend access for departed user. Use --force to override.')
        
        # Show current status
        self.stdout.write(f'Current user status:')
        self.stdout.write(f'  Username: {user.username}')
        self.stdout.write(f'  Full name: {user.get_full_name()}')
        self.stdout.write(f'  Current expiration: {user.access_expires_at or "Never expires"}')
        self.stdout.write(f'  Current status: {user.get_account_status_display()}')
        
        # Calculate new expiration
        if user.access_expires_at:
            new_expiration = user.access_expires_at + timedelta(days=days)
        else:
            new_expiration = timezone.now() + timedelta(days=days)
        
        # Confirm extension
        self.stdout.write(f'\nProposed extension:')
        self.stdout.write(f'  Extension period: {days} days')
        self.stdout.write(f'  New expiration: {new_expiration.strftime("%d/%m/%Y %H:%M")}')
        self.stdout.write(f'  Reason: {reason}')
        
        if not options.get('verbosity', 1) >= 2:  # Only prompt in interactive mode
            confirm = input('\nConfirm extension? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Extension cancelled.')
                return
        
        # Perform extension
        try:
            user.extend_access(days, reason, extended_by_user)
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully extended access for {username}'
            ))
            self.stdout.write(f'New expiration: {user.access_expires_at.strftime("%d/%m/%Y %H:%M")}')
            self.stdout.write(f'New status: {user.get_account_status_display()}')
            
        except Exception as e:
            raise CommandError(f'Failed to extend access: {e}')
```

### 2. Bulk Operations Tool

```python
# apps/accounts/management/commands/admin/bulk_user_operations.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import csv
import sys

class Command(BaseCommand):
    help = 'Perform bulk operations on users'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='operation', help='Bulk operation to perform')
        
        # Bulk extend operation
        extend_parser = subparsers.add_parser('extend', help='Bulk extend user access')
        extend_parser.add_argument('--csv-file', required=True, help='CSV file with usernames and extension data')
        extend_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
        
        # Bulk status update
        status_parser = subparsers.add_parser('update-status', help='Bulk update user status')
        status_parser.add_argument('--role', choices=['resident', 'student'], help='Filter by role')
        status_parser.add_argument('--from-status', help='Current status to update from')
        status_parser.add_argument('--to-status', required=True, help='New status to set')
        status_parser.add_argument('--reason', required=True, help='Reason for status change')
        
        # Bulk expiration set
        expiration_parser = subparsers.add_parser('set-expiration', help='Bulk set expiration dates')
        expiration_parser.add_argument('--role', choices=['resident', 'student'], required=True)
        expiration_parser.add_argument('--months', type=int, required=True, help='Months from now to expire')
        expiration_parser.add_argument('--reason', default='Bulk expiration update')
    
    def handle(self, *args, **options):
        operation = options['operation']
        
        if operation == 'extend':
            self._handle_bulk_extend(options)
        elif operation == 'update-status':
            self._handle_bulk_status_update(options)
        elif operation == 'set-expiration':
            self._handle_bulk_set_expiration(options)
        else:
            raise CommandError('No operation specified')
    
    def _handle_bulk_extend(self, options):
        """Handle bulk user access extension"""
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        self.stdout.write(f'Processing bulk extension from {csv_file}')
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                required_fields = ['username', 'days', 'reason']
                
                if not all(field in reader.fieldnames for field in required_fields):
                    raise CommandError(f'CSV must contain columns: {", ".join(required_fields)}')
                
                results = {'success': 0, 'errors': []}
                
                for row in reader:
                    try:
                        username = row['username'].strip()
                        days = int(row['days'])
                        reason = row['reason'].strip()
                        
                        if not dry_run:
                            self._extend_single_user(username, days, reason)
                        
                        results['success'] += 1
                        self.stdout.write(f'  ✓ {username}: +{days} days')
                        
                    except Exception as e:
                        results['errors'].append((row.get('username', 'Unknown'), str(e)))
                        self.stdout.write(f'  ✗ {username}: {e}')
                
                self._display_bulk_results(results, dry_run)
                
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_file}')
    
    def _extend_single_user(self, username, days, reason):
        """Extend access for a single user"""
        from apps.accounts.models import EqmdCustomUser
        
        user = EqmdCustomUser.objects.get(username=username)
        user.extend_access(days, reason, None)  # No specific admin user
    
    def _handle_bulk_set_expiration(self, options):
        """Set expiration dates for users by role"""
        from apps.accounts.models import EqmdCustomUser
        
        role = options['role']
        months = options['months']
        reason = options['reason']
        
        # Map role names to profession types
        role_mapping = {
            'resident': 1,
            'student': 4
        }
        
        profession_type = role_mapping[role]
        expiration_date = timezone.now() + timedelta(days=months * 30)
        
        users = EqmdCustomUser.objects.filter(
            profession_type=profession_type,
            is_active=True
        )
        
        self.stdout.write(f'Found {users.count()} {role}s to update')
        
        confirm = input(f'Set expiration to {expiration_date.strftime("%d/%m/%Y")} for all {role}s? (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write('Operation cancelled.')
            return
        
        with transaction.atomic():
            updated_count = users.update(
                access_expires_at=expiration_date,
                expiration_reason='end_of_internship' if role == 'resident' else 'end_of_rotation'
            )
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated expiration for {updated_count} {role}s'
        ))
```

## Reporting Commands

### 1. Comprehensive Lifecycle Report

```python
# apps/accounts/management/commands/reporting/lifecycle_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
import json
from datetime import timedelta, datetime

class Command(BaseCommand):
    help = 'Generate comprehensive user lifecycle report'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'csv', 'table'],
            default='table',
            help='Output format'
        )
        parser.add_argument(
            '--output-file',
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=90,
            help='Look ahead days for expiration analysis'
        )
    
    def handle(self, *args, **options):
        self.format = options['format']
        self.output_file = options['output_file']
        self.days_ahead = options['days_ahead']
        
        # Generate comprehensive report
        report_data = self._generate_report()
        
        # Output report
        if self.format == 'json':
            self._output_json(report_data)
        elif self.format == 'csv':
            self._output_csv(report_data)
        else:
            self._output_table(report_data)
    
    def _generate_report(self):
        """Generate comprehensive lifecycle report data"""
        from apps.accounts.models import EqmdCustomUser
        
        now = timezone.now()
        future_date = now + timedelta(days=self.days_ahead)
        
        # Basic user counts
        total_users = EqmdCustomUser.objects.filter(is_active=True).count()
        
        # Status breakdown
        status_counts = EqmdCustomUser.objects.filter(is_active=True).values(
            'account_status'
        ).annotate(count=Count('id'))
        
        # Role breakdown
        role_counts = EqmdCustomUser.objects.filter(is_active=True).values(
            'profession_type'
        ).annotate(count=Count('id'))
        
        # Expiration analysis
        expiration_analysis = self._analyze_expirations(now, future_date)
        
        # Activity analysis
        activity_analysis = self._analyze_activity(now)
        
        # Renewal requests
        renewal_stats = self._analyze_renewal_requests()
        
        return {
            'generated_at': now.isoformat(),
            'report_period': {
                'start_date': now.date().isoformat(),
                'end_date': future_date.date().isoformat(),
                'days_ahead': self.days_ahead
            },
            'summary': {
                'total_active_users': total_users,
                'status_breakdown': {item['account_status']: item['count'] for item in status_counts},
                'role_breakdown': {str(item['profession_type']): item['count'] for item in role_counts}
            },
            'expiration_analysis': expiration_analysis,
            'activity_analysis': activity_analysis,
            'renewal_requests': renewal_stats
        }
    
    def _analyze_expirations(self, now, future_date):
        """Analyze user expirations"""
        from apps.accounts.models import EqmdCustomUser
        
        # Users expiring in analysis period
        expiring_users = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__range=(now, future_date)
        ).order_by('access_expires_at')
        
        # Group by time periods
        periods = {
            'next_7_days': (now, now + timedelta(days=7)),
            'next_30_days': (now, now + timedelta(days=30)),
            'next_90_days': (now, now + timedelta(days=90))
        }
        
        expiration_breakdown = {}
        for period_name, (start, end) in periods.items():
            count = EqmdCustomUser.objects.filter(
                is_active=True,
                access_expires_at__range=(start, end)
            ).count()
            expiration_breakdown[period_name] = count
        
        # Already expired
        expired_count = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__lt=now
        ).count()
        
        return {
            'expired_users': expired_count,
            'expiring_breakdown': expiration_breakdown,
            'total_expiring_in_period': expiring_users.count(),
            'expiring_users_detail': [
                {
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'profession': user.get_profession_type_display(),
                    'expiration_date': user.access_expires_at.date().isoformat(),
                    'days_until_expiration': (user.access_expires_at.date() - now.date()).days,
                    'status': user.account_status
                }
                for user in expiring_users[:50]  # Limit for performance
            ]
        }
    
    def _output_table(self, report_data):
        """Output report as formatted table"""
        output = []
        
        # Summary section
        output.append("=" * 60)
        output.append("USER LIFECYCLE REPORT")
        output.append("=" * 60)
        output.append(f"Generated: {report_data['generated_at']}")
        output.append(f"Analysis Period: {report_data['days_ahead']} days ahead")
        output.append("")
        
        # Summary statistics
        output.append("SUMMARY STATISTICS")
        output.append("-" * 30)
        output.append(f"Total Active Users: {report_data['summary']['total_active_users']}")
        output.append("")
        
        # Status breakdown
        output.append("Status Breakdown:")
        for status, count in report_data['summary']['status_breakdown'].items():
            output.append(f"  {status}: {count}")
        output.append("")
        
        # Expiration analysis
        exp_data = report_data['expiration_analysis']
        output.append("EXPIRATION ANALYSIS")
        output.append("-" * 30)
        output.append(f"Already Expired: {exp_data['expired_users']}")
        output.append(f"Expiring in next 7 days: {exp_data['expiring_breakdown']['next_7_days']}")
        output.append(f"Expiring in next 30 days: {exp_data['expiring_breakdown']['next_30_days']}")
        output.append(f"Expiring in next 90 days: {exp_data['expiring_breakdown']['next_90_days']}")
        
        # Write output
        report_content = "\n".join(output)
        
        if self.output_file:
            with open(self.output_file, 'w') as f:
                f.write(report_content)
            self.stdout.write(f'Report written to {self.output_file}')
        else:
            self.stdout.write(report_content)
```

## Scheduled Execution

### Cron Job Configuration

```bash
# /etc/cron.d/equipemd-lifecycle

# Daily expiration checks (run at 6 AM)
0 6 * * * www-data cd /app && uv run python manage.py check_user_expiration

# Daily notification sending (run at 8 AM)
0 8 * * * www-data cd /app && uv run python manage.py send_expiration_notifications

# Weekly inactive user cleanup (run Sundays at 2 AM)
0 2 * * 0 www-data cd /app && uv run python manage.py cleanup_inactive_users

# Monthly comprehensive reports (run 1st of month at 7 AM)
0 7 1 * * www-data cd /app && uv run python manage.py lifecycle_report --format json --output-file /app/reports/lifecycle_$(date +\%Y\%m).json
```

### Django Management Command Scheduler

```python
# apps/core/management/commands/run_lifecycle_scheduler.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
import schedule
import time
import logging

class Command(BaseCommand):
    help = 'Run lifecycle management scheduler (for environments without cron)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (keeps running)'
        )
    
    def handle(self, *args, **options):
        self.logger = logging.getLogger('lifecycle.scheduler')
        daemon_mode = options['daemon']
        
        self.stdout.write('Starting lifecycle scheduler...')
        
        # Schedule daily tasks
        schedule.every().day.at("06:00").do(self._run_expiration_check)
        schedule.every().day.at("08:00").do(self._run_notification_sender)
        
        # Schedule weekly tasks
        schedule.every().sunday.at("02:00").do(self._run_inactive_cleanup)
        
        # Schedule monthly tasks
        schedule.every().month.do(self._run_monthly_report)
        
        if daemon_mode:
            self.stdout.write('Running in daemon mode. Press Ctrl+C to stop.')
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                self.stdout.write('Scheduler stopped.')
        else:
            # Run pending tasks once and exit
            schedule.run_pending()
            self.stdout.write('Scheduled tasks completed.')
    
    def _run_expiration_check(self):
        """Run daily expiration check"""
        self.logger.info('Running scheduled expiration check')
        try:
            call_command('check_user_expiration')
        except Exception as e:
            self.logger.error(f'Error in expiration check: {e}')
    
    def _run_notification_sender(self):
        """Run daily notification sender"""
        self.logger.info('Running scheduled notification sender')
        try:
            call_command('send_expiration_notifications')
        except Exception as e:
            self.logger.error(f'Error in notification sender: {e}')
```

## Testing Strategy

### Command Testing Framework

```python
# apps/accounts/tests/test_lifecycle_commands.py

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO
from datetime import timedelta
from apps.accounts.models import EqmdCustomUser

class LifecycleCommandTests(TestCase):
    def setUp(self):
        # Create test users with various expiration states
        self.active_user = EqmdCustomUser.objects.create_user(
            username='active_user',
            email='active@test.com',
            access_expires_at=timezone.now() + timedelta(days=60)
        )
        
        self.expiring_user = EqmdCustomUser.objects.create_user(
            username='expiring_user',
            email='expiring@test.com',
            access_expires_at=timezone.now() + timedelta(days=15)
        )
        
        self.expired_user = EqmdCustomUser.objects.create_user(
            username='expired_user',
            email='expired@test.com',
            access_expires_at=timezone.now() - timedelta(days=5)
        )
    
    def test_expiration_check_command(self):
        """Test expiration checking command"""
        out = StringIO()
        
        # Run command
        call_command('check_user_expiration', '--dry-run', stdout=out)
        
        # Verify output
        output = out.getvalue()
        self.assertIn('expiring_user', output)
        self.assertIn('expired_user', output)
    
    def test_user_extension_command(self):
        """Test user access extension command"""
        out = StringIO()
        
        # Extend expired user access
        call_command(
            'extend_user_access',
            'expired_user',
            '--days', '90',
            '--reason', 'Test extension',
            '--force',
            stdout=out
        )
        
        # Verify extension
        self.expired_user.refresh_from_db()
        self.assertTrue(self.expired_user.access_expires_at > timezone.now())
```

## Success Metrics

### Operational Metrics

- ✅ **Automation Coverage**: 100% of daily/weekly tasks automated
- ✅ **Command Reliability**: <1% failure rate for management commands
- ✅ **Notification Delivery**: >95% successful email delivery rate
- ✅ **Performance**: Commands complete within acceptable time limits

### Administrative Efficiency  

- ✅ **Manual Effort Reduction**: 80% reduction in manual user management tasks
- ✅ **Report Generation**: Automated monthly lifecycle reports
- ✅ **Bulk Operations**: Support for managing 100+ users efficiently

---

**Next Phase**: [Phase 4: Admin Interface and Dashboards](phase_4_admin_interface.md)
