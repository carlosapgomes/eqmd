"""S6: the responsible leader team tag page.

The suite is a request matrix, not a button inventory: every negative case is a
direct POST that must be denied with no catalogue, history or transition side
effect, and the rendered page is checked in addition for missing controls.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, cast

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserProfile, UserSpecialty
from apps.accounts.services import team_membership
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, AllowedTagTransition
from apps.patients.services import tag_catalogue
from apps.patients.templatetags.team_tags import led_teams

TEAM_PAGE_LABEL = "Tags da Equipe"


def make_user(username: str, *, is_admin: bool = False):
    """Create an active account with the lifecycle gates cleared."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="team-tag-pass",
        is_staff=is_admin,
        is_superuser=is_admin,
    )


def make_specialty(abbreviation: str) -> MedicalSpecialty:
    """Create one specialty team namespace."""
    return MedicalSpecialty.objects.create(
        name=f"Equipe {abbreviation}", abbreviation=abbreviation
    )


def join_team(
    user: Any,
    specialty: MedicalSpecialty,
    *,
    is_leader: bool = False,
    active: bool = True,
) -> UserSpecialty:
    """Create a retained membership row for one team."""
    return UserSpecialty.objects.create(
        user=user, specialty=specialty, is_active=active, is_leader=is_leader
    )


