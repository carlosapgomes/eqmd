from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.matrix_integration.models import MatrixGlobalRoom
from apps.matrix_integration.services import (
    MatrixApiError,
    MatrixClient,
    MatrixConfig,
    SynapseAdminClient,
    build_external_ids,
    build_matrix_user_id,
    display_name_for_user,
)


BLOCKED_STATUSES = {"inactive", "suspended", "departed", "expired"}


def is_user_active(user):
    if not user.is_active:
        return False
    account_status = getattr(user, "account_status", "active")
    if account_status in BLOCKED_STATUSES:
        return False
    return True


class Command(BaseCommand):
    help = "Sync Matrix user activation/deactivation with EQMD lifecycle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-global",
            action="store_true",
            help="Skip global room kicks for inactive users",
        )

    def handle(self, *args, **options):
        config = MatrixConfig.from_env()
        if not config.admin_token:
            raise CommandError("SYNAPSE_ADMIN_TOKEN is required")

        admin_client = SynapseAdminClient(config)
        matrix_client = MatrixClient(config) if config.bot_access_token else None
        global_room = None
        if not options["skip_global"]:
            global_room = MatrixGlobalRoom.objects.first()

        User = get_user_model()
        users = User.objects.all()
        for user in users:
            localpart = None
            try:
                localpart = user.profile.matrix_localpart
            except Exception:
                localpart = None
            matrix_user_id = build_matrix_user_id(user, config.matrix_fqdn)
            if not localpart:
                self.stdout.write(
                    self.style.WARNING(
                        f"Matrix localpart missing for {user}. Using fallback {matrix_user_id}"
                    )
                )
            display_name = display_name_for_user(user)
            external_ids = build_external_ids(user, config.oidc_provider_id)
            if is_user_active(user):
                admin_client.reactivate_user(
                    matrix_user_id,
                    display_name=display_name,
                    external_ids=external_ids,
                )
                continue

            try:
                admin_client.deactivate_user(matrix_user_id, erase=False)
                self.stdout.write(f"Deactivated {matrix_user_id}")
            except MatrixApiError as exc:
                self.stdout.write(self.style.WARNING(f"Deactivate failed: {exc}"))

            if global_room and matrix_client:
                try:
                    matrix_client.kick_user(
                        global_room.room_id,
                        matrix_user_id,
                        reason="Account inactive",
                    )
                except MatrixApiError as exc:
                    self.stdout.write(
                        self.style.WARNING(f"Kick failed for {matrix_user_id}: {exc}")
                    )

        self.stdout.write(self.style.SUCCESS("✓ Matrix lifecycle sync complete"))
