from django.core.management.base import BaseCommand, CommandError

from apps.matrix_integration.services import MatrixConfig, SynapseAdminClient


class Command(BaseCommand):
    help = "Create or update the Matrix bot user and output an access token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            default=None,
            help="Matrix user ID for the bot (default: MATRIX_BOT_USER_ID)",
        )
        parser.add_argument(
            "--display-name",
            default=None,
            help="Display name to set for the bot",
        )
        parser.add_argument(
            "--admin",
            action="store_true",
            help="Grant Synapse admin status to the bot",
        )

    def handle(self, *args, **options):
        config = MatrixConfig.from_env()
        if not config.admin_token:
            raise CommandError("SYNAPSE_ADMIN_TOKEN is required")

        user_id = options["user_id"] or config.bot_user_id
        display_name = options["display_name"] or config.bot_display_name
        admin_flag = options["admin"]

        admin_client = SynapseAdminClient(config)
        admin_client.ensure_user(
            user_id,
            display_name=display_name,
            admin=admin_flag,
            deactivated=False,
        )
        login_payload = admin_client.create_login_token(user_id)
        token = login_payload.get("access_token")
        if not token:
            raise CommandError("Failed to retrieve bot access token")

        self.stdout.write(self.style.SUCCESS("✓ Matrix bot user ready"))
        self.stdout.write(f"User: {user_id}")
        self.stdout.write("Set this in your .env:")
        self.stdout.write(f"MATRIX_BOT_ACCESS_TOKEN={token}")
