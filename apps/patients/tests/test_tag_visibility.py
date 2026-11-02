"""S5 R1/R4: every patient tag reader returns only requester-visible metadata.

Each assertion is a payload-negative check: a restricted tag's name, colour,
catalogue id and association id must be absent from the response body for an
outsider, while the same fixture must prove the authorised positive case.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag, Ward

CLINICAL_PERMISSIONS = ("change_patient", "view_patient")


def make_user(
    username: str,
    *,
    permissions: tuple[str, ...] | None = CLINICAL_PERMISSIONS,
    is_staff: bool = False,
    is_superuser: bool = False,
):
    """Create an active account with the requested clinical permissions."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="visibility-pass",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    if permissions:
        user.user_permissions.add(
            *[Permission.objects.get(codename=codename) for codename in permissions]
        )
    return user


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


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


class TagReaderVisibilityFixture(TestCase):
    """Shared catalogue/patient fixture for the reader matrix."""

    cirger: MedicalSpecialty
    cardio: MedicalSpecialty
    owner: Any
    public_tag: AllowedTag
    restricted_tag: AllowedTag
    inactive_restricted_tag: AllowedTag
    archived_restricted_tag: AllowedTag
    member: Any
    member_membership: UserSpecialty
    outsider: Any
    revoked: Any
    revoked_membership: UserSpecialty
    administrator: Any
    ward: Ward
    patient: Patient
    public_association: Tag
    restricted_association: Tag
    inactive_association: Tag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("visibility-owner")

        cls.public_tag = make_tag(cls.owner, "Prioridade Global", color="#111111")
        cls.restricted_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            color="#222222",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.inactive_restricted_tag = make_tag(
            cls.owner,
            "Inativa CIRGER",
            color="#333333",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.archived_restricted_tag = make_tag(
            cls.owner,
            "Arquivada CIRGER",
            color="#444444",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )

        cls.member = make_user("visibility-member")
        cls.member_membership = join_team(cls.member, cls.cirger)
        cls.outsider = make_user("visibility-outsider")
        join_team(cls.outsider, cls.cardio)
        cls.revoked = make_user("visibility-revoked")
        cls.revoked_membership = join_team(cls.revoked, cls.cirger, active=False)
        cls.administrator = make_user(
            "visibility-admin", permissions=None, is_staff=True, is_superuser=True
        )

        cls.ward = Ward.objects.create(
            name="Unidade CIRGER",
            abbreviation="UCIR",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.patient = Patient.objects.create(
            name="Paciente Visibilidade",
            birthday="1980-01-01",
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed="101",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.public_association = Tag.objects.create(
            allowed_tag=cls.public_tag,
            patient=cls.patient,
            notes="public note",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.restricted_association = Tag.objects.create(
            allowed_tag=cls.restricted_tag,
            patient=cls.patient,
            notes="restricted note",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.inactive_association = Tag.objects.create(
            allowed_tag=cls.inactive_restricted_tag,
            patient=cls.patient,
            notes="inactive note",
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def login(self, actor: Any) -> None:
        self.client.force_login(actor)

    def assert_restricted_metadata_absent(self, body: str) -> None:
        """Fail when any hidden restricted identifier or label leaked."""
        hidden = [
            self.restricted_tag.name,
            self.restricted_tag.color,
            self.inactive_restricted_tag.name,
            self.inactive_restricted_tag.color,
            self.archived_restricted_tag.name,
            str(self.restricted_association.pk),
            str(self.inactive_association.pk),
            "restricted note",
            "inactive note",
        ]
        for needle in hidden:
            if needle in body:
                self.fail(f"restricted metadata leaked into the response: {needle!r}")

    def assert_hidden_catalogue_ids_absent(self, payload: Any) -> None:
        """Fail when a hidden catalogue identity appears in structured output."""
        serialized = json.dumps(payload, default=str)
        hidden_ids = [
            self.restricted_tag.pk,
            self.inactive_restricted_tag.pk,
            self.archived_restricted_tag.pk,
        ]
        for hidden_id in hidden_ids:
            for pattern in (f'"allowed_tag_id": {hidden_id}', f'"id": {hidden_id}'):
                if pattern in serialized:
                    self.fail(f"hidden catalogue identifier leaked: {pattern}")


class PatientListReaderTests(TagReaderVisibilityFixture):
    """R1: the patient list table and its tag selector are requester-aware."""

    def test_patient_list_row_shows_visible_restricted_badge_to_member(self) -> None:
        self.login(self.member)

        response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)
        self.assertContains(response, "Inativa")

    def test_patient_list_row_hides_restricted_badge_from_outsider(self) -> None:
        self.login(self.outsider)

        response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_tag.name)
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_patient_list_selector_lists_only_visible_tags(self) -> None:
        self.login(self.outsider)

        response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            self.restricted_tag.name, self.selector_markup(response.content.decode())
        )
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_patient_list_selector_offers_own_team_tag(self) -> None:
        self.login(self.member)

        response = self.client.get(reverse("patients:patient_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.restricted_tag.name, self.selector_markup(response.content.decode())
        )

    def selector_markup(self, body: str) -> str:
        """Return only the tag <select> block so row badges cannot mask a leak."""
        start = body.index('id="tag"')
        return body[start : body.index("</select>", start)]


class PatientListFilterTests(TagReaderVisibilityFixture):
    """R4: legacy single-tag filter input enforces visibility now."""

    def test_visible_tag_filter_still_returns_the_patient(self) -> None:
        self.login(self.member)

        response = self.client.get(
            reverse("patients:patient_list"), {"tag": self.restricted_tag.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p.pk for p in response.context["patients"]], [self.patient.pk])

    def test_outsider_forged_restricted_filter_yields_no_inferential_result(self) -> None:
        self.login(self.outsider)

        response = self.client.get(
            reverse("patients:patient_list"), {"tag": self.restricted_tag.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotContains(response, self.patient.name)
        self.assert_restricted_metadata_absent(str(response.context["tag_filter_error"]))

    def test_unknown_filter_id_yields_generic_error_without_results(self) -> None:
        self.login(self.member)

        response = self.client.get(
            reverse("patients:patient_list"), {"tag": "999999"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotContains(response, self.patient.name)
        self.assertNotIn("999999", str(response.context["tag_filter_error"]))

    def test_malformed_filter_value_yields_generic_error_without_results(self) -> None:
        self.login(self.member)

        response = self.client.get(
            reverse("patients:patient_list"), {"tag": "not-a-tag"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["patients"]), [])
        self.assertTrue(response.context["tag_filter_error"])
        self.assertNotIn("not-a-tag", str(response.context["tag_filter_error"]))

    def test_archived_visible_filter_is_allowed_for_member(self) -> None:
        Tag.objects.create(
            allowed_tag=self.archived_restricted_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.login(self.member)

        response = self.client.get(
            reverse("patients:patient_list"), {"tag": self.archived_restricted_tag.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p.pk for p in response.context["patients"]], [self.patient.pk])


class PatientDetailAndApiReaderTests(TagReaderVisibilityFixture):
    """R1: server-rendered detail HTML and the tag AJAX API payloads."""

    def api_url(self) -> str:
        return reverse(
            "patients:patient_tags_api", kwargs={"patient_id": self.patient.pk}
        )

    def test_detail_page_shows_restricted_badge_and_state_to_member(self) -> None:
        self.login(self.member)

        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)
        self.assertContains(response, "Inativa")

    def test_detail_page_hides_restricted_metadata_from_outsider(self) -> None:
        self.login(self.outsider)

        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_tag.name)
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_tag_api_hides_restricted_metadata_from_outsider(self) -> None:
        self.login(self.outsider)

        response = self.client.get(self.api_url())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [tag["name"] for tag in payload["current_tags"]]
        self.assertEqual(names, [self.public_tag.name])
        self.assert_hidden_catalogue_ids_absent(payload)
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_tag_api_lists_visible_state_for_member(self) -> None:
        self.login(self.member)

        response = self.client.get(self.api_url())

        self.assertEqual(response.status_code, 200)
        current = {tag["name"]: tag for tag in response.json()["current_tags"]}
        self.assertEqual(current[self.restricted_tag.name]["state"], "active")
        self.assertEqual(current[self.inactive_restricted_tag.name]["state"], "inactive")
        self.assertEqual(
            current[self.inactive_restricted_tag.name]["state_label"], "Inativa"
        )

    def test_tag_api_available_options_hide_inaccessible_tags(self) -> None:
        self.login(self.outsider)

        response = self.client.get(self.api_url())

        self.assertEqual(response.status_code, 200)
        available = {tag["name"] for tag in response.json()["available_tags"]}
        self.assertEqual(available, set())
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_administrator_sees_restricted_metadata_without_membership(self) -> None:
        self.login(self.administrator)

        response = self.client.get(self.api_url())

        self.assertEqual(response.status_code, 200)
        names = {tag["name"] for tag in response.json()["current_tags"]}
        self.assertEqual(
            names,
            {
                self.public_tag.name,
                self.restricted_tag.name,
                self.inactive_restricted_tag.name,
            },
        )


class TagMutationPayloadTests(TagReaderVisibilityFixture):
    """R1: add/remove/bulk AJAX responses carry projected payloads only."""

    def test_remove_response_payload_is_projected_for_the_caller(self) -> None:
        self.login(self.member)

        response = self.client.post(
            reverse(
                "patients:patient_tag_remove",
                kwargs={"patient_id": self.patient.pk, "tag_id": self.public_association.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = {tag["name"] for tag in payload["tags"]}
        self.assertIn(self.restricted_tag.name, names)
        self.assertNotIn(self.public_tag.name, names)

    def test_bulk_remove_response_payload_omits_preserved_hidden_associations(self) -> None:
        self.login(self.outsider)

        response = self.client.post(
            reverse(
                "patients:patient_tag_remove_all",
                kwargs={"patient_id": self.patient.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["preserved"], 2)
        self.assertEqual([tag["name"] for tag in payload["tags"]], [])
        self.assert_restricted_metadata_absent(response.content.decode())


class WardReaderTests(TagReaderVisibilityFixture):
    """R1: ward detail rows and the ward patient map."""

    def test_ward_detail_hides_restricted_badges_from_outsider(self) -> None:
        self.login(self.outsider)

        response = self.client.get(
            reverse("patients:ward_detail", kwargs={"pk": self.ward.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_ward_detail_shows_restricted_badges_to_member(self) -> None:
        self.login(self.member)

        response = self.client.get(
            reverse("patients:ward_detail", kwargs={"pk": self.ward.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)


class RevocationTests(TagReaderVisibilityFixture):
    """R1: revocation applies to the next response of an existing session."""

    def test_revocation_removes_restricted_metadata_everywhere(self) -> None:
        self.login(self.member)
        list_url = reverse("patients:patient_list")
        detail_url = reverse(
            "patients:patient_detail", kwargs={"pk": self.patient.pk}
        )
        api_url = reverse(
            "patients:patient_tags_api", kwargs={"patient_id": self.patient.pk}
        )

        warm = self.client.get(list_url)
        self.assertContains(warm, self.restricted_tag.name)

        UserSpecialty.objects.filter(pk=self.member_membership.pk).update(
            is_active=False
        )

        for url in (list_url, detail_url, api_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assert_restricted_metadata_absent(response.content.decode())
