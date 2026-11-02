"""S8 R1-R4: retained per-specialty tag preferences and explicit save.

The preference belongs to the retained ``UserSpecialty`` membership, so absence
("not configured yet") is different from an explicitly saved empty selection.
Saving is an explicit, CSRF-protected mutation limited to the user's currently
valid specialty context.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.messages import get_messages
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.models import (
    MedicalSpecialty,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.services import tag_preferences, team_membership
from apps.accounts.tests.factories import SuperUserFactory
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag

BASE_MIGRATION = ("accounts", "0007_medicalspecialty_principal_tag")
HEAD_MIGRATION = ("accounts", "0008_userspecialty_tag_preference")
SAVE_URL_NAME = "apps.accounts:tag_preference_save"
PREFERENCES_URL_NAME = "apps.accounts:tag_preferences"


def make_user(username: str, **overrides: Any) -> Any:
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="tag-preference-pass",
        **overrides,
    )


def make_specialty(name: str, abbreviation: str) -> MedicalSpecialty:
    return MedicalSpecialty.objects.create(name=name, abbreviation=abbreviation)


def join_team(user: Any, specialty: MedicalSpecialty) -> UserSpecialty:
    return UserSpecialty.objects.create(user=user, specialty=specialty, is_active=True)


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def set_current(user: Any, specialty: MedicalSpecialty) -> None:
    profile = user.profile
    profile.current_specialty = specialty
    profile.save(update_fields=["current_specialty"])


def save_via_client(client: Client, specialty: MedicalSpecialty, **payload: Any):
    data: dict[str, Any] = {
        "specialty_id": str(specialty.pk),
        "tag_mode": payload.pop("tag_mode", "any"),
    }
    data.update(payload)
    return client.post(reverse(SAVE_URL_NAME), data)


class TagPreferenceModelTests(TestCase):
    """R1: one retained preference per membership, absent vs saved-empty."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = SuperUserFactory()
        cls.user = make_user("preference-model-user")
        cls.cirger = make_specialty("Cirurgia Geral", "MCIRGER")
        cls.cardio = make_specialty("Cardiologia", "MCARDIO")
        cls.cirger_membership = join_team(cls.user, cls.cirger)
        cls.cardio_membership = join_team(cls.user, cls.cardio)
        cls.cirger_tag = make_tag(cls.owner, "Modelo CIRGER")
        cls.cardio_tag = make_tag(cls.owner, "Modelo CARDIO")

    def test_absent_preference_is_distinct_from_saved_empty(self) -> None:
        self.assertIsNone(getattr(self.cirger_membership, "tag_preference", None))

        preference = UserSpecialtyTagPreference.objects.create(membership=self.cirger_membership)

        self.assertEqual(preference.mode, UserSpecialtyTagPreference.Mode.ANY)
        self.assertEqual(preference.tags.count(), 0)
        self.assertIsNotNone(getattr(self.cirger_membership, "tag_preference", None))

    def test_one_preference_per_membership_is_enforced(self) -> None:
        UserSpecialtyTagPreference.objects.create(membership=self.cirger_membership)

        with self.assertRaises(IntegrityError), transaction.atomic():
            UserSpecialtyTagPreference.objects.create(membership=self.cirger_membership)

    def test_two_teams_keep_independent_preferences(self) -> None:
        cirger_preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cirger_membership, mode=UserSpecialtyTagPreference.Mode.ALL
        )
        cirger_preference.tags.set([self.cirger_tag])
        cardio_preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cardio_membership
        )
        cardio_preference.tags.set([self.cardio_tag])

        self.assertEqual(
            list(cirger_preference.tags.values_list("pk", flat=True)),
            [self.cirger_tag.pk],
        )
        self.assertEqual(cirger_preference.mode, "all")
        self.assertEqual(
            list(cardio_preference.tags.values_list("pk", flat=True)),
            [self.cardio_tag.pk],
        )
        self.assertEqual(cardio_preference.mode, "any")

    def test_principal_tag_is_optional_in_saved_settings(self) -> None:
        self.assertIsNone(self.cirger.principal_tag)

        preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cirger_membership
        )

        self.assertEqual(preference.tags.count(), 0)

    def test_mode_check_constraint_rejects_unknown_mode(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserSpecialtyTagPreference.objects.create(
                membership=self.cirger_membership, mode="xor"
            )


class TagPreferenceMigrationTests(TransactionTestCase):
    """R1: additive migration creates the preference table without backfill."""

    def test_additive_migration_keeps_memberships_and_adds_no_preference(
        self,
    ) -> None:
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([BASE_MIGRATION])
            executor.loader.build_graph()
            old_apps = executor.loader.project_state([BASE_MIGRATION]).apps
            old_user = old_apps.get_model("accounts", "EqmdCustomUser")
            old_specialty = old_apps.get_model("accounts", "MedicalSpecialty")
            old_membership = old_apps.get_model("accounts", "UserSpecialty")
            member = old_user.objects.create(
                username="preference-migration-member",
                email="preference-migration-member@example.com",
            )
            specialty = old_specialty.objects.create(
                name="Migracao Preferencia", abbreviation="MIGPREF"
            )
            membership = old_membership.objects.create(
                user=member, specialty=specialty
            )
            membership_pk = membership.pk

            executor = MigrationExecutor(connection)
            executor.migrate([HEAD_MIGRATION])
            executor.loader.build_graph()

            migrated = UserSpecialty.objects.get(pk=membership_pk)
            self.assertTrue(migrated.is_active)
            self.assertFalse(
                UserSpecialtyTagPreference.objects.filter(
                    membership_id=membership_pk
                ).exists()
            )

            UserSpecialtyTagPreference.objects.create(
                membership=migrated, mode=UserSpecialtyTagPreference.Mode.ALL
            )
            self.assertEqual(
                UserSpecialtyTagPreference.objects.get(
                    membership_id=membership_pk
                ).mode,
                "all",
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()
            executor.migrate(executor.loader.graph.leaf_nodes())


class TagPreferenceSaveTests(TestCase):
    """R3: explicit CSRF-protected save limited to the active specialty."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = SuperUserFactory()
        cls.user = make_user("preference-save-user")
        cls.other = make_user("preference-save-other")
        cls.cirger = make_specialty("Cirurgia Geral", "SCIRGER")
        cls.cardio = make_specialty("Cardiologia", "SCARDIO")
        cls.cardio_only = make_specialty("Pediatria", "SPED")
        cls.cirger_membership = join_team(cls.user, cls.cirger)
        cls.cardio_membership = join_team(cls.user, cls.cardio)
        join_team(cls.other, cls.cardio_only)
        cls.active_tag = make_tag(cls.owner, "Salvar Ativa")
        cls.second_tag = make_tag(cls.owner, "Salvar Segunda")
        cls.inactive_tag = make_tag(cls.owner, "Salvar Inativa", is_active=False)
        cls.archived_tag = make_tag(
            cls.owner, "Salvar Arquivada", is_active=False, is_deleted=True
        )
        cls.foreign_tag = make_tag(
            cls.owner,
            "Salvar Restrita Alheia",
            specialty=cls.cardio_only,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def setUp(self) -> None:
        set_current(self.user, self.cirger)
        self.client.force_login(self.user)

    def test_explicit_save_persists_tags_and_mode_together(self) -> None:
        response = save_via_client(
            self.client,
            self.cirger,
            tags=[self.active_tag.pk, self.second_tag.pk],
            tag_mode="all",
        )

        self.assertEqual(response.status_code, 302)
        preference = UserSpecialtyTagPreference.objects.get(
            membership=self.cirger_membership
        )
        self.assertEqual(preference.mode, "all")
        self.assertEqual(
            set(preference.tags.values_list("pk", flat=True)),
            {self.active_tag.pk, self.second_tag.pk},
        )
        self.assertFalse(
            UserSpecialtyTagPreference.objects.filter(
                membership=self.cardio_membership
            ).exists()
        )

    def test_saving_empty_selection_persists_intentionally_empty_preference(
        self,
    ) -> None:
        response = save_via_client(self.client, self.cirger)

        self.assertEqual(response.status_code, 302)
        preference = UserSpecialtyTagPreference.objects.get(
            membership=self.cirger_membership
        )
        self.assertEqual(preference.tags.count(), 0)
        self.assertEqual(preference.mode, "any")

    def test_save_requires_csrf_token(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = save_via_client(csrf_client, self.cirger, tags=[self.active_tag.pk])

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_get_never_saves_a_preference(self) -> None:
        response = self.client.get(reverse(SAVE_URL_NAME))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_forged_specialty_target_is_denied_and_writes_nothing(self) -> None:
        response = save_via_client(self.client, self.cardio, tags=[self.active_tag.pk])

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_other_users_specialty_cannot_be_targeted(self) -> None:
        response = save_via_client(
            self.client, self.cardio_only, tags=[self.active_tag.pk]
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_stale_specialty_target_after_context_switch_is_denied(self) -> None:
        set_current(self.user, self.cardio)

        response = save_via_client(self.client, self.cirger, tags=[self.active_tag.pk])

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_inactive_or_archived_tags_cannot_be_saved(self) -> None:
        for tag in (self.inactive_tag, self.archived_tag):
            with self.subTest(tag=tag.name):
                response = save_via_client(self.client, self.cirger, tags=[tag.pk])
                self.assertEqual(response.status_code, 302)
                self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_inaccessible_restricted_tag_cannot_be_saved(self) -> None:
        response = save_via_client(
            self.client, self.cirger, tags=[self.foreign_tag.pk]
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn(tag_preferences.SAVE_REJECTED_MESSAGE, messages)
        self.assertNotIn(self.foreign_tag.name, " ".join(messages))

    def test_malformed_tag_identifier_is_rejected_without_echo(self) -> None:
        response = save_via_client(self.client, self.cirger, tags=["not-a-tag"])

        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn(tag_preferences.SAVE_REJECTED_MESSAGE, messages)
        self.assertNotIn("not-a-tag", " ".join(messages))

    def test_invalid_mode_is_rejected(self) -> None:
        response = save_via_client(
            self.client, self.cirger, tags=[self.active_tag.pk], tag_mode="xor"
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_save_updates_only_the_current_membership(self) -> None:
        cardio_preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cardio_membership, mode=UserSpecialtyTagPreference.Mode.ALL
        )
        cardio_preference.tags.set([self.second_tag])

        response = save_via_client(self.client, self.cirger, tags=[self.active_tag.pk])

        self.assertEqual(response.status_code, 302)
        cardio_preference.refresh_from_db()
        self.assertEqual(cardio_preference.mode, "all")
        self.assertEqual(
            list(cardio_preference.tags.values_list("pk", flat=True)),
            [self.second_tag.pk],
        )

    def test_anonymous_save_is_redirected_to_login(self) -> None:
        self.client.logout()

        response = save_via_client(self.client, self.cirger, tags=[self.active_tag.pk])

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_save_rejects_an_unknown_specialty_target(self) -> None:
        response = self.client.post(
            reverse(SAVE_URL_NAME),
            {"specialty_id": str(uuid.uuid4()), "tag_mode": "any"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())

    def test_save_rejects_a_malformed_specialty_identifier(self) -> None:
        response = self.client.post(
            reverse(SAVE_URL_NAME),
            {"specialty_id": "not-a-specialty", "tag_mode": "any"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserSpecialtyTagPreference.objects.exists())


class TagPreferenceOverviewTests(TestCase):
    """R1/R4: the preferences page shows retained settings without leakage."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = SuperUserFactory()
        cls.user = make_user("preference-overview-user")
        cls.cirger = make_specialty("Cirurgia Geral", "OCIRGER")
        cls.cardio = make_specialty("Cardiologia", "OCARDIO")
        cls.cirger_membership = join_team(cls.user, cls.cirger)
        cls.cardio_membership = join_team(cls.user, cls.cardio)
        cls.public_tag = make_tag(cls.owner, "Visivel Geral")
        cls.cardio_restricted = make_tag(
            cls.owner,
            "Restrita OCardio",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_page_requires_login(self) -> None:
        self.client.logout()

        response = self.client.get(reverse(PREFERENCES_URL_NAME))

        self.assertEqual(response.status_code, 302)

    def test_page_lists_retained_memberships_and_saved_mode(self) -> None:
        preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cirger_membership, mode=UserSpecialtyTagPreference.Mode.ALL
        )
        preference.tags.set([self.public_tag])

        response = self.client.get(reverse(PREFERENCES_URL_NAME))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.cirger.name)
        self.assertContains(response, self.public_tag.name)
        self.assertContains(response, "Todas as tags")
        self.assertContains(response, self.cardio.name)
        self.assertContains(response, "Sem preferência")

    def test_revoked_membership_retains_preference_without_leaking_names(
        self,
    ) -> None:
        admin = SuperUserFactory()
        preference = UserSpecialtyTagPreference.objects.create(
            membership=self.cardio_membership
        )
        preference.tags.set([self.cardio_restricted])
        team_membership.revoke_membership(
            actor=admin, membership=self.cardio_membership
        )

        response = self.client.get(reverse(PREFERENCES_URL_NAME))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserSpecialtyTagPreference.objects.filter(
                membership=self.cardio_membership
            ).exists()
        )
        self.assertNotContains(response, self.cardio_restricted.name)

    def test_profile_links_owner_to_the_preferences_page(self) -> None:
        response = self.client.get(
            reverse(
                "apps.accounts:profile",
                kwargs={"public_id": self.user.profile.public_id},
            )
        )

        self.assertContains(response, reverse(PREFERENCES_URL_NAME))
