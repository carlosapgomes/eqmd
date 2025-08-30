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