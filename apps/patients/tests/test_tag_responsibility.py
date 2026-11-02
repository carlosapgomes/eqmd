"""S3 responsibility transfer and responsible-leader policy boundaries."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.services import team_membership
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, AllowedTagTransition
from apps.patients.services import tag_catalogue, tag_policy

User = get_user_model()


def make_user(username: str, *, is_staff: bool = False) -> User:
    """Create an active clinical or staff account."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="responsibility-pass",
        is_staff=is_staff,
    )


def make_admin(username: str = "responsibility-admin") -> User:
    """Create an authorized catalogue administrator."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="responsibility-pass",
        is_staff=True,
        is_superuser=True,
    )


def make_specialty(abbreviation: str) -> MedicalSpecialty:
    """Create a specialty team namespace."""
    return MedicalSpecialty.objects.create(
        name=f"Especialidade {abbreviation}", abbreviation=abbreviation
    )


def make_leader(
    username: str, specialty: MedicalSpecialty, *, is_leader: bool = True
) -> User:
    """Create a user with an active membership in a team."""
    user = make_user(username)
    UserSpecialty.objects.create(
        user=user, specialty=specialty, is_active=True, is_leader=is_leader
    )
    return user


def make_tag(actor: User, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def admin_payload(**overrides: Any) -> dict[str, Any]:
    """Build a catalogue admin change payload with editable fields only."""
    payload: dict[str, Any] = {
        "name": "Reavaliar",
        "description": "Catalogue entry",
        "color": "#123456",
        "origin": AllowedTag.Origin.CUSTOM,
        "visibility": AllowedTag.Visibility.RESTRICTED,
        "specialty": "",
        "responsible_user": "",
        "_save": "Salvar",
    }
    payload.update(overrides)
    return payload


class TransferResponsibilityServiceTests(TestCase):
    """R3: administrator transfers to a current same-team leader only."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.cirger = make_specialty("TRFCIR")
        cls.cardio = make_specialty("TRFCAR")
        cls.leader_a = make_leader("leader-a", cls.cirger)
        cls.leader_b = make_leader("leader-b", cls.cirger)
        cls.member = make_leader("member-cirger", cls.cirger, is_leader=False)
        cls.other_leader = make_leader("leader-cardio", cls.cardio)

    def _tag(self, **overrides: Any) -> AllowedTag:
        return make_tag(
            self.leader_a,
            "Reavaliar",
            specialty=self.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            responsible_user=self.leader_a,
            **overrides,
        )

    def test_admin_transfer_preserves_creator_and_changes_authority(self) -> None:
        tag = self._tag()
        tag_pk = tag.pk
        rows_before = AllowedTag.all_objects.count()

        tag_catalogue.transfer_responsibility(
            actor=self.admin, tag=tag, recipient=self.leader_b
        )

        tag.refresh_from_db()
        self.assertEqual(AllowedTag.all_objects.count(), rows_before)
        self.assertEqual(tag.pk, tag_pk)
        self.assertEqual(tag.responsible_user_id, self.leader_b.pk)
        self.assertEqual(tag.created_by_id, self.leader_a.pk)
        self.assertFalse(tag_policy.can_manage_tag(self.leader_a, tag))
        self.assertTrue(tag_policy.can_manage_tag(self.leader_b, tag))

    def test_transfer_history_records_actor_time_and_endpoints(self) -> None:
        tag = self._tag()
        tag_catalogue.transfer_responsibility(
            actor=self.admin, tag=tag, recipient=self.leader_b
        )
        transition = tag.transitions.get(
            action=AllowedTagTransition.Action.TRANSFER
        )
        self.assertEqual(transition.performed_by_id, self.admin.pk)
        self.assertIsNotNone(transition.performed_at)
        self.assertEqual(transition.previous_responsible_id, self.leader_a.pk)
        self.assertEqual(transition.new_responsible_id, self.leader_b.pk)
        self.assertEqual(transition.reason, "")

    def test_non_leader_member_recipient_rejected_without_side_effects(self) -> None:
        tag = self._tag()
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.member
            )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertFalse(
            AllowedTagTransition.objects.filter(
                tag_id=tag.pk, action=AllowedTagTransition.Action.TRANSFER
            ).exists()
        )

    def test_other_team_leader_recipient_rejected(self) -> None:
        tag = self._tag()
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.other_leader
            )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_revoked_leader_recipient_rejected(self) -> None:
        membership = UserSpecialty.objects.get(
            user=self.leader_b, specialty=self.cirger
        )
        team_membership.revoke_leadership(actor=self.admin, membership=membership)
        tag = self._tag()
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.leader_b
            )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_inactive_membership_recipient_rejected(self) -> None:
        membership = UserSpecialty.objects.get(
            user=self.leader_b, specialty=self.cirger
        )
        team_membership.revoke_membership(actor=self.admin, membership=membership)
        tag = self._tag()
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.leader_b
            )

    def test_non_administrator_cannot_transfer(self) -> None:
        tag = self._tag()
        for actor in (self.leader_a, self.leader_b, self.member):
            with self.subTest(
                actor=actor.username
            ), self.assertRaises(PermissionDenied):
                tag_catalogue.transfer_responsibility(
                    actor=actor, tag=tag, recipient=self.leader_b
                )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_public_or_global_tag_cannot_be_transferred(self) -> None:
        public = make_tag(self.leader_a, "Publica", specialty=self.cirger)
        global_tag = make_tag(self.admin, "Global")
        for tag in (public, global_tag):
            with self.subTest(
                tag=tag.name
            ), self.assertRaises(ValidationError):
                tag_catalogue.transfer_responsibility(
                    actor=self.admin, tag=tag, recipient=self.leader_b
                )

    def test_archived_tag_cannot_be_transferred(self) -> None:
        tag = self._tag()
        tag_catalogue.archive_tag(actor=self.admin, tag=tag)
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.leader_b
            )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_transfer_to_current_responsible_rejected(self) -> None:
        tag = self._tag()
        with self.assertRaises(ValidationError):
            tag_catalogue.transfer_responsibility(
                actor=self.admin, tag=tag, recipient=self.leader_a
            )
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)


