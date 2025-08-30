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