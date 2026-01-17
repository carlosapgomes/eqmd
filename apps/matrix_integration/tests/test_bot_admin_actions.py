from unittest import mock

from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from apps.accounts.admin import EqmdCustomUserAdmin
from apps.accounts.tests.factories import SuperUserFactory, UserFactory
from apps.accounts.models import EqmdCustomUser


class BotAdminActionTests(TestCase):
    def setUp(self):
        self.admin_user = SuperUserFactory(is_staff=True, is_superuser=True)
        self.user = UserFactory()
        self.request = RequestFactory().post("/")
        self.request.user = self.admin_user
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)
        self.admin = EqmdCustomUserAdmin(EqmdCustomUser, admin.site)

    @mock.patch("apps.accounts.admin.MatrixRoomProvisioningService.ensure_direct_room")
    @mock.patch("apps.accounts.admin.MatrixProvisioningService.provision_user")
    def test_reprovision_dm_room_action_calls_services(self, provision_user, ensure_room):
        provision_user.return_value = "@joao:matrix.test"
        queryset = EqmdCustomUser.objects.filter(pk=self.user.pk)

        self.admin.reprovision_matrix_dm_room(self.request, queryset)

        provision_user.assert_called_once()
        ensure_room.assert_called_once()
