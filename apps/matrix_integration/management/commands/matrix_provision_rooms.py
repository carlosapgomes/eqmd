from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.matrix_integration.models import MatrixDirectRoom, MatrixGlobalRoom
from apps.matrix_integration.services import (
    MatrixApiError,
    MatrixClient,
    MatrixConfig,
    SynapseAdminClient,
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
    help = "Provision Matrix rooms for active users (DM + global room)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--global-room-name",
            default=None,
            help="Override MATRIX_GLOBAL_ROOM_NAME",
        )
        parser.add_argument(
            "--skip-global",
            action="store_true",
            help="Skip global room provisioning",
        )
        parser.add_argument(
            "--skip-dm",
            action="store_true",
            help="Skip per-user DM provisioning",
        )

    def handle(self, *args, **options):
        config = MatrixConfig.from_env()
        if not config.admin_token:
            raise CommandError("SYNAPSE_ADMIN_TOKEN is required")
        if not config.bot_access_token:
            raise CommandError("MATRIX_BOT_ACCESS_TOKEN is required")

        admin_client = SynapseAdminClient(config)
        matrix_client = MatrixClient(config)

        global_room = None
        if not options["skip_global"]:
            global_room = self._ensure_global_room(matrix_client, config, options)

        User = get_user_model()
        active_users = [user for user in User.objects.filter(is_active=True) if is_user_active(user)]
        self.stdout.write(f"Active users: {len(active_users)}")

        for user in active_users:
            matrix_user_id = build_matrix_user_id(user, config.matrix_fqdn)
            display_name = display_name_for_user(user)
            admin_client.ensure_user(matrix_user_id, display_name=display_name)

            if not options["skip_dm"]:
                self._ensure_direct_room(matrix_client, user, matrix_user_id)

            if global_room:
                self._invite_to_global(matrix_client, matrix_user_id, global_room)

        self.stdout.write(self.style.SUCCESS("✓ Matrix provisioning complete"))

    def _ensure_global_room(self, matrix_client, config, options):
        global_room = MatrixGlobalRoom.objects.first()
        if global_room:
            self.stdout.write(f"Global room exists: {global_room.room_id}")
            return global_room

        name = options["global_room_name"] or config.global_room_name
        payload = {
            "name": name,
            "preset": "private_chat",
        }
        response = matrix_client.create_room(payload)
        room_id = response.get("room_id")
        if not room_id:
            raise CommandError("Failed to create global room")
        global_room = MatrixGlobalRoom.objects.create(room_id=room_id, name=name)
        self.stdout.write(f"Created global room: {room_id}")
        return global_room

    def _ensure_direct_room(self, matrix_client, user, matrix_user_id):
        direct_room = MatrixDirectRoom.objects.filter(user=user).first()
        if direct_room:
            return direct_room

        payload = {
            "invite": [matrix_user_id],
            "is_direct": True,
            "preset": "private_chat",
        }
        response = matrix_client.create_room(payload)
        room_id = response.get("room_id")
        if not room_id:
            raise CommandError(f"Failed to create DM room for {matrix_user_id}")

        direct_room = MatrixDirectRoom.objects.create(user=user, room_id=room_id)
        self.stdout.write(f"Created DM room for {matrix_user_id}: {room_id}")
        return direct_room

    def _invite_to_global(self, matrix_client, matrix_user_id, global_room):
        try:
            matrix_client.invite_user(global_room.room_id, matrix_user_id)
            self.stdout.write(f"Invited {matrix_user_id} to global room")
        except MatrixApiError as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"Invite skipped for {matrix_user_id}: {exc}"
                )
            )
