"""
Management command to create a new bot client.
"""

from django.core.management.base import BaseCommand, CommandError
from apps.botauth.bot_service import BotClientService, ALLOWED_BOT_SCOPES


class Command(BaseCommand):
    help = 'Create a new bot client for OIDC delegation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            help='Display name for the bot'
        )
        parser.add_argument(
            '--description',
            default='',
            help='Description of the bot'
        )
        parser.add_argument(
            '--scopes',
            nargs='+',
            default=[],
            help=f'Allowed scopes (choose from: {", ".join(ALLOWED_BOT_SCOPES)})'
        )
    
    def handle(self, *args, **options):
        name = options['name']
        description = options['description']
        scopes = options['scopes']
        
        # Validate scopes
        for scope in scopes:
            if scope not in ALLOWED_BOT_SCOPES:
                raise CommandError(
                    f"Invalid scope: {scope}\n"
                    f"Allowed scopes: {', '.join(ALLOWED_BOT_SCOPES)}"
                )
        
        try:
            bot_profile, client_secret = BotClientService.create_bot(
                display_name=name,
                description=description,
                allowed_scopes=scopes
            )
            
            self.stdout.write(self.style.SUCCESS(f'\nBot created successfully!\n'))
            self.stdout.write(f'Name: {bot_profile.display_name}')
            self.stdout.write(f'Client ID: {bot_profile.client.client_id}')
            self.stdout.write(
                self.style.WARNING(f'Client Secret: {client_secret}')
            )
            self.stdout.write(f'Allowed Scopes: {", ".join(scopes) or "(none)"}')
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  Save the client secret now! It cannot be retrieved later.'
                )
            )
            
        except ValueError as e:
            raise CommandError(str(e))