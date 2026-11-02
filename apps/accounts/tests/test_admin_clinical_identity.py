"""Admin guardrails requiring ``profession_type`` for clinical users.

D3: Django admin user forms require ``profession_type`` unless the
user is a superuser or belongs to ``User Managers``. The model field
stays nullable, so the guard lives only in the admin form path.
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.formats import localize_input

from apps.accounts.admin import EqmdCustomUserAdmin
from apps.accounts.models import EqmdCustomUser
from apps.accounts.tests.factories import SuperUserFactory, UserFactory

User = get_user_model()

USER_MANAGERS = "User Managers"


def change_form_data(user, **overrides):
    """Build the change-form payload for ``user`` with all fields present."""
    data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profession_type": "" if user.profession_type is None else user.profession_type,
        "professional_registration_number": user.professional_registration_number,
        "country_id_number": user.country_id_number,
        "fiscal_number": user.fiscal_number,
        "phone": user.phone,
        "account_status": user.account_status,
        "expiration_reason": user.expiration_reason,
        "is_active": "on" if user.is_active else "",
        "is_staff": "on" if user.is_staff else "",
        "is_superuser": "on" if user.is_superuser else "",
        "groups": list(user.groups.values_list("pk", flat=True)),
        "user_permissions": list(user.user_permissions.values_list("pk", flat=True)),
        "is_researcher": "on" if user.is_researcher else "",
        "password_change_required": "on" if user.password_change_required else "",
        "terms_accepted": "on" if user.terms_accepted else "",
    }
    date_joined, time_joined = localize_input(user.date_joined).split(" ")
    data["date_joined_0"] = date_joined
    data["date_joined_1"] = time_joined
    data.update(overrides)
    return data


def add_form_data(**overrides):
    """Build a valid admin add-form payload for a regular clinical user."""
    data = {
        "username": "novo.clinico",
        "email": "novo.clinico@example.com",
        "password1": "complexpassword123",
        "password2": "complexpassword123",
        "first_name": "Novo",
        "last_name": "Clinico",
        "profession_type": "",
        "professional_registration_number": "CRM-9999",
        "country_id_number": "",
        "fiscal_number": "",
        "phone": "",
        "_save": "Save",
    }
    data.update(overrides)
    return data


class ClinicalIdentityAdminFormTests(TestCase):
    """R1: admin change form rejects profession-less clinical users."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = EqmdCustomUserAdmin(EqmdCustomUser, self.site)
        self.request = RequestFactory().get("/admin/accounts/eqmdcustomuser/")
        self.request.user = SuperUserFactory(username="request.superuser")

    def _change_form(self, user, **overrides):
        form_class = self.admin.get_form(self.request, user, change=True)
        return form_class(data=change_form_data(user, **overrides), instance=user)

    def test_regular_user_change_without_profession_is_rejected(self):
        user = UserFactory(username="regular.user", profession_type=None)

        form = self._change_form(user, profession_type="")

        self.assertFalse(form.is_valid())
        self.assertIn("profession_type", form.errors)
        user.refresh_from_db()
        self.assertIsNone(user.profession_type)

    def test_regular_user_change_with_profession_is_accepted(self):
        user = UserFactory(username="regular.user", profession_type=None)

        form = self._change_form(user, profession_type=EqmdCustomUser.NURSE)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        user.refresh_from_db()
        self.assertEqual(user.profession_type, EqmdCustomUser.NURSE)

    def test_superuser_change_without_profession_is_accepted(self):
        user = SuperUserFactory(username="super.user", profession_type=None)

        form = self._change_form(user, profession_type="", is_superuser="on")
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        user.refresh_from_db()
        self.assertIsNone(user.profession_type)

    def test_user_manager_change_without_profession_is_accepted(self):
        user_manager_group, _created = Group.objects.get_or_create(name=USER_MANAGERS)
        user = UserFactory(username="manager.user", profession_type=None)
        user.groups.add(user_manager_group)

        form = self._change_form(
            user, profession_type="", groups=[user_manager_group.pk]
        )
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        user.refresh_from_db()
        self.assertIsNone(user.profession_type)

    def test_user_manager_removed_from_group_without_profession_is_rejected(self):
        user_manager_group, _created = Group.objects.get_or_create(name=USER_MANAGERS)
        user = UserFactory(username="manager.user", profession_type=None)
        user.groups.add(user_manager_group)

        form = self._change_form(user, profession_type="", groups=[])

        self.assertFalse(form.is_valid())
        self.assertIn("profession_type", form.errors)


