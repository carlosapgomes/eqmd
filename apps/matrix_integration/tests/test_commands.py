from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.matrix_integration.services import MatrixConfig


class MatrixProvisionRoomsCommandTests(TestCase):
    @mock.patch(
        "apps.matrix_integration.management.commands.matrix_provision_rooms.MatrixConfig.from_env"
    )
    @mock.patch(
        "apps.matrix_integration.management.commands.matrix_provision_rooms.SynapseAdminClient.ensure_user"
    )
    @mock.patch(
        "apps.matrix_integration.management.commands.matrix_provision_rooms.MatrixClient"
    )
    def test_matrix_provision_rooms_uses_localpart(
        self,
        matrix_client,
        ensure_user,
        from_env,
    ):
        user = UserFactory()
        user.profile.matrix_localpart = "joao.silva"
        user.profile.save()

        config = MatrixConfig(
            matrix_fqdn="matrix.test",
            admin_base_url="http://matrix-admin.test",
            client_base_url="http://matrix-client.test",
            admin_token="admin-token",
            oidc_provider_id="equipemed",
            bot_user_id="@bot:matrix.test",
            bot_access_token="bot-token",
            global_room_name="EquipeMed",
        )
        from_env.return_value = config

        call_command("matrix_provision_rooms", "--skip-global", "--skip-dm")

        call_args = ensure_user.call_args
        self.assertIsNotNone(call_args)
        if call_args.args:
            matrix_user_id = call_args.args[0]
        else:
            matrix_user_id = call_args.kwargs.get("user_id")
        self.assertEqual(matrix_user_id, "@joao.silva:matrix.test")
