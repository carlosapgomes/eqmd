"""Isolated classification editor fixtures and rendered-control parser."""

import json
from html.parser import HTMLParser
from typing import ClassVar

from allauth.account.models import EmailAddress
from django.test import TestCase

from apps.accounts.models import (
    MedicalSpecialty,
    UserProfile,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.core.models import WardMappingCache
from apps.patients.models import AllowedTag, Patient
from apps.reports.models import Report, ReportTemplate
from apps.reports.tests.tag_fixtures import (
    TemplateTagFixturesMixin,
    make_tag,
    make_template,
)


class TemplateTagEditorFixture(TemplateTagFixturesMixin, TestCase):
    model: ClassVar[ReportTemplate]
    long_tag: ClassVar[AllowedTag]
    foreign_principal: ClassVar[AllowedTag]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.model = make_template(cls.creator, "RTTE Existente")
        cls.model.tags.add(
            cls.public_tag,
            cls.restricted_a,
            cls.inactive_a,
            cls.archived_a,
            cls.restricted_b,
        )
        cls.long_tag = make_tag(
            cls.creator,
            "Reabilitação multidisciplinar de acompanhamento prolongado <b>seguro</b>",
        )
        cls.foreign_principal = make_tag(
            cls.outsider, "RTTE Principal de Outra Equipe", specialty=cls.team_b
        )
        MedicalSpecialty.objects.filter(pk=cls.team_b.pk).update(
            principal_tag=cls.foreign_principal
        )
        profile = cls.creator.profile
        profile.current_specialty = cls.team_a
        profile.save(update_fields=["current_specialty"])
        membership = cls.creator.user_specialties.get(specialty=cls.team_a)
        preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode="all"
        )
        preference.tags.add(cls.public_tag)
        EmailAddress.objects.create(
            user=cls.creator, email=cls.creator.email, primary=True, verified=True
        )

    def setUp(self) -> None:
        self.client.force_login(self.creator)

    def invariant_snapshot(self) -> str:
        return json.dumps(
            {
                "catalogue": list(AllowedTag.all_objects.order_by("pk").values()),
                "profiles": list(UserProfile.objects.order_by("pk").values()),
                "memberships": list(UserSpecialty.objects.order_by("pk").values()),
                "preferences": list(
                    UserSpecialtyTagPreference.objects.values("pk", "mode", "tags")
                ),
                "patients": list(Patient.objects.order_by("pk").values()),
                "reports": list(Report.objects.order_by("pk").values()),
                "cache": list(WardMappingCache.objects.order_by("pk").values()),
            },
            default=str,
            sort_keys=True,
        )


class EditorControls(HTMLParser):
    """Read actual successful native controls, not initial model values."""

    def __init__(self, body: str) -> None:
        super().__init__()
        self.selects: list[dict[str, str | None]] = []
        self.selected: list[str] = []
        self.inputs: list[dict[str, str | None]] = []
        self.in_select = False
        self.feed(body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "select" and data.get("name") == "tag_ids":
            self.selects.append(data)
            self.in_select = True
        if tag == "option" and self.in_select and "selected" in data:
            self.selected.append(str(data["value"]))
        if tag == "input":
            self.inputs.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self.in_select = False