class ClinicalIdentityAdminAddViewTests(TestCase):
    """R1: admin add view blocks and allows saves end to end."""

    def setUp(self):
        self.client.force_login(
            SuperUserFactory(
                username="request.superuser",
                password_change_required=False,
                terms_accepted=True,
            )
        )
        self.add_url = reverse("admin:accounts_eqmdcustomuser_add")

    def test_add_without_profession_is_rejected_and_not_saved(self):
        response = self.client.post(self.add_url, add_form_data(profession_type=""))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="novo.clinico").exists())
        form_errors = response.context["adminform"].form.errors
        self.assertIn("profession_type", form_errors)

    def test_add_with_profession_is_saved(self):
        response = self.client.post(
            self.add_url, add_form_data(profession_type=EqmdCustomUser.NURSE)
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="novo.clinico")
        self.assertEqual(user.profession_type, EqmdCustomUser.NURSE)

    def test_add_superuser_without_profession_is_saved(self):
        response = self.client.post(
            self.add_url,
            add_form_data(
                username="novo.superuser", profession_type="", is_superuser="on"
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="novo.superuser")
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.profession_type)

    def test_add_user_manager_member_without_profession_is_saved(self):
        user_manager_group, _created = Group.objects.get_or_create(name=USER_MANAGERS)

        response = self.client.post(
            self.add_url,
            add_form_data(
                username="novo.manager",
                profession_type="",
                groups=[user_manager_group.pk],
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="novo.manager")
        self.assertTrue(user.groups.filter(pk=user_manager_group.pk).exists())
        self.assertIsNone(user.profession_type)


class ClinicalIdentityAdminAddSuperuserGatingTests(TestCase):
    """P1: only a superuser requester may create a superuser in the admin."""

    def setUp(self):
        add_only = UserFactory(
            username="add.only.staff",
            is_staff=True,
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )
        add_only.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="accounts",
                codename__in=("add_eqmdcustomuser", "change_eqmdcustomuser"),
            )
        )
        self.add_only = add_only
        self.client.force_login(add_only)
        self.add_url = reverse("admin:accounts_eqmdcustomuser_add")

    def test_add_only_staff_cannot_create_superuser(self):
        response = self.client.post(
            self.add_url,
            add_form_data(
                username="escalated.user",
                profession_type=EqmdCustomUser.NURSE,
                is_superuser="on",
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="escalated.user")
        self.assertFalse(user.is_superuser)

    def test_add_only_staff_add_form_hides_superuser_flag(self):
        request = RequestFactory().get(self.add_url)
        request.user = self.add_only

        form_class = EqmdCustomUserAdmin(EqmdCustomUser, AdminSite()).get_form(
            request, None
        )

        self.assertNotIn("is_superuser", form_class.base_fields)
        self.assertIn("groups", form_class.base_fields)

    def test_add_only_staff_can_still_create_regular_user(self):
        response = self.client.post(
            self.add_url,
            add_form_data(
                username="novo.enfermeiro", profession_type=EqmdCustomUser.NURSE
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="novo.enfermeiro")
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profession_type, EqmdCustomUser.NURSE)

    def test_add_only_staff_can_still_create_user_manager_member_without_profession(
        self,
    ):
        user_manager_group, _created = Group.objects.get_or_create(name=USER_MANAGERS)

        response = self.client.post(
            self.add_url,
            add_form_data(
                username="novo.manager.staff",
                profession_type="",
                groups=[user_manager_group.pk],
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="novo.manager.staff")
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(pk=user_manager_group.pk).exists())
        self.assertIsNone(user.profession_type)

    def test_save_model_never_persists_superuser_for_non_superuser_requester(self):
        request = RequestFactory().post(self.add_url)
        request.user = self.add_only
        model_admin = EqmdCustomUserAdmin(EqmdCustomUser, AdminSite())
        forged = EqmdCustomUser(username="forged.superuser", is_superuser=True)

        model_admin.save_model(request, forged, form=None, change=False)

        forged.refresh_from_db()
        self.assertFalse(forged.is_superuser)
