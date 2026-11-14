"""Shared fixtures for report-template tag classification tests (S1)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import EqmdCustomUser, MedicalSpecialty, UserSpecialty
from apps.patients.models import AllowedTag
from apps.reports.models import ReportTemplate


def make_user(
    username: str,
    *,
    profession_type: int | None = EqmdCustomUser.MEDICAL_DOCTOR,
    is_staff: bool = False,
    is_superuser: bool = False,
    permissions: tuple[str, ...] = (),
) -> EqmdCustomUser:
    """Create an active user, optionally with model permissions."""
    user = EqmdCustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
        is_staff=is_staff,
        is_superuser=is_superuser,
        password_change_required=False,
        terms_accepted=True,
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
    user: EqmdCustomUser, specialty: MedicalSpecialty, *, active: bool = True
) -> UserSpecialty:
    """Create a retained membership row for one team."""
    return UserSpecialty.objects.create(
        user=user, specialty=specialty, is_active=active
    )


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def make_template(actor: Any, name: str, **overrides: Any) -> ReportTemplate:
    """Create a report template with valid placeholders."""
    defaults: dict[str, Any] = {
        "markdown_body": "Paciente: {{patient_name}}",
        "created_by": actor,
        "updated_by": actor,
    }
    defaults.update(overrides)
    return ReportTemplate.objects.create(name=name, **defaults)


def persisted_tag_ids(template: ReportTemplate) -> set[int]:
    """Return associated tag identities read through the association table."""
    through = ReportTemplate.tags.through
    return set(
        through.objects.filter(reporttemplate_id=template.pk).values_list(
            "allowedtag_id", flat=True
        )
    )


class TemplateTagFixturesMixin:
    """Catalogue and actors shared by the classification tests."""

    team_a: MedicalSpecialty
    team_b: MedicalSpecialty
    creator: EqmdCustomUser
    outsider: EqmdCustomUser
    other_doctor: EqmdCustomUser
    staff_plain: EqmdCustomUser
    catalogue_admin: EqmdCustomUser
    superuser: EqmdCustomUser
    public_tag: AllowedTag
    principal_tag: AllowedTag
    restricted_a: AllowedTag
    restricted_b: AllowedTag
    inactive_a: AllowedTag
    archived_a: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team_a = make_specialty("S1TA")
        cls.team_b = make_specialty("S1TB")

        cls.creator = make_user("s1-creator")
        join_team(cls.creator, cls.team_a)
        cls.outsider = make_user("s1-outsider")
        join_team(cls.outsider, cls.team_b)
        cls.other_doctor = make_user("s1-other-doctor")
        cls.staff_plain = make_user(
            "s1-staff-plain", profession_type=None, is_staff=True
        )
        cls.catalogue_admin = make_user(
            "s1-catalogue-admin",
            profession_type=None,
            is_staff=True,
            permissions=("add_allowedtag", "change_allowedtag"),
        )
        cls.superuser = make_user(
            "s1-superuser",
            profession_type=None,
            is_staff=True,
            is_superuser=True,
        )

        cls.public_tag = make_tag(cls.creator, "S1 Publica")
        cls.principal_tag = make_tag(
            cls.creator,
            "S1 Principal",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.PUBLIC,
        )
        MedicalSpecialty.objects.filter(pk=cls.team_a.pk).update(
            principal_tag_id=cls.principal_tag.pk
        )
        cls.restricted_a = make_tag(
            cls.creator,
            "S1 Restrita A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.restricted_b = make_tag(
            cls.creator,
            "S1 Restrita B",
            specialty=cls.team_b,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.inactive_a = make_tag(
            cls.creator,
            "S1 Inativa A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.archived_a = make_tag(
            cls.creator,
            "S1 Arquivada A",
            specialty=cls.team_a,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )

    def _create_url(self) -> str:
        return reverse("reports:template_create")

    def _update_url(self, template: ReportTemplate) -> str:
        return reverse("reports:template_update", kwargs={"pk": template.pk})

    def _create_payload(self, tag_ids, **overrides):
        payload = {
            "name": "S1 New",
            "markdown_body": "Paciente: {{patient_name}}",
            "is_active": True,
            "is_public": False,
            "tags_present": "1",
            "tag_ids": [str(tag_id) for tag_id in tag_ids],
        }
        payload.update(overrides)
        return payload

    def _update_payload(self, template, tag_ids, **overrides):
        payload = {
            "name": template.name,
            "markdown_body": "Paciente: {{patient_name}}",
            "is_active": True,
            "is_public": template.is_public,
            "tags_present": "1",
            "tag_ids": [str(tag_id) for tag_id in tag_ids],
        }
        payload.update(overrides)
        return payload
