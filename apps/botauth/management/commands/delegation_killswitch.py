"""
Management command for bot delegation kill switch.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.botauth.killswitch import KillSwitchService

User = get_user_model()


class Command(BaseCommand):
    help = 'Control bot delegation kill switch'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'disable', 'enable', 'maintenance-on', 'maintenance-off'],
            help='Action to perform'
        )
        parser.add_argument(
            '--reason',
            default='',
            help='Reason for disable action'
        )
        parser.add_argument(
            '--message',
            default='',
            help='Maintenance message'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'status':
            status = KillSwitchService.get_status()
            self.stdout.write(f"\nBot Delegation Status:")
            self.stdout.write(f"  Enabled: {status['enabled']}")
            self.stdout.write(f"  Maintenance: {status['maintenance_mode']}")
            if not status['enabled']:
                self.stdout.write(f"  Disabled at: {status['disabled_at']}")
                self.stdout.write(f"  Reason: {status['disabled_reason']}")
        
        elif action == 'disable':
            # Use system user for CLI operations
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                raise CommandError(
                    'No superuser found. Please create a superuser first.'
                )
            
            KillSwitchService.disable_delegation(
                system_user,
                reason=options['reason'] or 'CLI disable'
            )
            self.stdout.write(
                self.style.ERROR('🚨 Bot delegation DISABLED')
            )
        
        elif action == 'enable':
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                raise CommandError(
                    'No superuser found. Please create a superuser first.'
                )
            
            KillSwitchService.enable_delegation(system_user)
            self.stdout.write(
                self.style.SUCCESS('✅ Bot delegation enabled')
            )
        
        elif action == 'maintenance-on':
            KillSwitchService.enable_maintenance(options['message'])
            self.stdout.write('Maintenance mode enabled')
        
        elif action == 'maintenance-off':
            KillSwitchService.disable_maintenance()
            self.stdout.write('Maintenance mode disabled')