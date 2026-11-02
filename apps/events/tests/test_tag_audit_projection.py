"""S5 R2/R3: timeline tag audit presentation follows current visibility.

Every historical action is rendered from stable catalogue references plus the
current catalogue/membership state. Outsiders receive a generic restricted-tag
action (actor, team abbreviation, time) and never a hidden name, colour,
description, note or identifier.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth.models import Permission
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import TagAddedEvent
from apps.events.services import tag_audit, tag_audit_presentation
from apps.patients.models import AllowedTag, Patient, Tag, Ward

CLINICAL_PERMISSIONS = ("change_patient", "view_patient")
UNRESOLVED_TAG_AUDIT_SUMMARY = "Ação de tag não identificada"
UNPROJECTED_TAG_AUDIT_SUMMARY = "Ação de tag registrada"


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
        password="projection-pass",
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


def template_request(actor: Any):
    """Build a request whose user is the given actor for inclusion tags."""
    request = RequestFactory().get("/")
    request.user = actor
    return request


class TagAuditProjectionFixture(TestCase):
    """Shared event fixture for the timeline projection matrix."""

    cirger: MedicalSpecialty
    cardio: MedicalSpecialty
    owner: Any
    public_tag: AllowedTag
    restricted_tag: AllowedTag
    cardio_restricted_tag: AllowedTag
    member: Any
    outsider: Any
    administrator: Any
    ward: Ward
    patient: Patient
    current_association: Tag
    restricted_association: Tag
    restricted_event: TagAddedEvent

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("CIRGER")
        cls.cardio = make_specialty("CARDIO")
        cls.owner = make_user("audit-owner")
        cls.owner.first_name = "Ana"
        cls.owner.last_name = "Lima"
        cls.owner.save(update_fields=["first_name", "last_name"])

        cls.public_tag = make_tag(cls.owner, "Prioridade Global", color="#101010")
        cls.restricted_tag = make_tag(
            cls.owner,
            "Estável CIRGER",
            color="#202020",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cardio_restricted_tag = make_tag(
            cls.owner,
            "Cardio Restrita",
            color="#303030",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

        cls.member = make_user("audit-member")
        join_team(cls.member, cls.cirger)
        cls.outsider = make_user("audit-outsider")
        join_team(cls.outsider, cls.cardio)
        cls.administrator = make_user(
            "audit-admin", permissions=None, is_staff=True, is_superuser=True
        )

        cls.ward = Ward.objects.create(
            name="Enfermaria Auditoria",
            abbreviation="EAUD",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.patient = Patient.objects.create(
            name="Paciente Auditoria",
            birthday="1979-05-05",
            status=Patient.Status.INPATIENT,
            ward=cls.ward,
            bed="202",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        # A current association that stays on the patient for the header badge.
        cls.current_association = Tag.objects.create(
            allowed_tag=cls.public_tag,
            patient=cls.patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.restricted_association = Tag.objects.create(
            allowed_tag=cls.restricted_tag,
            patient=cls.patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        cls.restricted_event = tag_audit.record_tag_added(
            actor=cls.owner,
            patient=cls.patient,
            tag=cls.restricted_tag,
            notes="nota secreta",
        )

    def login(self, actor: Any) -> None:
        self.client.force_login(actor)

    def timeline_url(self) -> str:
        return reverse(
            "patients:patient_events_timeline", kwargs={"patient_id": self.patient.pk}
        )

    def assert_restricted_event_metadata_absent(self, body: str) -> None:
        """Fail when any hidden tag audit identifier or label leaked."""
        hidden = [
            self.restricted_tag.name,
            self.restricted_tag.color,
            "nota secreta",
            f'"tag_id": {self.restricted_tag.pk}',
            f'data-tag-id="{self.restricted_association.pk}"',
        ]
        for needle in hidden:
            if needle in body:
                self.fail(f"restricted event metadata leaked: {needle!r}")


class TimelineReaderTests(TagAuditProjectionFixture):
    """R2: the patient timeline card is projected per requester."""

    def test_member_sees_detailed_restricted_action(self) -> None:
        self.login(self.member)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)
        self.assertContains(response, self.public_tag.name)

    def test_outsider_sees_generic_restricted_action(self) -> None:
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assert_restricted_event_metadata_absent(body)
        self.assertIn("Tag restrita (CIRGER)", body)
        self.assertIn("Tag restrita (CIRGER) adicionada", body)

    def test_outsider_timeline_keeps_actor_and_time(self) -> None:
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Lima")
        self.assertContains(response, "adicionada")

    def test_administrator_sees_detailed_restricted_action(self) -> None:
        self.login(self.administrator)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)

    def test_mixed_bulk_event_redacts_only_the_hidden_classification(self) -> None:
        tag_audit.record_bulk_removed(
            actor=self.owner,
            patient=self.patient,
            removed=[(self.public_tag, "publica"), (self.restricted_tag, "oculta")],
        )
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(self.public_tag.name, body)
        self.assert_restricted_event_metadata_absent(body)
        self.assertIn("Tag restrita (CIRGER)", body)
        self.assertIn("removida", body)

    def test_bulk_event_never_renders_the_concatenated_legacy_names(self) -> None:
        bulk_event = tag_audit.record_bulk_removed(
            actor=self.owner,
            patient=self.patient,
            removed=[(self.restricted_tag, "oculta")],
        )
        self.assertEqual(bulk_event.tag_names, self.restricted_tag.name)
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assert_restricted_event_metadata_absent(response.content.decode())


class ReclassificationTests(TagAuditProjectionFixture):
    """R2: current visibility governs historical event output."""

    def test_public_to_restricted_reclassification_protects_old_event(self) -> None:
        event = tag_audit.record_tag_added(
            actor=self.owner, patient=self.patient, tag=self.public_tag, notes="nota publica"
        )
        self.login(self.outsider)
        warm = self.client.get(self.timeline_url())
        self.assertContains(warm, self.public_tag.name)

        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            visibility=AllowedTag.Visibility.RESTRICTED,
            specialty=self.cirger,
        )

        for url in (
            self.timeline_url(),
            reverse(
                "events:patient_events_list", kwargs={"patient_id": self.patient.pk}
            ),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            body = response.content.decode()
            self.assertNotIn(f"Tag '{self.public_tag.name}'", body)
            self.assertNotIn("nota publica", body)
            self.assertIn("Tag restrita", body)
        self.assertTrue(
            TagAddedEvent.objects.filter(pk=event.pk).exists(),
            "the stored event must never be rewritten or deleted",
        )

    def test_reclassification_keeps_action_time_snapshot_for_members(self) -> None:
        event = tag_audit.record_tag_added(
            actor=self.owner, patient=self.patient, tag=self.public_tag
        )
        AllowedTag.all_objects.filter(pk=self.public_tag.pk).update(
            name="Renomeada",
            visibility=AllowedTag.Visibility.RESTRICTED,
            specialty=self.cirger,
        )
        self.login(self.member)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_tag.name)
        self.assertEqual(event.tag_references.first().tag_name, self.public_tag.name)


class LegacyEventTests(TagAuditProjectionFixture):
    """R2: unresolved legacy snapshots stay intact and render generically."""

    def test_unresolved_legacy_event_is_generic_and_unchanged(self) -> None:
        legacy = TagAddedEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=3),
            description="Tag 'Fantasma' adicionada",
            tag_name="Fantasma",
            tag_color="#999999",
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Fantasma")
        self.assertContains(response, UNRESOLVED_TAG_AUDIT_SUMMARY)
        self.assertContains(response, "Tag restrita")
        legacy.refresh_from_db()
        self.assertEqual(legacy.description, "Tag 'Fantasma' adicionada")
        self.assertEqual(legacy.tag_name, "Fantasma")

    def test_resolvable_legacy_event_shows_details_to_members(self) -> None:
        legacy = TagAddedEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=1),
            description=f"Tag '{self.restricted_tag.name}' adicionada",
            tag_name=self.restricted_tag.name,
            tag_color=self.restricted_tag.color,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.assertFalse(legacy.tag_references.exists())
        self.login(self.member)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.restricted_tag.name)

    def test_resolvable_legacy_event_is_redacted_for_outsiders(self) -> None:
        TagAddedEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=1),
            description=f"Tag '{self.restricted_tag.name}' adicionada",
            tag_name=self.restricted_tag.name,
            tag_color=self.restricted_tag.color,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assert_restricted_event_metadata_absent(response.content.decode())
        self.assertContains(response, "Tag restrita (CIRGER)")


class MissingCatalogueRowTests(TagAuditProjectionFixture):
    """D4/D5: a resolved snapshot without its current row stays fail-closed."""

    ORPHAN_NAME = "Temporária CIRGER"
    ORPHAN_COLOR = "#616161"

    def make_snapshot_without_catalogue_row(self) -> tuple[TagAddedEvent, int]:
        """Record a legacy snapshot that resolves, then remove its current row."""
        tag = make_tag(
            self.owner,
            self.ORPHAN_NAME,
            color=self.ORPHAN_COLOR,
            specialty=self.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        legacy = TagAddedEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description=f"Tag '{tag.name}' adicionada",
            tag_name=tag.name,
            tag_color=tag.color,
            created_by=self.owner,
            updated_by=self.owner,
        )
        tag_id = tag.pk
        tag.hard_delete()
        self.assertFalse(
            AllowedTag.all_objects.filter(pk=tag_id).exists(),
            "the fixture must remove the current catalogue row",
        )
        return legacy, tag_id

    def test_snapshot_without_current_row_still_resolves_from_history(self) -> None:
        legacy, tag_id = self.make_snapshot_without_catalogue_row()

        resolution = tag_audit.resolve_legacy_event(legacy)

        self.assertEqual(resolution.status, "known")
        self.assertEqual(resolution.tag_ids, (tag_id,))
        self.assertIsNone(tag_audit.LegacyEventResolver().tag(tag_id))

    def test_outsider_timeline_never_emits_the_orphan_snapshot(self) -> None:
        legacy, _tag_id = self.make_snapshot_without_catalogue_row()
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn(self.ORPHAN_NAME, body)
        self.assertNotIn(self.ORPHAN_COLOR, body)
        self.assertEqual(
            body.count(UNRESOLVED_TAG_AUDIT_SUMMARY),
            1,
            "the orphan snapshot must render the generic unidentified action",
        )
        presentation = tag_audit_presentation.project_tag_audit_event(legacy, viewer=self.outsider)
        if presentation is None:
            self.fail("a tag audit event must always project")
        self.assertTrue(presentation.unresolved)
        self.assertEqual(presentation.summary, UNRESOLVED_TAG_AUDIT_SUMMARY)
        self.assertTrue(all(not action.visible for action in presentation.actions))
        payload = tag_audit_presentation.tag_audit_payload(presentation)
        self.assertNotIn(self.ORPHAN_NAME, str(payload))
        self.assertNotIn(self.ORPHAN_COLOR, str(payload))

    def test_outsider_list_and_widget_never_emit_the_orphan_snapshot(self) -> None:
        self.make_snapshot_without_catalogue_row()
        self.login(self.outsider)

        list_response = self.client.get(
            reverse(
                "events:patient_events_list", kwargs={"patient_id": self.patient.pk}
            )
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertNotIn(self.ORPHAN_NAME, list_response.content.decode())
        template = Template("{% load event_tags %}{% recent_events_widget patient %}")
        rendered = template.render(
            Context(
                {"patient": self.patient, "request": template_request(self.outsider)}
            )
        )
        self.assertNotIn(self.ORPHAN_NAME, rendered)
        self.assertNotIn(self.ORPHAN_COLOR, rendered)

    def test_administrator_keeps_the_detailed_orphan_snapshot(self) -> None:
        self.make_snapshot_without_catalogue_row()
        self.login(self.administrator)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ORPHAN_NAME)
        self.assertContains(response, self.ORPHAN_COLOR)

    def test_resolved_public_snapshot_keeps_details_for_outsiders(self) -> None:
        public_tag = make_tag(self.owner, "Prioridade Auditada", color="#515151")
        legacy = TagAddedEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description=f"Tag '{public_tag.name}' adicionada",
            tag_name=public_tag.name,
            tag_color=public_tag.color,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.assertEqual(tag_audit.resolve_legacy_event(legacy).status, "known")
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, public_tag.name)
        self.assertContains(response, public_tag.color)


class EventDescriptionFallbackTests(TestCase):
    """R2: an unprojected tag audit event fails closed instead of leaking."""

    def test_unprojected_tag_audit_event_uses_the_generic_description(self) -> None:
        actor = make_user("fallback-owner")
        patient = Patient.objects.create(
            name="Paciente Fallback",
            birthday="1982-02-02",
            created_by=actor,
            updated_by=actor,
        )
        event = TagAddedEvent.objects.create(
            patient=patient,
            event_datetime=timezone.now(),
            description="Tag 'Segredo' adicionada",
            tag_name="Segredo",
            tag_color="#777777",
            created_by=actor,
            updated_by=actor,
        )

        self.assertEqual(event.get_display_description(), UNPROJECTED_TAG_AUDIT_SUMMARY)
        self.assertNotIn("Segredo", event.get_excerpt())
        self.assertEqual(event.description, "Tag 'Segredo' adicionada")


class EventListReaderTests(TagAuditProjectionFixture):
    """R2: list/table and widget readers use the projected description."""

    def test_patient_events_list_hides_restricted_metadata(self) -> None:
        self.login(self.outsider)

        response = self.client.get(
            reverse(
                "events:patient_events_list", kwargs={"patient_id": self.patient.pk}
            )
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assert_restricted_event_metadata_absent(body)
        self.assertIn("Tag restrita (CIRGER)", body)
        self.assertIn("Tag restrita (CIRGER) adicionada", body)

    def test_user_events_list_hides_restricted_metadata(self) -> None:
        self.login(self.owner)

        response = self.client.get(reverse("events:user_events_list"))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Tag restrita", body)
        self.assertNotIn(f"Tag '{self.restricted_tag.name}'", body)

    def test_recent_events_widget_hides_restricted_metadata(self) -> None:
        self.login(self.outsider)

        template = Template("{% load event_tags %}{% recent_events_widget patient %}")
        rendered = template.render(
            Context({"patient": self.patient, "request": template_request(self.outsider)})
        )

        self.assert_restricted_event_metadata_absent(rendered)
        self.assertIn("Tag restrita", rendered)

    def test_recent_events_widget_shows_details_to_members(self) -> None:
        self.login(self.member)

        template = Template("{% load event_tags %}{% recent_events_widget patient %}")
        rendered = template.render(
            Context({"patient": self.patient, "request": template_request(self.member)})
        )

        self.assertIn(self.restricted_tag.name, rendered)

    def test_event_api_payload_is_projected(self) -> None:
        presentation = tag_audit_presentation.project_tag_audit_event(
            self.restricted_event, viewer=self.outsider
        )

        if presentation is None:
            self.fail("a tag audit event must always project")
        payload = tag_audit_presentation.tag_audit_payload(presentation)
        self.assertNotIn(self.restricted_tag.name, str(payload))
        self.assertEqual(payload["summary"], "Tag restrita (CIRGER) adicionada")
        self.assertEqual(payload["actions"][0]["action"], "added")
        self.assertEqual(payload["actions"][0]["team_abbreviation"], "CIRGER")
        self.assertFalse(payload["actions"][0]["visible"])

    def test_event_detail_api_response_never_carries_restricted_names(self) -> None:
        self.login(self.outsider)
        self.client.raise_request_exception = False

        response = self.client.get(
            reverse("events:event_api_detail", kwargs={"pk": self.restricted_event.pk})
        )

        self.assertNotIn(
            self.restricted_tag.name, response.content.decode(errors="ignore")
        )


class TimelineHeaderTests(TagAuditProjectionFixture):
    """R3: current visible tags in the timeline header, desktop and mobile."""

    def header_markup(self, body: str, element_id: str) -> str:
        """Return one header badge block by id."""
        start = body.index(f'id="{element_id}"')
        return body[start : body.index("</div>", start)]

    def test_header_shows_current_visible_tag_on_desktop_and_mobile(self) -> None:
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for element_id in ("timeline-current-tags", "timeline-current-tags-mobile"):
            markup = self.header_markup(body, element_id)
            self.assertIn(self.public_tag.name, markup)
            self.assertNotIn(self.restricted_tag.name, markup)

    def test_header_labels_inactive_association_state(self) -> None:
        inactive_tag = make_tag(
            self.owner,
            "Inativa Auditoria",
            color="#404040",
            specialty=self.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        Tag.objects.create(
            allowed_tag=inactive_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.login(self.member)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        markup = self.header_markup(response.content.decode(), "timeline-current-tags")
        self.assertIn(inactive_tag.name, markup)
        self.assertIn("Inativa", markup)

    def test_header_excludes_removed_association_and_keeps_history(self) -> None:
        removed_tag = make_tag(self.owner, "Removida Auditoria", color="#505050")
        tag_audit.record_tag_added(
            actor=self.owner, patient=self.patient, tag=removed_tag
        )
        tag_audit.record_tag_removed(
            actor=self.owner, patient=self.patient, tag=removed_tag
        )
        self.login(self.outsider)

        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        header = self.header_markup(body, "timeline-current-tags")
        self.assertNotIn(removed_tag.name, header)
        # The historical removal stays represented below the header.
        self.assertIn(removed_tag.name, body)


class PatientTagsInclusionTagTests(TagAuditProjectionFixture):
    """R1: the reusable patient tag inclusion tag is requester-aware."""

    def render_for(self, actor: Any) -> str:
        template = Template("{% load patient_tags %}{% patient_tags patient %}")
        return template.render(
            Context({"patient": self.patient, "user": actor, "request": template_request(actor)})
        )

    def test_patient_tags_inclusion_tag_hides_restricted_metadata(self) -> None:
        rendered = self.render_for(self.outsider)

        self.assertIn(self.public_tag.name, rendered)
        self.assertNotIn(self.restricted_tag.name, rendered)
        self.assertNotIn(self.restricted_tag.color, rendered)

    def test_patient_tags_inclusion_tag_shows_team_metadata_to_member(self) -> None:
        rendered = self.render_for(self.member)

        self.assertIn(self.restricted_tag.name, rendered)