class ResponsibleLeaderPolicyTests(TestCase):
    """R4: responsible leader may only edit/deactivate/reactivate own tag."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.specialty = make_specialty("POLCIR")
        cls.other_specialty = make_specialty("POLCAR")
        cls.leader_a = make_leader("policy-a", cls.specialty)
        cls.leader_b = make_leader("policy-b", cls.specialty)
        cls.other_leader = make_leader("policy-cardio", cls.other_specialty)
        cls.plain = make_user("policy-plain")

    def _tag(self, **overrides: Any) -> AllowedTag:
        values: dict[str, Any] = {
            "specialty": self.specialty,
            "visibility": AllowedTag.Visibility.RESTRICTED,
            "origin": AllowedTag.Origin.CUSTOM,
            "responsible_user": self.leader_a,
        }
        values.update(overrides)
        name = values.pop("name", "Privada")
        return make_tag(self.leader_a, name, **values)

    def test_responsible_leader_manages_own_custom_restricted_tag(self) -> None:
        tag = self._tag()
        self.assertTrue(tag_policy.can_manage_tag(self.leader_a, tag))

        tag_catalogue.deactivate_tag(actor=self.leader_a, tag=tag)
        tag.refresh_from_db()
        self.assertFalse(tag.is_active)
        self.assertEqual(tag.deactivated_by_id, self.leader_a.pk)

        tag_catalogue.reactivate_tag(actor=self.leader_a, tag=tag)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)

        tag_catalogue.edit_tag(
            actor=self.leader_a,
            tag=tag,
            name="Renomeada",
            description="Pela liderança",
        )
        tag.refresh_from_db()
        self.assertEqual(tag.name, "Renomeada")
        self.assertEqual(tag.description, "Pela liderança")
        self.assertEqual(tag.created_by_id, self.leader_a.pk)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.specialty.pk)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)

    def test_responsible_leader_cannot_archive_or_transfer(self) -> None:
        tag = self._tag()
        with self.assertRaises(PermissionDenied):
            tag_catalogue.archive_tag(actor=self.leader_a, tag=tag)
        with self.assertRaises(PermissionDenied):
            tag_catalogue.transfer_responsibility(
                actor=self.leader_a, tag=tag, recipient=self.leader_b
            )
        tag.refresh_from_db()
        self.assertFalse(tag.is_deleted)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_responsible_leader_cannot_change_classification_or_namespace(self) -> None:
        tag = self._tag()
        with self.assertRaises(PermissionDenied):
            tag_catalogue.update_tag(
                actor=self.leader_a,
                tag=tag,
                visibility=AllowedTag.Visibility.PUBLIC,
            )
        with self.assertRaises(PermissionDenied):
            tag_catalogue.update_tag(
                actor=self.leader_a, tag=tag, specialty=self.other_specialty
            )
        tag.refresh_from_db()
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.specialty.pk)

    def test_other_leader_and_plain_user_denied(self) -> None:
        tag = self._tag()
        for actor in (self.leader_b, self.other_leader, self.plain):
            with self.subTest(actor=actor.username):
                self.assertFalse(tag_policy.can_manage_tag(actor, tag))
                with self.assertRaises(PermissionDenied):
                    tag_catalogue.deactivate_tag(actor=actor, tag=tag)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)

    def test_revoked_membership_denies_immediately_and_keeps_reference(self) -> None:
        tag = self._tag()
        membership = UserSpecialty.objects.get(
            user=self.leader_a, specialty=self.specialty
        )
        team_membership.revoke_membership(actor=self.admin, membership=membership)

        self.assertFalse(tag_policy.can_manage_tag(self.leader_a, tag))
        with self.assertRaises(PermissionDenied):
            tag_catalogue.deactivate_tag(actor=self.leader_a, tag=tag)

        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

    def test_former_responsible_denied_after_transfer(self) -> None:
        tag = self._tag()
        tag_catalogue.transfer_responsibility(
            actor=self.admin, tag=tag, recipient=self.leader_b
        )
        with self.assertRaises(PermissionDenied):
            tag_catalogue.deactivate_tag(actor=self.leader_a, tag=tag)
        with self.assertRaises(PermissionDenied):
            tag_catalogue.edit_tag(actor=self.leader_a, tag=tag, name="Autoria")
        tag.refresh_from_db()
        self.assertEqual(tag.name, "Privada")
        self.assertEqual(tag.created_by_id, self.leader_a.pk)

    def test_public_global_and_system_tags_are_not_manager_manageable(self) -> None:
        public = make_tag(
            self.leader_a, "Publica", specialty=self.specialty,
            responsible_user=self.leader_a,
        )
        global_tag = make_tag(self.admin, "Global")
        system = self._tag(
            name="Sistema", origin=AllowedTag.Origin.SYSTEM
        )
        for tag in (public, global_tag, system):
            with self.subTest(tag=tag.name):
                self.assertFalse(tag_policy.can_manage_tag(self.leader_a, tag))

    def test_responsible_requires_restricted_namespaced_tag(self) -> None:
        public = AllowedTag(
            name="Invalida",
            responsible_user=self.leader_a,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            public.full_clean()

        global_tag = AllowedTag(
            name="Invalida global",
            visibility=AllowedTag.Visibility.RESTRICTED,
            responsible_user=self.leader_a,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            global_tag.full_clean()

    def test_can_manage_requires_authenticated_active_user(self) -> None:
        tag = self._tag()
        self.assertFalse(tag_policy.can_manage_tag(None, tag))
        self.leader_a.is_active = False
        self.assertFalse(tag_policy.can_manage_tag(self.leader_a, tag))


class AdminResponsibilityRouteTests(TestCase):
    """R3/R4: admin responsibility edits use the transfer workflow."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.specialty = make_specialty("ADMCIR")
        cls.leader_a = make_leader("route-a", cls.specialty)
        cls.leader_b = make_leader("route-b", cls.specialty)
        cls.member = make_leader("route-member", cls.specialty, is_leader=False)

    def setUp(self) -> None:
        self.client = Client()
        self.client.force_login(self.admin)

    def _tag(self) -> AllowedTag:
        return make_tag(
            self.leader_a,
            "Reavaliar",
            specialty=self.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
            responsible_user=self.leader_a,
        )

    def _payload(self, tag: AllowedTag, responsible: Any) -> dict[str, Any]:
        return admin_payload(
            name=tag.name,
            specialty=str(self.specialty.pk),
            responsible_user=str(responsible.pk) if responsible else "",
        )

    def test_admin_change_form_transfers_responsibility(self) -> None:
        tag = self._tag()
        response = self.client.post(
            reverse("admin:patients_allowedtag_change", args=[tag.pk]),
            self._payload(tag, self.leader_b),
        )
        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_b.pk)
        self.assertEqual(tag.created_by_id, self.leader_a.pk)
        transition = tag.transitions.get(
            action=AllowedTagTransition.Action.TRANSFER
        )
        self.assertEqual(transition.performed_by_id, self.admin.pk)
        self.assertEqual(transition.previous_responsible_id, self.leader_a.pk)
        self.assertEqual(transition.new_responsible_id, self.leader_b.pk)

    def test_admin_change_form_rejects_ineligible_recipient(self) -> None:
        tag = self._tag()
        transition_count = AllowedTagTransition.objects.count()
        response = self.client.post(
            reverse("admin:patients_allowedtag_change", args=[tag.pk]),
            self._payload(tag, self.member),
        )
        self.assertEqual(response.status_code, 200)
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertEqual(AllowedTagTransition.objects.count(), transition_count)

    def test_admin_form_limits_responsibility_to_current_leaders(self) -> None:
        tag = self._tag()
        response = self.client.get(
            reverse("admin:patients_allowedtag_change", args=[tag.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "route-b")
        self.assertNotContains(response, "route-member")

    def test_admin_add_cannot_forge_initial_responsibility(self) -> None:
        response = self.client.post(
            reverse("admin:patients_allowedtag_add"),
            admin_payload(
                name="Nova",
                specialty=str(self.specialty.pk),
                responsible_user=str(self.leader_b.pk),
            ),
        )
        self.assertEqual(response.status_code, 302)
        tag = AllowedTag.all_objects.get(name="Nova")
        self.assertIsNone(tag.responsible_user_id)

    def test_ordinary_staff_cannot_change_responsibility(self) -> None:
        staff = create_navigation_user(
            username="route-staff",
            email="route-staff@example.com",
            password="responsibility-pass",
            is_staff=True,
        )
        staff.user_permissions.add(
            Permission.objects.get(
                codename="view_allowedtag", content_type__app_label="patients"
            )
        )
        tag = self._tag()
        client = Client()
        client.force_login(staff)
        response = client.post(
            reverse("admin:patients_allowedtag_change", args=[tag.pk]),
            self._payload(tag, self.leader_b),
        )
        self.assertEqual(response.status_code, 403)
        tag.refresh_from_db()
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
