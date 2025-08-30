# Phase 3: Simplified Management Commands and Automation

## Overview
**Timeline: 1 week**
**Priority: Medium**

Implement **essential** automated maintenance tasks and basic administrative tools. This simplified phase focuses on core daily automation without complex reporting or advanced features.

## Essential Command Structure (Simplified)

```
apps/accounts/management/commands/
├── check_user_expiration.py          # Daily expiration checks (essential)
├── send_expiration_notifications.py  # Email notifications only (essential)
├── extend_user_access.py              # Manual access extension (essential)
├── bulk_user_operations.py            # Basic bulk operations (essential)
└── cleanup_inactive_users.py         # Reports only - no auto-changes (simplified)
```

## Essential Daily Commands

### 1. Simplified User Expiration Checker

```python
# apps/accounts/management/commands/check_user_expiration.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

class Command(BaseCommand):
    help = 'Check and update user expiration statuses (simplified - run daily)'
    
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
            '--role',
            choices=['resident', 'student', 'all'],
            default='all',
            help='Check specific user roles only'
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.role_filter = options['role']
        
        self.stdout.write(self.style.SUCCESS(
            f'Starting simplified expiration check (dry_run={self.dry_run})'
        ))
        
        # Get users to check
        users_to_check = self._get_users_to_check()
        
        self.stdout.write(f'Found {users_to_check.count()} users to check')
        
        # Process expiration updates
        results = self._process_expirations(users_to_check)
        
        # Display results
        self._display_results(results)
    
    def _get_users_to_check(self):
        """Get users that need expiration checking"""
        from apps.accounts.models import EqmdCustomUser
        
        queryset = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__isnull=False
        )
        
        # Apply role filtering
        if self.role_filter == 'resident':
            queryset = queryset.filter(profession_type=1)
        elif self.role_filter == 'student':
            queryset = queryset.filter(profession_type=4)
        
        return queryset
    
    def _process_expirations(self, users):
        """Process expiration status updates for users (simplified logic)"""
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
                new_status = self._calculate_simple_status(user, now)
                
                if new_status != old_status:
                    if not self.dry_run:
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
    
    def _calculate_simple_status(self, user, now):
        """Calculate appropriate status based on expiration date (simplified)"""
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
        
        if results['errors']:
            self.stdout.write(self.style.ERROR(
                f"\n{len(results['errors'])} errors occurred:"
            ))
            for user, error in results['errors']:
                self.stdout.write(f"  - {user.username}: {error}")
```

### 2. Simplified Expiration Notifications (Email Only)

```python
# apps/accounts/management/commands/send_expiration_notifications.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send expiration notifications via email only (simplified - run daily)'
    
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
            f'Sending expiration notifications (simplified - email only, dry_run={self.dry_run})'
        ))
        
        results = {
            'notifications_sent': 0,
            'errors': []
        }
        
        for warning_days in self.warning_days:
            users_to_notify = self._get_users_to_notify(warning_days)
            
            self.stdout.write(f'Found {users_to_notify.count()} users to notify ({warning_days} days)')
            
            for user in users_to_notify:
                try:
                    if self._should_send_notification(user):
                        if not self.dry_run:
                            self._send_simple_notification(user, warning_days)
                            self._update_notification_tracking(user)
                        
                        results['notifications_sent'] += 1
                        self.stdout.write(f"  Email sent to {user.username}")
                
                except Exception as e:
                    results['errors'].append((user, str(e)))
                    self.logger.error(f'Error sending notification to {user.username}: {e}')
        
        self.stdout.write(self.style.SUCCESS(
            f"Sent {results['notifications_sent']} notifications, {len(results['errors'])} errors"
        ))
    
    def _get_users_to_notify(self, warning_days):
        """Get users who should receive expiration warnings"""
        from apps.accounts.models import EqmdCustomUser
        
        target_date = timezone.now() + timedelta(days=warning_days)
        
        return EqmdCustomUser.objects.filter(
            is_active=True,
            account_status__in=['active', 'expiring_soon'],
            access_expires_at__date=target_date.date()
        )
    
    def _should_send_notification(self, user):
        """Check if notification should be sent (simplified)"""
        # Only send one notification per week to avoid spam
        if user.expiration_warning_sent:
            days_since_warning = (timezone.now() - user.expiration_warning_sent).days
            if days_since_warning < 7:
                return False
        
        return True
    
    def _send_simple_notification(self, user, warning_days):
        """Send simplified expiration notification email"""
        from apps.core.services.simple_notifications import send_expiration_warning_email
        send_expiration_warning_email(user, warning_days)
    
    def _update_notification_tracking(self, user):
        """Update user notification tracking"""
        user.expiration_warning_sent = timezone.now()
        user.save(update_fields=['expiration_warning_sent'])
```