def make_team_tag(
    actor: Any,
    name: str,
    specialty: MedicalSpecialty,
    *,
    responsible: Any | None = None,
    **overrides: Any,
) -> AllowedTag:
    """Create a restricted team tag without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name,
        created_by=actor,
        updated_by=actor,
        origin=AllowedTag.Origin.CUSTOM,
        visibility=AllowedTag.Visibility.RESTRICTED,
        specialty=specialty,
        responsible_user=responsible if responsible is not None else actor,
        **overrides,
    )


class TeamTagFixture(TestCase):
    """Two leaders of one team, a member, an outsider leader and an admin."""

    cirger: MedicalSpecialty
    cardio: MedicalSpecialty
    leader_a: Any
    leader_b: Any
    member: Any
    outsider_leader: Any
    admin: Any
    own_tag: AllowedTag
    cardio_tag: AllowedTag
    public_tag: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.leader_a = make_user("team-leader-a")
        join_team(cls.leader_a, cls.cirger, is_leader=True)
        cls.leader_b = make_user("team-leader-b")
        join_team(cls.leader_b, cls.cirger, is_leader=True)
        cls.member = make_user("team-member")
        join_team(cls.member, cls.cirger)
        cls.outsider_leader = make_user("team-outsider-leader")
        join_team(cls.outsider_leader, cls.cardio, is_leader=True)
        cls.admin = make_user("team-admin", is_admin=True)

        cls.own_tag = make_team_tag(cls.leader_a, "Reavaliar", cls.cirger)
        cls.cardio_tag = make_team_tag(
            cls.outsider_leader, "Reavaliar", cls.cardio
        )
        cls.public_tag = AllowedTag.objects.create(
            name="Prioridade Global",
            created_by=cls.admin,
            updated_by=cls.admin,
            origin=AllowedTag.Origin.SYSTEM,
            visibility=AllowedTag.Visibility.PUBLIC,
        )

    def page_url(self, specialty: MedicalSpecialty | None = None) -> str:
        return reverse(
            "patients:team_tags",
            kwargs={"specialty_id": (specialty or self.cirger).pk},
        )

    def create_url(self, specialty: MedicalSpecialty | None = None) -> str:
        return reverse(
            "patients:team_tag_create",
            kwargs={"specialty_id": (specialty or self.cirger).pk},
        )

    def edit_url(
        self, tag: AllowedTag, specialty: MedicalSpecialty | None = None
    ) -> str:
        return reverse(
            "patients:team_tag_edit",
            kwargs={
                "specialty_id": (specialty or self.cirger).pk,
                "pk": tag.pk,
            },
        )

    def lifecycle_url(
        self,
        action: str,
        tag: AllowedTag,
        specialty: MedicalSpecialty | None = None,
    ) -> str:
        return reverse(
            f"patients:team_tag_{action}",
            kwargs={
                "specialty_id": (specialty or self.cirger).pk,
                "pk": tag.pk,
            },
        )

    def tag_payload(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": "Nova Tag",
            "description": "Descrição da equipe",
            "color": "#123456",
        }
        payload.update(overrides)
        return payload

    def assert_no_control(self, body: str, tag: AllowedTag, specialty=None) -> None:
        """Assert no management control for the tag was rendered."""
        for url in (
            self.edit_url(tag, specialty),
            self.lifecycle_url("deactivate", tag, specialty),
            self.lifecycle_url("reactivate", tag, specialty),
        ):
            self.assertNotIn(url, body)


class TeamTagPageAccessTests(TeamTagFixture):
    """R1/R2: only a current leader of the addressed team may open the page."""

    def test_leader_opens_team_page(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.get(self.page_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, TEAM_PAGE_LABEL)
        self.assertContains(response, "Equipe CIRGER")
        self.assertContains(response, "CIRGER")
        self.assertContains(response, "Reavaliar")

    def test_member_is_denied_page_and_sees_no_metadata(self) -> None:
        self.client.force_login(self.member)
        response = self.client.get(self.page_url())
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Reavaliar", status_code=403)

    def test_outsider_leader_is_denied_another_team_page(self) -> None:
        self.client.force_login(self.outsider_leader)
        response = self.client.get(self.page_url())
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Reavaliar", status_code=403)

    def test_revoked_leader_is_denied_without_logout(self) -> None:
        self.client.force_login(self.leader_a)
        self.assertEqual(self.client.get(self.page_url()).status_code, 200)

        membership = UserSpecialty.objects.get(
            user=self.leader_a, specialty=self.cirger
        )
        team_membership.revoke_membership(actor=self.admin, membership=membership)

        self.assertEqual(self.client.get(self.page_url()).status_code, 403)
        response = self.client.post(
            self.create_url(), data=self.tag_payload(name="Após revogação")
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            AllowedTag.objects.filter(name="Após revogação").exists()
        )

    def test_anonymous_is_redirected_to_login(self) -> None:
        response = self.client.get(self.page_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_page_shows_only_the_addressed_team_namespace(self) -> None:
        join_team(self.leader_a, self.cardio)
        self.client.force_login(self.leader_a)
        body = self.client.get(self.page_url()).content.decode()
        self.assertIn(self.own_tag.name, body)
        self.assertNotIn("Prioridade Global", body)
        self.assertNotIn(f"/patients/tags/team/{self.cardio.pk}/", body)

    def test_team_url_does_not_change_the_active_specialty(self) -> None:
        join_team(self.leader_a, self.cardio)
        self.client.force_login(self.leader_a)
        profile = UserProfile.objects.get(user=self.leader_a)
        team_membership.set_current_specialty(profile=profile, specialty=self.cardio)

        self.assertEqual(self.client.get(self.page_url()).status_code, 200)

        profile.refresh_from_db()
        self.assertEqual(profile.current_specialty, self.cardio)


class TeamTagCreateTests(TeamTagFixture):
    """R1: leaders create only custom restricted tags in their own team."""

    def test_leader_creates_custom_restricted_tag(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.create_url(),
            data=self.tag_payload(name="Observação CIRGER"),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Observação CIRGER")

        tag = AllowedTag.objects.get(name="Observação CIRGER")
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.cirger.pk)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertEqual(tag.created_by_id, self.leader_a.pk)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)

    def test_create_form_is_rendered(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.get(self.create_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova tag da equipe")
        self.assertContains(response, "personalizada e restrita")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_forged_administrative_fields_are_server_controlled(self) -> None:
        self.client.force_login(self.leader_a)
        payload = self.tag_payload(
            name="Campos Forjados",
            origin=AllowedTag.Origin.SYSTEM,
            visibility=AllowedTag.Visibility.PUBLIC,
            specialty=str(self.cardio.pk),
            responsible_user=str(self.leader_b.pk),
            is_active="",
            is_deleted="on",
        )
        response = self.client.post(self.create_url(), data=payload)
        self.assertEqual(response.status_code, 302)

        tag = AllowedTag.objects.get(name="Campos Forjados")
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.cirger.pk)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)
        self.assertFalse(
            AllowedTag.objects.filter(name="Campos Forjados", specialty=self.cardio).exists()
        )

    def test_cross_team_creation_is_denied(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.create_url(self.cardio),
            data=self.tag_payload(name="Invasão CARDIO"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AllowedTag.objects.filter(name="Invasão CARDIO").exists())

    def test_member_cannot_create(self) -> None:
        self.client.force_login(self.member)
        response = self.client.post(
            self.create_url(), data=self.tag_payload(name="Tag do Membro")
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AllowedTag.objects.filter(name="Tag do Membro").exists())

    def test_duplicate_name_is_rejected_across_lifecycle_states(self) -> None:
        make_team_tag(
            self.leader_a,
            "Arquivada CIRGER",
            self.cirger,
            is_active=False,
            is_deleted=True,
        )
        before = AllowedTag.all_objects.count()

        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.create_url(), data=self.tag_payload(name="  arquivada cirger  ")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "já está reservado", status_code=200)
        self.assertEqual(AllowedTag.all_objects.count(), before)

    def test_same_name_is_allowed_in_another_team_namespace(self) -> None:
        make_team_tag(self.leader_a, "Exclusiva CIRGER", self.cirger)
        join_team(self.leader_a, self.cardio, is_leader=True)

        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.create_url(self.cardio),
            data=self.tag_payload(name="Exclusiva CIRGER"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AllowedTag.objects.filter(
                name="Exclusiva CIRGER", specialty=self.cardio
            ).exists()
        )

        duplicate = self.client.post(
            self.create_url(self.cardio),
            data=self.tag_payload(name=" exclusiva cirger "),
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertContains(duplicate, "já está reservado", status_code=200)

    def test_empty_name_is_rejected_with_feedback(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(self.create_url(), data=self.tag_payload(name="   "))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe o nome da tag")
        self.assertEqual(AllowedTag.objects.filter(name="").count(), 0)


class TeamTagManagementTests(TeamTagFixture):
    """R2/R3: management follows responsibility; administrative fields stay fixed."""

    def test_responsible_leader_edits_allowed_fields(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.edit_url(self.own_tag),
            data=self.tag_payload(name="Reavaliar Agora", description="Nova"),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reavaliar Agora")

        self.own_tag.refresh_from_db()
        self.assertEqual(self.own_tag.name, "Reavaliar Agora")
        self.assertEqual(self.own_tag.description, "Nova")

    def test_edit_form_shows_the_current_values(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.get(self.edit_url(self.own_tag))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar &quot;Reavaliar&quot;")
        self.assertContains(response, "Reavaliar")
        self.assertContains(response, self.own_tag.color)

    def test_edit_ignores_forged_administrative_fields(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.edit_url(self.own_tag),
            data=self.tag_payload(
                name="Reavaliar Editada",
                origin=AllowedTag.Origin.SYSTEM,
                visibility=AllowedTag.Visibility.PUBLIC,
                specialty=str(self.cardio.pk),
                responsible_user=str(self.leader_b.pk),
                is_active="",
                is_deleted="on",
            ),
        )
        self.assertEqual(response.status_code, 302)

        tag = AllowedTag.all_objects.get(pk=self.own_tag.pk)
        self.assertEqual(tag.name, "Reavaliar Editada")
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.cirger.pk)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)

    def test_other_leader_cannot_edit_or_deactivate(self) -> None:
        self.client.force_login(self.leader_b)
        self.assertEqual(self.client.get(self.edit_url(self.own_tag)).status_code, 403)

        response = self.client.post(
            self.edit_url(self.own_tag), data=self.tag_payload(name="Sequestrada")
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(self.lifecycle_url("deactivate", self.own_tag))
        self.assertEqual(response.status_code, 403)

        self.own_tag.refresh_from_db()
        self.assertEqual(self.own_tag.name, "Reavaliar")
        self.assertTrue(self.own_tag.is_active)
        self.assertFalse(AllowedTagTransition.objects.filter(tag=self.own_tag).exists())

    def test_transfer_moves_rights_to_the_new_responsible_leader(self) -> None:
        self.client.force_login(self.leader_a)
        self.assertEqual(
            self.client.post(self.lifecycle_url("deactivate", self.own_tag)).status_code,
            302,
        )
        self.own_tag.refresh_from_db()
        self.assertFalse(self.own_tag.is_active)
        self.assertEqual(
            self.client.post(self.lifecycle_url("reactivate", self.own_tag)).status_code,
            302,
        )

        tag_catalogue.transfer_responsibility(
            actor=self.admin, tag=self.own_tag, recipient=self.leader_b
        )

        self.client.force_login(self.leader_b)
        response = self.client.post(
            self.edit_url(self.own_tag), data=self.tag_payload(name="Do Novo Líder")
        )
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.edit_url(self.own_tag), data=self.tag_payload(name="Do Antigo Líder")
        )
        self.assertEqual(response.status_code, 403)

        tag = AllowedTag.all_objects.get(pk=self.own_tag.pk)
        self.assertEqual(tag.name, "Do Novo Líder")
        self.assertEqual(tag.created_by_id, self.leader_a.pk)
        self.assertEqual(tag.responsible_user_id, self.leader_b.pk)

    def test_cross_team_tag_identity_is_not_reachable(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.edit_url(self.cardio_tag), data=self.tag_payload(name="Invasão")
        )
        self.assertEqual(response.status_code, 404)

        self.cardio_tag.refresh_from_db()
        self.assertEqual(self.cardio_tag.name, "Reavaliar")

    def test_public_tag_is_not_manageable_from_the_team_page(self) -> None:
        self.client.force_login(self.leader_a)
        response = self.client.post(
            self.edit_url(self.public_tag), data=self.tag_payload(name="Global")
        )
        self.assertEqual(response.status_code, 404)
        self.public_tag.refresh_from_db()
        self.assertEqual(self.public_tag.name, "Prioridade Global")

    def test_archived_tag_cannot_be_managed_by_a_leader(self) -> None:
        tag_catalogue.archive_tag(actor=self.admin, tag=self.own_tag)

        self.client.force_login(self.leader_a)
        self.assertEqual(self.client.get(self.edit_url(self.own_tag)).status_code, 404)
        self.assertEqual(
            self.client.post(self.lifecycle_url("deactivate", self.own_tag)).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(self.lifecycle_url("reactivate", self.own_tag)).status_code,
            404,
        )

        tag = AllowedTag.all_objects.get(pk=self.own_tag.pk)
        self.assertTrue(tag.is_deleted)
        self.assertFalse(tag.is_active)

        page = self.client.get(self.page_url())
        self.assertContains(page, "Arquivada")
        self.assert_no_control(page.content.decode(), self.own_tag)

    def test_leader_deactivates_and_reactivates_own_tag(self) -> None:
        self.client.force_login(self.leader_a)

        response = self.client.post(
            self.lifecycle_url("deactivate", self.own_tag), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inativa")

        tag = AllowedTag.all_objects.get(pk=self.own_tag.pk)
        self.assertFalse(tag.is_active)
        self.assertFalse(tag.is_deleted)
        transition = AllowedTagTransition.objects.get(tag=tag)
        self.assertEqual(transition.action, AllowedTagTransition.Action.DEACTIVATE)
        self.assertEqual(transition.performed_by, self.leader_a)

        response = self.client.post(
            self.lifecycle_url("reactivate", tag), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ativa")

        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertEqual(
            AllowedTagTransition.objects.filter(tag=tag).count(), 2
        )

    def test_lifecycle_actions_reject_get(self) -> None:
        self.client.force_login(self.leader_a)
        self.assertEqual(
            self.client.get(self.lifecycle_url("deactivate", self.own_tag)).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(self.lifecycle_url("reactivate", self.own_tag)).status_code,
            405,
        )

    def test_administrative_actions_are_absent(self) -> None:
        self.client.force_login(self.leader_a)
        for action in ("archive", "restore", "transfer", "delete"):
            with self.subTest(action=action):
                response = self.client.post(
                    f"/patients/tags/team/{self.cirger.pk}/{self.own_tag.pk}/{action}/"
                )
                self.assertEqual(response.status_code, 404)

        tag = AllowedTag.all_objects.get(pk=self.own_tag.pk)
        self.assertFalse(tag.is_deleted)
        self.assertTrue(tag.is_active)
        self.assertEqual(tag.responsible_user_id, self.leader_a.pk)

        body = self.client.get(self.page_url()).content.decode()
        for label in ("Arquivar", "Restaurar", "Transferir", "Excluir"):
            self.assertNotIn(label, body)

    def test_page_hides_controls_for_a_tag_without_responsibility(self) -> None:
        self.client.force_login(self.leader_b)
        body = self.client.get(self.page_url()).content.decode()
        self.assertIn("Reavaliar", body)
        self.assert_no_control(body, self.own_tag)

        self.client.force_login(self.leader_a)
        body = self.client.get(self.page_url()).content.decode()
        self.assertIn(self.edit_url(self.own_tag), body)
        self.assertIn(self.lifecycle_url("deactivate", self.own_tag), body)


class TeamTagNavigationTests(TeamTagFixture):
    """R4: one permission-checked navigation entry, leaders only."""

    def dashboard_body(self) -> str:
        return self.client.get(reverse("apps.core:dashboard")).content.decode()

    def test_leader_sees_the_navigation_entry(self) -> None:
        self.client.force_login(self.leader_a)
        body = self.dashboard_body()
        self.assertIn(self.page_url(), body)
        self.assertIn(TEAM_PAGE_LABEL, body)

    def test_member_has_no_navigation_entry(self) -> None:
        self.client.force_login(self.member)
        self.assertNotIn(self.page_url(), self.dashboard_body())

    def test_outsider_leader_only_sees_own_team_entry(self) -> None:
        self.client.force_login(self.outsider_leader)
        body = self.dashboard_body()
        self.assertIn(self.page_url(self.cardio), body)
        self.assertNotIn(self.page_url(self.cirger), body)

    def test_revoked_leader_loses_the_navigation_entry(self) -> None:
        self.client.force_login(self.leader_a)
        self.assertIn(self.page_url(), self.dashboard_body())

        membership = UserSpecialty.objects.get(
            user=self.leader_a, specialty=self.cirger
        )
        team_membership.revoke_membership(actor=self.admin, membership=membership)

        self.assertNotIn(self.page_url(), self.dashboard_body())


class LedTeamsFilterTests(TeamTagFixture):
    """R4: the navigation filter exposes current leadership and nothing else."""

    def test_filter_returns_only_led_teams(self) -> None:
        self.assertEqual(
            [team.pk for team in led_teams(self.leader_a)], [self.cirger.pk]
        )
        self.assertEqual(
            [team.pk for team in led_teams(self.outsider_leader)], [self.cardio.pk]
        )
        self.assertEqual(led_teams(self.member), [])
        self.assertEqual(led_teams(self.admin), [])

    def test_filter_drops_revoked_leadership_immediately(self) -> None:
        membership = UserSpecialty.objects.get(
            user=self.leader_b, specialty=self.cirger
        )
        team_membership.revoke_membership(actor=self.admin, membership=membership)
        self.assertEqual(led_teams(self.leader_b), [])

    def test_filter_drops_an_inactive_team(self) -> None:
        self.cirger.is_active = False
        self.cirger.save()
        self.assertEqual(led_teams(self.leader_a), [])

    def test_filter_rejects_anonymous_and_missing_users(self) -> None:
        self.assertEqual(led_teams(None), [])
        self.assertEqual(led_teams(cast(Any, AnonymousUser())), [])


class MembershipRevocationRaceTests(TransactionTestCase):
    """P1: leader writes revalidate authority from the locked membership row.

    A concurrent revocation commits while the write waits for the membership
    lock; the write must then be denied from the locked row, not from the
    unlocked leadership read that made the revocation race reachable.
    """

    def test_revocation_under_the_lock_denies_the_edit(self) -> None:
        outcomes, waited, tag = self._run_revocation_race(
            lambda leader, tag: tag_catalogue.edit_tag(
                actor=leader, tag=tag, name="Renomeada na Corrida"
            )
        )

        self.assertTrue(waited, f"edit never waited on the membership lock: {outcomes}")
        self.assertEqual(outcomes, ["denied"])
        tag.refresh_from_db()
        self.assertEqual(tag.name, "Corrida Revogação")

    def test_revocation_under_the_lock_denies_the_deactivation(self) -> None:
        outcomes, waited, tag = self._run_revocation_race(
            lambda leader, tag: tag_catalogue.deactivate_tag(actor=leader, tag=tag)
        )

        self.assertTrue(
            waited, f"deactivation never waited on the membership lock: {outcomes}"
        )
        self.assertEqual(outcomes, ["denied"])
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertFalse(AllowedTagTransition.objects.filter(tag=tag).exists())

    def _run_revocation_race(
        self, write: Callable[[Any, AllowedTag], None]
    ) -> tuple[list[str], bool, AllowedTag]:
        """Revoke the leader's membership under a lock while the write runs."""
        administrator = make_user("race-admin", is_admin=True)
        leader = make_user("race-leader")
        team = make_specialty("RACET")
        membership = join_team(leader, team, is_leader=True)
        tag = make_team_tag(leader, "Corrida Revogação", team)
        locked = threading.Event()
        release = threading.Event()
        outcomes: list[str] = []

        def revoker() -> None:
            try:
                with transaction.atomic():
                    UserSpecialty.objects.select_for_update().get(pk=membership.pk)
                    locked.set()
                    release.wait(timeout=30)
                    team_membership.revoke_membership(
                        actor=administrator, membership=membership
                    )
            finally:
                connection.close()

        def writer() -> None:
            try:
                write(leader, tag)
                outcomes.append("written")
            except PermissionDenied:
                outcomes.append("denied")
            # A thread failure must surface in the assertion message above.
            except Exception as error:  # noqa: BLE001
                outcomes.append(f"error:{type(error).__name__}:{error}")
            finally:
                connection.close()

        revoke_thread = threading.Thread(target=revoker)
        revoke_thread.start()
        self.assertTrue(locked.wait(timeout=30), "revoker never took the row lock")
        write_thread = threading.Thread(target=writer)
        write_thread.start()
        waited = self._wait_until_blocked_on_lock(write_thread)
        release.set()
        revoke_thread.join(timeout=30)
        write_thread.join(timeout=30)

        self.assertFalse(revoke_thread.is_alive())
        self.assertFalse(write_thread.is_alive())
        return outcomes, waited, tag

    def _wait_until_blocked_on_lock(self, thread: threading.Thread) -> bool:
        """Return whether the write waits on a row lock before finishing."""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not thread.is_alive():
                return False
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_locks WHERE NOT granted")
                if cursor.fetchone()[0]:
                    return True
            time.sleep(0.02)
        return False
