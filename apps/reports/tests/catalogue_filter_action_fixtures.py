"""Isolated catalogue action fixtures; no shared dev profiles or cache writes."""

import json
from datetime import date
from html.parser import HTMLParser
from typing import ClassVar

from allauth.account.models import EmailAddress
from django.test import TestCase

from apps.accounts.models import UserProfile, UserSpecialty, UserSpecialtyTagPreference
from apps.patients.models import AllowedTag, Patient
from apps.reports.models import Report, ReportTemplate
from apps.reports.tests.tag_fixtures import make_tag, make_template
from apps.reports.tests.test_template_discovery import DiscoveryFixturesMixin


class CatalogueActionFixture(DiscoveryFixturesMixin, TestCase):
    """Saved X/ALL, real name matches, untagged models and foreign private data."""

    preference: ClassVar[UserSpecialtyTagPreference]
    patient: ClassVar[Patient]
    long_tag: ClassVar[AllowedTag]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        profile = cls.viewer.profile
        profile.current_specialty = cls.team_a
        profile.save(update_fields=["current_specialty"])
        membership = cls.viewer.user_specialties.get(specialty=cls.team_a)
        cls.preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode="all"
        )
        cls.preference.tags.add(cls.tag_x)
        cls.long_tag = make_tag(
            cls.viewer,
            "Equipe multidisciplinar de acompanhamento prolongado e reabilitação especializada",
        )
        for template, name in (
            (cls.tpl_a, "Ana XY"),
            (cls.tpl_b, "Ana X"),
            (cls.tpl_inactive, "Ana Inativa X"),
            (cls.tpl_c, "Bruno Sem tags"),
        ):
            template.name = name
            template.save(update_fields=["name"])
        for number in range(21):
            make_template(cls.viewer, f"Ana Sem tags {number:02d}")
        EmailAddress.objects.create(
            user=cls.viewer, email=cls.viewer.email, primary=True, verified=True
        )
        cls.patient = Patient.objects.create(
            name="Paciente sintético RTFA",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.viewer,
            updated_by=cls.viewer,
        )

    def snapshot(self) -> str:
        return json.dumps(
            {
                "preferences": list(
                    UserSpecialtyTagPreference.objects.values("pk", "mode", "tags")
                ),
                "memberships": list(UserSpecialty.objects.values()),
                "profiles": list(UserProfile.objects.order_by("pk").values()),
                "templates": list(ReportTemplate.objects.order_by("pk").values()),
                "associations": list(
                    ReportTemplate.tags.through.objects.order_by("pk").values()
                ),
                "reports": list(Report.objects.values()),
                "patients": list(Patient.objects.order_by("pk").values()),
                "catalogue": list(AllowedTag.all_objects.order_by("pk").values()),
            },
            default=str,
            sort_keys=True,
        )


class AttributeParser(HTMLParser):
    """Collect actual rendered elements with one named attribute."""

    def __init__(self, attribute: str) -> None:
        super().__init__()
        self.attribute = attribute
        self.elements: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if self.attribute in values:
            self.elements.append(values)


def elements(body: str, attribute: str) -> list[dict[str, str | None]]:
    parser = AttributeParser(attribute)
    parser.feed(body)
    return parser.elements