### 3. Inactive User Reporter (No Auto-Changes)

```python
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
            days_inactive = (timezone.now().date() - user.last_meaningful_activity.date()).days
            self.stdout.write(
                f"{user.username:<20} "
                f"{user.get_profession_type_display():<15} "
                f"{user.last_meaningful_activity.strftime('%d/%m/%Y'):<12} "
                f"{days_inactive:<5}"
            )
        
        self.stdout.write("\nRECOMMENDATION: Review these users for potential status updates")
```

## Essential Administrative Tools

### 1. Simplified User Access Extension

```python
# apps/accounts/management/commands/extend_user_access.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Extend user access expiration date (simplified)'
    
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
            '--force',
            action='store_true',
            help='Force extension even if user is expired/departed'
        )
    
    def handle(self, *args, **options):
        from apps.accounts.models import EqmdCustomUser
        
        username = options['username']
        days = options['days']
        reason = options['reason']
        force = options['force']
        
        # Get target user
        try:
            user = EqmdCustomUser.objects.get(username=username)
        except EqmdCustomUser.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Validate extension
        if not force and user.account_status == 'departed':
            raise CommandError(f'Cannot extend access for departed user. Use --force to override.')
        
        # Show current status
        self.stdout.write(f'Current user status:')
        self.stdout.write(f'  Username: {user.username}')
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
        
        confirm = input('\nConfirm extension? (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write('Extension cancelled.')
            return
        
        # Perform extension
        try:
            user.extend_access(days, reason, None)  # No admin user tracking in simplified version
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully extended access for {username}'
            ))
            self.stdout.write(f'New expiration: {user.access_expires_at.strftime("%d/%m/%Y %H:%M")}')
            self.stdout.write(f'New status: {user.get_account_status_display()}')
            
        except Exception as e:
            raise CommandError(f'Failed to extend access: {e}')
```

### 2. Essential Bulk Operations

```python
# apps/accounts/management/commands/bulk_user_operations.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import csv

class Command(BaseCommand):
    help = 'Perform essential bulk operations on users (simplified)'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='operation', help='Bulk operation to perform')
        
        # Bulk extend operation
        extend_parser = subparsers.add_parser('extend', help='Bulk extend user access')
        extend_parser.add_argument('--csv-file', required=True, help='CSV file with usernames and extension data')
        extend_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
        
        # Bulk expiration set (simplified)
        expiration_parser = subparsers.add_parser('set-expiration', help='Bulk set expiration dates')
        expiration_parser.add_argument('--role', choices=['resident', 'student'], required=True)
        expiration_parser.add_argument('--months', type=int, required=True, help='Months from now to expire')
        expiration_parser.add_argument('--reason', default='Bulk expiration update')
    
    def handle(self, *args, **options):
        operation = options['operation']
        
        if operation == 'extend':
            self._handle_bulk_extend(options)
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
                
                self.stdout.write(self.style.SUCCESS(
                    f"Success: {results['success']}, Errors: {len(results['errors'])}"
                ))
                
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_file}')
    
    def _extend_single_user(self, username, days, reason):
        """Extend access for a single user"""
        from apps.accounts.models import EqmdCustomUser
        
        user = EqmdCustomUser.objects.get(username=username)
        user.extend_access(days, reason, None)
    
    def _handle_bulk_set_expiration(self, options):
        """Set expiration dates for users by role (simplified)"""
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

## Simple Reporting Command

### Basic Lifecycle Report (CSV Only)

```python
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
```

## Simplified Scheduling

### Basic Cron Configuration

```bash
# /etc/cron.d/equipemd-lifecycle-simple

