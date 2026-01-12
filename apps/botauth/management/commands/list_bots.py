"""
Management command to list all bot clients.
"""

from django.core.management.base import BaseCommand
from apps.botauth.models import BotClientProfile


class Command(BaseCommand):
    help = 'List all registered bot clients'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active bots'
        )
    
    def handle(self, *args, **options):
        queryset = BotClientProfile.objects.select_related('client').all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
        
        if not queryset.exists():
            self.stdout.write('No bots registered.')
            return
        
        self.stdout.write(f'\n{"Name":<30} {"Client ID":<25} {"Status":<10} {"Scopes":<30}')
        self.stdout.write('-' * 95)
        
        for bot in queryset:
            status = '🟢 Active' if bot.is_active else '🔴 Suspended'
            scopes = ', '.join(bot.allowed_scopes[:3])
            if len(bot.allowed_scopes) > 3:
                scopes += f' (+{len(bot.allowed_scopes) - 3})'
            
            self.stdout.write(
                f'{bot.display_name:<30} '
                f'{bot.client.client_id[:20]:<25} '
                f'{status:<10} '
                f'{scopes:<30}'
            )
        
        self.stdout.write(f'\nTotal: {queryset.count()} bot(s)')