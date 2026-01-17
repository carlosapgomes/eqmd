import asyncio

from django.core.management.base import BaseCommand, CommandError

from apps.matrix_integration.bot.runtime import MatrixBotService
from apps.matrix_integration.models import MatrixBotConversationState
from apps.matrix_integration.services import MatrixConfig


class Command(BaseCommand):
    help = "Run the Matrix bot event loop."

    def handle(self, *args, **options):
        config = MatrixConfig.from_env()
        if not config.bot_access_token:
            raise CommandError("MATRIX_BOT_ACCESS_TOKEN is required")

        MatrixBotConversationState.objects.all().delete()
        service = MatrixBotService(config)
        asyncio.run(service.run())
