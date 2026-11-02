"""S5 R4: the shared ward mapping cache cannot decide authorization.

The global cache stays a structural base. Tag metadata and patient
associations are rehydrated and reprojected per requester before rendering, so
a warm payload written by a background command never leaks restricted names,
colours or identifiers and is never mutated for one requester.
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.core.models import WardMappingCache
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
        password="cache-privacy-pass",
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


def join_team(user: Any, specialty: MedicalSpecialty) -> UserSpecialty:
    """Create an active membership row for one team."""
    return UserSpecialty.objects.create(user=user, specialty=specialty, is_active=True)


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


class WardMapCachePrivacyTests(TestCase):
    """R4: warm full/partial cache payloads are reprojected per requester."""

    cirger: MedicalSpecialty
    cardio: MedicalSpecialty
    owner: Any
    public_tag: AllowedTag
    restricted_tag: AllowedTag
    member: Any
    outsider: Any
    ward: Ward
    patient: Patient
    warm_ward_data: dict[str, Any]
    warm_filter_data: dict[str, Any]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("cache-owner")

        cls.public_tag = make_tag(cls.owner, "Prioridade Global", color="#111111")
        cls.restricted_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            color="#222222",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

        cls.member = make_user("cache-member")
        join_team(cls.member, cls.cirger)
        cls.outsider = make_user("cache-outsider")
        join_team(cls.outsider, cls.cardio)

        cls.ward = Ward.objects.create(
            name="Ala Cache",
            abbreviation="ACAH",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.patient = Patient.objects.create(
            name="Paciente Cache",
            birthday="1983-03-03",
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed="303",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        Tag.objects.create(
            allowed_tag=cls.public_tag,
            patient=cls.patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        Tag.objects.create(
            allowed_tag=cls.restricted_tag,
            patient=cls.patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def setUp(self) -> None:
        self._seed_warm_cache()

    def _seed_warm_cache(self) -> None:
        """Write the shared payload exactly as the background command does."""
        self.warm_ward_data = {
            "ward_data": [
                {
                    "ward": {
                        "id": str(self.ward.pk),
                        "name": self.ward.name,
                        "abbreviation": self.ward.abbreviation,
                        "floor": None,
                    },
                    "patient_count": 1,
                    "capacity_estimate": None,
                    "utilization_percentage": None,
                    "patients": [
                        {
                            "patient": {
                                "pk": str(self.patient.pk),
                                "name": self.patient.name,
                            },
                            "bed": self.patient.bed,
                            "admission_duration": None,
                            "tags": [
                                {
                                    "allowed_tag": {
                                        "id": self.public_tag.pk,
                                        "name": self.public_tag.name,
                                        "color": self.public_tag.color,
                                    }
                                },
                                {
                                    "allowed_tag": {
                                        "id": self.restricted_tag.pk,
                                        "name": self.restricted_tag.name,
                                        "color": self.restricted_tag.color,
                                    }
                                },
                            ],
                        }
                    ],
                }
            ],
            "total_patients": 1,
            "total_wards": 1,
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
        self.warm_filter_data = {
            "all_wards": [
                {
                    "id": str(self.ward.pk),
                    "name": self.ward.name,
                    "abbreviation": self.ward.abbreviation,
                }
            ],
            "available_tags": [
                {
                    "id": self.public_tag.pk,
                    "name": self.public_tag.name,
                    "color": self.public_tag.color,
                },
                {
                    "id": self.restricted_tag.pk,
                    "name": self.restricted_tag.name,
                    "color": self.restricted_tag.color,
                },
            ],
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
        WardMappingCache.objects.update_or_create(
            cache_key="ward_mapping_full", defaults={"ward_data": self.warm_ward_data}
        )
        WardMappingCache.objects.update_or_create(
            cache_key="ward_filters", defaults={"ward_data": self.warm_filter_data}
        )

    def map_url(self, **params: Any) -> str:
        url = reverse("patients:patient_map")
        if not params:
            return url
        return f"{url}?{'&'.join(f'{key}={value}' for key, value in params.items())}"

    def patient_tag_ids(self, body: str) -> set[str]:
        """Return the tag ids embedded in the map's data attribute."""
        match = re.search(r'data-patient-tags="([^"]*)"', body)
        if match is None:
            return set()
        return {tag_id for tag_id in match.group(1).split(",") if tag_id}

    def assert_restricted_metadata_absent(self, body: str) -> None:
        """Fail when cached restricted metadata reached the response."""
        hidden = [
            self.restricted_tag.name,
            self.restricted_tag.color,
        ]
        for needle in hidden:
            if needle in body:
                self.fail(f"cached restricted metadata leaked: {needle!r}")
        self.assertNotIn(str(self.restricted_tag.pk), self.patient_tag_ids(body))

    def test_outsider_response_reprojects_the_warm_cache(self) -> None:
        self.client.force_login(self.outsider)

        response = self.client.get(self.map_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(self.patient.name, body)
        self.assertIn(self.public_tag.name, body)
        self.assert_restricted_metadata_absent(body)

    def test_outsider_ajax_tree_response_reprojects_the_warm_cache(self) -> None:
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.map_url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(self.patient.name, body)
        self.assert_restricted_metadata_absent(body)

    def test_member_response_shows_own_team_metadata_from_live_catalogue(self) -> None:
        self.client.force_login(self.member)

        response = self.client.get(self.map_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(self.restricted_tag.name, body)
        self.assertEqual(
            self.patient_tag_ids(body),
            {str(self.public_tag.pk), str(self.restricted_tag.pk)},
        )

    def test_warm_cache_payload_is_never_mutated_for_a_requester(self) -> None:
        self.client.force_login(self.member)
        self.client.get(self.map_url())
        self.client.force_login(self.outsider)
        self.client.get(self.map_url())

        self.assertEqual(
            WardMappingCache.objects.get(cache_key="ward_mapping_full").ward_data,
            self.warm_ward_data,
        )
        self.assertEqual(
            WardMappingCache.objects.get(cache_key="ward_filters").ward_data,
            self.warm_filter_data,
        )

    def test_outsider_tag_filter_options_come_from_current_catalogue(self) -> None:
        self.client.force_login(self.outsider)

        response = self.client.get(self.map_url())

        self.assertEqual(response.status_code, 200)
        available = [tag["name"] for tag in response.context["available_tags"]]
        self.assertIn(self.public_tag.name, available)
        self.assertNotIn(self.restricted_tag.name, available)

    def test_outsider_forged_tag_filter_yields_generic_error_without_results(self) -> None:
        self.client.force_login(self.outsider)

        response = self.client.get(self.map_url(tag=self.restricted_tag.pk))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["tag_filter_error"])
        self.assertEqual(list(response.context["ward_data"]), [])
        self.assertNotContains(response, self.patient.name)
        self.assert_restricted_metadata_absent(response.content.decode())
        self.assertNotIn(
            str(self.restricted_tag.pk), str(response.context["tag_filter_error"])
        )

    def test_visible_tag_filter_still_narrows_the_map(self) -> None:
        self.client.force_login(self.member)

        response = self.client.get(self.map_url(tag=self.restricted_tag.pk))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["tag_filter_error"])
        self.assertEqual(len(response.context["ward_data"]), 1)

    def test_revoked_membership_loses_warm_cache_metadata_immediately(self) -> None:
        membership = UserSpecialty.objects.get(user=self.member, specialty=self.cirger)
        self.client.force_login(self.member)
        warm = self.client.get(self.map_url())
        self.assertIn(self.restricted_tag.name, warm.content.decode())

        UserSpecialty.objects.filter(pk=membership.pk).update(is_active=False)

        response = self.client.get(self.map_url())
        self.assertEqual(response.status_code, 200)
        self.assert_restricted_metadata_absent(response.content.decode())

    def test_reclassified_public_tag_disappears_from_warm_cache_output(self) -> None:
        self.client.force_login(self.outsider)
        warm = self.client.get(self.map_url())
        self.assertIn(self.public_tag.name, warm.content.decode())

        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            visibility=AllowedTag.Visibility.RESTRICTED,
            specialty=self.cirger,
        )

        response = self.client.get(self.map_url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn(self.public_tag.name, body)

    def test_stale_cached_tag_name_is_replaced_by_current_catalogue_name(self) -> None:
        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            name="Prioridade Renomeada"
        )
        self.client.force_login(self.outsider)

        response = self.client.get(self.map_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Prioridade Renomeada", body)
        self.assertNotIn(self.public_tag.name, body)
