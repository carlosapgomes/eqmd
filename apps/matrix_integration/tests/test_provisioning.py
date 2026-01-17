from unittest import mock

from django.test import TestCase

from apps.accounts.tests.factories import SuperUserFactory, UserFactory
from apps.botauth.models import MatrixUserBinding
from apps.matrix_integration.services import (
    MatrixConfig,
    MatrixProvisioningError,
    MatrixProvisioningService,
    build_matrix_user_id,
)


class MatrixProvisioningServiceTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.admin_user = SuperUserFactory()
        self.config = MatrixConfig(
            matrix_fqdn="matrix.test",
            admin_base_url="http://matrix-admin.test",
            client_base_url="http://matrix-client.test",
            admin_token="admin-token",
            oidc_provider_id="equipemed",
            bot_user_id="@bot:matrix.test",
            bot_access_token="",
            global_room_name="EquipeMed",
        )

    @mock.patch("apps.matrix_integration.services.SynapseAdminClient.ensure_user")
    def test_provision_creates_verified_binding(self, ensure_user):
        self.user.profile.matrix_localpart = "joao.silva"
        self.user.profile.save()

        matrix_user_id = MatrixProvisioningService.provision_user(
            self.user,
            self.config,
            performed_by=self.admin_user,
        )

        binding = MatrixUserBinding.objects.get(user=self.user)
        self.assertTrue(binding.verified)
        self.assertEqual(binding.matrix_id, matrix_user_id)

        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.matrix_provisioned_at)
        self.assertEqual(self.user.profile.matrix_provisioned_by, self.admin_user)

        ensure_user.assert_called_once()
        call_kwargs = ensure_user.call_args.kwargs
        self.assertEqual(
            call_kwargs["external_ids"],
            [
                {
                    "auth_provider": "oidc-equipemed",
                    "external_id": str(self.user.profile.public_id),
                }
            ],
        )

    def test_provision_requires_localpart(self):
        with self.assertRaises(MatrixProvisioningError):
            MatrixProvisioningService.provision_user(self.user, self.config)


class MatrixUserIdTests(TestCase):
    def test_build_matrix_user_id_uses_localpart(self):
        user = UserFactory()
        user.profile.matrix_localpart = "joao.silva"
        user.profile.save()

        matrix_user_id = build_matrix_user_id(user, "matrix.test")
        self.assertEqual(matrix_user_id, "@joao.silva:matrix.test")