# Daily expiration checks (run at 6 AM)
0 6 * * * www-data cd /app && uv run python manage.py check_user_expiration

# Daily notification sending (run at 8 AM) 
0 8 * * * www-data cd /app && uv run python manage.py send_expiration_notifications

# Weekly inactive user reports (run Sundays at 7 AM)
0 7 * * 0 www-data cd /app && uv run python manage.py cleanup_inactive_users --format csv --output-file /app/reports/inactive_users_$(date +\%Y\%m\%d).csv
```

## Testing Strategy (Simplified)

### Essential Command Tests

```python
# apps/accounts/tests/test_simplified_commands.py

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO
from datetime import timedelta
from apps.accounts.models import EqmdCustomUser

class SimplifiedCommandTests(TestCase):
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
        """Test simplified expiration checking command"""
        out = StringIO()
        
        # Run command
        call_command('check_user_expiration', '--dry-run', stdout=out)
        
        # Verify output mentions relevant users
        output = out.getvalue()
        self.assertIn('expiring_user', output)
        self.assertIn('expired_user', output)
    
    def test_user_extension_command(self):
        """Test simplified user access extension command"""
        out = StringIO()
        
        # Mock user input for confirmation
        import unittest.mock
        with unittest.mock.patch('builtins.input', return_value='y'):
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
    
    def test_inactive_user_report(self):
        """Test inactive user reporting command"""
        # Create inactive user
        inactive_user = EqmdCustomUser.objects.create_user(
            username='inactive_user',
            email='inactive@test.com',
            last_meaningful_activity=timezone.now() - timedelta(days=120)
        )
        
        out = StringIO()
        call_command('cleanup_inactive_users', '--inactivity-days', '90', stdout=out)
        
        output = out.getvalue()
        self.assertIn('inactive_user', output)
        self.assertIn('RECOMMENDATION', output)  # Should be report-only
```

## What Was Simplified

### ❌ Removed from Original:
- **Complex Activity Categorization**: All activities treated equally with simple timestamp
- **Advanced Bulk Operations**: Reduced to essential extend and set-expiration only
- **Automated Status Changes**: `cleanup_inactive_users` only reports, doesn't auto-change
- **Complex Reporting**: Only basic CSV export, no JSON/analytics
- **Performance Optimizations**: No caching, batching, or async processing
- **Advanced Scheduling**: Basic cron jobs only, no Django scheduler
- **Notification Tracking**: Simplified to basic "last sent" timestamp

### ✅ Kept (Essential):
- Daily expiration checking and status updates
- Email-only expiration notifications
- Manual user access extension tools
- Basic bulk operations (extend, set expiration)
- Simple inactive user reporting
- CSV export for basic lifecycle data

## Success Metrics (Simplified)

### Operational Metrics
- ✅ **Essential Automation**: Daily expiration checks and email notifications
- ✅ **Command Reliability**: Basic commands run without errors
- ✅ **Email Delivery**: Expiration warnings sent successfully
- ✅ **Admin Tools**: Manual extension and bulk operations available

### Administrative Efficiency
- ✅ **Manual Process Reduction**: Automated daily expiration checking
- ✅ **Basic Reporting**: CSV reports for inactive user review
- ✅ **Essential Bulk Operations**: Support for managing multiple users at once

---

**Next Phase**: [Future Enhancements](future_enhancements.md)