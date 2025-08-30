# apps/accounts/management/commands/send_expiration_notifications.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

class Command(BaseCommand):
    help = 'Send expiration notifications via email only (simplified - run daily)'
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('lifecycle.notifications')
    
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