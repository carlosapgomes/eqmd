"""Isolated real ORM/default/cache fixtures for PMFA-S1 regressions."""

import json
import re
from html import unescape
from typing import TYPE_CHECKING, ClassVar

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    EqmdCustomUser,
    MedicalSpecialty,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.tests.helpers import create_navigation_user
from apps.core.models import WardMappingCache
from apps.patients.models import AllowedTag, Patient, Ward
from apps.patients.tests.test_ward_map_tag_filters import (
    assign,
    make_patient,
    seed_warm_cache,
)

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse


class MapFilterFixture(TestCase):
    """Saved X/ALL, five inpatients, three wards and an excluded outpatient."""

    viewer: ClassVar[EqmdCustomUser]
    specialty: ClassVar[MedicalSpecialty]
    preference: ClassVar[UserSpecialtyTagPreference]
    x: ClassVar[AllowedTag]
    y: ClassVar[AllowedTag]
    hidden: ClassVar[AllowedTag]
    wards: ClassVar[list[Ward]]
    inpatients: ClassVar[list[Patient]]
    outpatient: ClassVar[Patient]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.viewer = create_navigation_user(
            username="pmfa-viewer",
            email="pmfa-viewer@example.com",
            password="isolated-pmfa-test",
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
        )
        EmailAddress.objects.create(
            user=cls.viewer, email=cls.viewer.email, verified=True, primary=True
        )
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_patient"))
        cls.specialty = MedicalSpecialty.objects.create(
            name="Equipe PMFA", abbreviation="PMFA"
        )
        membership = UserSpecialty.objects.create(
            user=cls.viewer, specialty=cls.specialty
        )
        profile = cls.viewer.profile
        profile.current_specialty = cls.specialty
        profile.save(update_fields=["current_specialty"])
        cls.x = cls.create_tag("PMFA X", cls.specialty)
        cls.y = cls.create_tag("PMFA Y", cls.specialty)
        other = MedicalSpecialty.objects.create(
            name="Equipe privada PMFA", abbreviation="PMFB"
        )
        cls.hidden = cls.create_tag("PMFA Z restrita", other)
        cls.preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode="all"
        )
        cls.preference.tags.add(cls.x)
        cls.create_population()

    @classmethod
    def create_tag(cls, name: str, specialty: MedicalSpecialty) -> AllowedTag:
        return AllowedTag.objects.create(
            name=name,
            specialty=specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=cls.viewer,
            updated_by=cls.viewer,
        )

    @classmethod
    def create_population(cls) -> None:
        cls.wards = [
            Ward.objects.create(
                name=f"PMFA Ala {label}",
                abbreviation=f"P{label}",
                created_by=cls.viewer,
                updated_by=cls.viewer,
            )
            for label in "ABC"
        ]
        cls.inpatients = []
        for name, ward, tags in (
            ("Ana X", cls.wards[0], [cls.x]),
            ("Ana Y", cls.wards[0], [cls.y]),
            ("Ana XY", cls.wards[0], [cls.x, cls.y]),
            ("Bruno Y", cls.wards[1], [cls.y]),
            ("Bruno Sem tag", cls.wards[1], []),
        ):
            patient = make_patient(
                cls.viewer, name, status=Patient.Status.INPATIENT, ward=ward, bed="01"
            )
            cls.inpatients.append(patient)
            for tag in tags:
                assign(cls.viewer, patient, tag)
        cls.outpatient = make_patient(
            cls.viewer,
            "PMFA Ambulatório",
            status=Patient.Status.OUTPATIENT,
            ward=cls.wards[0],
        )
        assign(cls.viewer, cls.outpatient, cls.x)
        seed_warm_cache(
            [
                (cls.wards[0], cls.inpatients[:3]),
                (cls.wards[1], cls.inpatients[3:]),
                (cls.wards[2], []),
            ]
        )

    def setUp(self) -> None:
        self.client.force_login(self.viewer)

    def response(
        self, *, ajax: bool = False, **params: str
    ) -> "_MonkeyPatchedWSGIResponse":
        response = self.client.get(
            reverse("patients:patient_map"),
            params,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest" if ajax else "",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def action_href(self, response: "_MonkeyPatchedWSGIResponse", label: str) -> str:
        pattern = (
            r'<a\b[^>]*href="([^"]+)"[^>]*>\s*(?:<i[^>]*>[^<]*</i>)?\s*'
            + re.escape(label)
            + r"\s*</a>"
        )
        found = re.findall(pattern, response.content.decode(), re.DOTALL)
        self.assertEqual(len(found), 1, f"Expected one {label} action")
        return unescape(found[0])

    def snapshot(self) -> str:
        return json.dumps(
            {
                "preferences": list(
                    UserSpecialtyTagPreference.objects.values("pk", "mode", "tags")
                ),
                "memberships": list(UserSpecialty.objects.values()),
                "specialty": str(self.viewer.profile.current_specialty_id),
                "cache": list(WardMappingCache.objects.order_by("cache_key").values()),
                "patients": list(
                    Patient.objects.order_by("pk").values(
                        "pk", "status", "ward_id", "updated_at"
                    )
                ),
            },
            default=str,
            sort_keys=True,
        )
