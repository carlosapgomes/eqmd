"""S7 R3: paginated, visibility-checked searchable tag lookup.

The endpoint is a read-only selector backend: active visible tags by default,
inactive/archived visible tags only when historical inclusion is explicitly
requested, and a generic error for malformed input or forged selections.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag


def make_user(username: str, *, permissions: bool = True) -> Any:
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="tag-lookup-pass",
    )
    if permissions:
        user.user_permissions.add(Permission.objects.get(codename="view_patient"))
    return user


def make_specialty(abbreviation: str) -> MedicalSpecialty:
    return MedicalSpecialty.objects.create(
        name=f"Equipe {abbreviation}", abbreviation=abbreviation
    )


def join_team(user: Any, specialty: MedicalSpecialty) -> UserSpecialty:
    return UserSpecialty.objects.create(user=user, specialty=specialty, is_active=True)


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


class TagLookupFixture(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("lookup-owner")
        cls.member = make_user("lookup-member")
        join_team(cls.member, cls.cirger)
        cls.outsider = make_user("lookup-outsider")
        cls.administrator = create_navigation_user(
            username="lookup-admin",
            email="lookup-admin@example.com",
            password="tag-lookup-pass",
            is_staff=True,
            is_superuser=True,
        )

        cls.public_tag = make_tag(cls.owner, "Prioridade Global")
        cls.cirger_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cirger_inactive = make_tag(
            cls.owner,
            "Inativa CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.cirger_archived = make_tag(
            cls.owner,
            "Arquivada CIRGER",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )
        cls.cardio_tag = make_tag(
            cls.owner,
            "Estável CARDIO",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def lookup(self, actor: Any, **params: Any) -> Any:
        self.client.force_login(actor)
        return self.client.get(reverse("patients:tag_lookup"), params)

    def names(self, response: Any) -> set[str]:
        return {row["name"] for row in response.json()["results"]}


class TagLookupVisibilityTests(TagLookupFixture):
    def test_anonymous_is_redirected_to_login(self) -> None:
        response = self.client.get(reverse("patients:tag_lookup"))

        self.assertEqual(response.status_code, 302)

    def test_user_without_patient_permission_is_forbidden(self) -> None:
        actor = make_user("lookup-no-permission", permissions=False)
        response = self.lookup(actor)

        self.assertEqual(response.status_code, 403)

    def test_member_sees_own_team_active_but_not_inactive_or_archived(self) -> None:
        response = self.lookup(self.member)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            self.names(response),
            {self.public_tag.name, self.cirger_tag.name},
        )
        self.assertEqual(payload["count"], 2)
        self.assertEqual({row["state"] for row in payload["results"]}, {"active"})
        abbreviations = {
            row["team_abbreviation"] for row in payload["results"]
        }
        self.assertIn("CIRGER", abbreviations)
        self.assertTrue(
            all("team_abbreviation" in row for row in payload["results"])
        )
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.cirger_inactive.pk), serialized)
        self.assertNotIn(self.cirger_inactive.name, serialized)
        self.assertNotIn(self.cirger_archived.name, serialized)

    def test_member_gets_historical_rows_only_on_explicit_request(self) -> None:
        response = self.lookup(self.member, include_historical="1")

        self.assertEqual(response.status_code, 200)
        states = {
            row["name"]: (row["state"], row["state_label"])
            for row in response.json()["results"]
        }
        self.assertEqual(states[self.cirger_inactive.name], ("inactive", "Inativa"))
        self.assertEqual(states[self.cirger_archived.name], ("archived", "Arquivada"))

    def test_outsider_never_sees_another_team_historical_rows(self) -> None:
        response = self.lookup(self.outsider, include_historical="1")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn(self.cirger_tag.name, body)
        self.assertNotIn(self.cirger_inactive.name, body)
        self.assertNotIn(self.cirger_archived.name, body)
        self.assertNotIn(str(self.cirger_tag.pk), body)
        self.assertNotIn(str(self.cirger_archived.pk), body)
        self.assertEqual(self.names(response), {self.public_tag.name})

    def test_administrator_sees_every_historical_row(self) -> None:
        response = self.lookup(self.administrator, include_historical="1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.names(response),
            {
                self.public_tag.name,
                self.cirger_tag.name,
                self.cirger_inactive.name,
                self.cirger_archived.name,
                self.cardio_tag.name,
            },
        )

    def test_search_matches_name_and_team_abbreviation(self) -> None:
        by_name = self.lookup(self.member, q="Estável")
        by_team = self.lookup(self.member, q="CIRGER")

        self.assertIn(self.cirger_tag.name, self.names(by_name))
        self.assertNotIn(self.cirger_tag.name, self.names(self.lookup(self.member, q="CARDIO")))
        self.assertIn(self.cirger_tag.name, self.names(by_team))


class TagLookupPaginationTests(TagLookupFixture):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        for index in range(23):
            make_tag(cls.owner, f"Paginada {index:02d}")

    def test_page_size_limits_results_and_reports_totals(self) -> None:
        response = self.lookup(self.member, page_size="10")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 10)
        self.assertEqual(payload["count"], 25)
        self.assertEqual(payload["num_pages"], 3)
        self.assertTrue(payload["has_next"])
        self.assertFalse(payload["has_previous"])

    def test_second_page_advances_without_repeating_rows(self) -> None:
        first = self.lookup(self.member, page_size="10", page="1").json()
        second = self.lookup(self.member, page_size="10", page="2").json()

        self.assertTrue(second["has_previous"])
        self.assertFalse(
            {row["id"] for row in first["results"]}
            & {row["id"] for row in second["results"]}
        )


class TagLookupValidationTests(TagLookupFixture):
    def test_invalid_historical_flag_is_a_generic_error(self) -> None:
        response = self.lookup(self.member, include_historical="maybe")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Filtro de tag inválido.")
        self.assertNotIn("maybe", response.json()["error"])

    def test_invalid_page_size_is_a_generic_error(self) -> None:
        response = self.lookup(self.member, page_size="0")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Filtro de tag inválido.")

    def test_forged_selected_id_is_a_generic_error(self) -> None:
        response = self.lookup(self.member, selected=[self.cardio_tag.pk])

        self.assertEqual(response.status_code, 400)
        body = response.content.decode()
        self.assertEqual(response.json()["error"], "Filtro de tag inválido.")
        self.assertNotIn(self.cardio_tag.name, body)
        self.assertNotIn(str(self.cardio_tag.pk), body)

    def test_malformed_selected_id_is_a_generic_error(self) -> None:
        response = self.lookup(self.member, selected=["not-a-tag"])

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("not-a-tag", response.json()["error"])

    def test_valid_selected_ids_are_echoed_without_creating_anything(self) -> None:
        before = AllowedTag.all_objects.count()
        response = self.lookup(self.member, selected=[self.cirger_tag.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["name"] for row in response.json()["selected"]],
            [self.cirger_tag.name],
        )
        self.assertEqual(AllowedTag.all_objects.count(), before)

    def test_post_is_not_allowed(self) -> None:
        self.client.force_login(self.member)
        response = self.client.post(reverse("patients:tag_lookup"), data={})

        self.assertEqual(response.status_code, 405)
