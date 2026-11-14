"""S1 R1-R3/R5: report template tag classification, authority and display."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.reports.models import ReportTemplate
from apps.reports.tests.tag_fixtures import (
    TemplateTagFixturesMixin,
    make_template,
    persisted_tag_ids,
)

BODY = "Paciente: {{patient_name}}"
GENERIC_TAG_MESSAGE = "One or more selected tags are invalid."


class TemplateTagCreateTests(TemplateTagFixturesMixin, TestCase):
    """R1: optional multiple classification on creation."""

    def test_create_with_two_authorized_tags_persists_both(self) -> None:
        self.client.force_login(self.creator)
        response = self.client.post(
            self._create_url(),
            self._create_payload([self.public_tag.pk, self.restricted_a.pk]),
        )
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(
            persisted_tag_ids(template),
            {self.public_tag.pk, self.restricted_a.pk},
        )

    def test_create_with_duplicate_ids_stores_no_duplicates(self) -> None:
        self.client.force_login(self.creator)
        response = self.client.post(
            self._create_url(),
            self._create_payload(
                [self.public_tag.pk, self.public_tag.pk, self.restricted_a.pk]
            ),
        )
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(
            persisted_tag_ids(template),
            {self.public_tag.pk, self.restricted_a.pk},
        )

    def test_create_with_empty_selection_stays_untagged(self) -> None:
        self.client.force_login(self.creator)
        response = self.client.post(self._create_url(), self._create_payload([]))
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(persisted_tag_ids(template), set())

    def test_create_without_marker_stays_untagged(self) -> None:
        self.client.force_login(self.creator)
        payload = self._create_payload([self.public_tag.pk])
        del payload["tags_present"]
        del payload["tag_ids"]
        response = self.client.post(self._create_url(), payload)
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(persisted_tag_ids(template), set())


class TemplateTagUpdateTests(TemplateTagFixturesMixin, TestCase):
    """R1/R3: revision, explicit clear and legacy omission."""

    def test_update_replaces_authorized_selection(self) -> None:
        template = make_template(self.creator, "S1 Editable")
        template.tags.add(self.public_tag, self.restricted_a)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._update_payload(template, [self.principal_tag.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(template), {self.principal_tag.pk})

    def test_explicit_empty_selection_clears_editable_links(self) -> None:
        template = make_template(self.creator, "S1 Clearable")
        template.tags.add(self.public_tag, self.restricted_a)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template), self._update_payload(template, [])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(template), set())

    def test_legacy_update_without_marker_preserves_links(self) -> None:
        template = make_template(self.creator, "S1 Legacy")
        template.tags.add(self.public_tag, self.restricted_a)
        self.client.force_login(self.creator)
        payload = self._update_payload(template, [])
        del payload["tags_present"]
        del payload["tag_ids"]
        payload["name"] = "S1 Legacy Renamed"
        response = self.client.post(self._update_url(template), payload)
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Legacy Renamed")
        self.assertEqual(
            persisted_tag_ids(template),
            {self.public_tag.pk, self.restricted_a.pk},
        )


class TemplateTagRetentionTests(TemplateTagFixturesMixin, TestCase):
    """R3: protected and historical links survive or are removed safely."""

    def test_protected_link_is_preserved_and_not_exposed_in_editor(
        self,
    ) -> None:
        template = make_template(self.creator, "S1 Protected")
        template.tags.add(self.restricted_b)
        self.client.force_login(self.creator)
        response = self.client.get(self._update_url(template))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "S1 Restrita B")
        self.assertNotContains(response, f'value="{self.restricted_b.pk}"')

        response = self.client.post(
            self._update_url(template),
            self._update_payload(
                template,
                [self.public_tag.pk],
                name="S1 Protected Renamed",
                markdown_body="Alterado: {{patient_name}}",
            ),
        )
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Protected Renamed")
        self.assertEqual(
            persisted_tag_ids(template),
            {self.restricted_b.pk, self.public_tag.pk},
        )

    def test_explicit_clear_preserves_protected_link(self) -> None:
        template = make_template(self.creator, "S1 Protected Clear")
        template.tags.add(self.restricted_b, self.public_tag)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template), self._update_payload(template, [])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(template), {self.restricted_b.pk})

    def test_inactive_link_can_be_retained(self) -> None:
        template = make_template(self.creator, "S1 Inactive Kept")
        template.tags.add(self.inactive_a)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._update_payload(template, [self.inactive_a.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(template), {self.inactive_a.pk})

    def test_archived_link_can_be_removed(self) -> None:
        template = make_template(self.creator, "S1 Archived Removed")
        template.tags.add(self.archived_a)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._update_payload(template, [self.public_tag.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})

    def test_inactive_tag_cannot_be_newly_assigned(self) -> None:
        self.client.force_login(self.creator)
        response = self.client.post(
            self._create_url(), self._create_payload([self.inactive_a.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReportTemplate.objects.filter(name="S1 New").exists())
        self.assertContains(response, GENERIC_TAG_MESSAGE)


class TemplateTagAuthorityTests(TemplateTagFixturesMixin, TestCase):
    """R2: per-tag authority, lifecycle and template gates on writes."""

    def test_forged_restricted_tag_gets_generic_error_and_saves_nothing(
        self,
    ) -> None:
        self.client.force_login(self.creator)
        response = self.client.post(
            self._create_url(), self._create_payload([self.restricted_b.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReportTemplate.objects.filter(name="S1 New").exists())
        self.assertContains(response, GENERIC_TAG_MESSAGE)
        self.assertNotContains(response, "S1 Restrita B")
        self.assertNotContains(response, "S1TB")

    def test_unknown_and_forged_ids_share_the_same_generic_error(self) -> None:
        self.client.force_login(self.creator)
        forged = self.client.post(
            self._create_url(), self._create_payload([self.restricted_b.pk])
        )
        unknown = self.client.post(
            self._create_url(),
            self._create_payload([999999]),
            name="S1 Unknown",
        )
        forged_errors = forged.context["form"].errors["tag_ids"]
        unknown_errors = unknown.context["form"].errors["tag_ids"]
        self.assertEqual(list(forged_errors), list(unknown_errors))
        self.assertEqual(list(forged_errors), [GENERIC_TAG_MESSAGE])

    def test_principal_tag_requires_team_membership(self) -> None:
        self.client.force_login(self.outsider)
        response = self.client.post(
            self._create_url(),
            self._create_payload([self.principal_tag.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReportTemplate.objects.filter(name="S1 New").exists())

        self.client.force_login(self.creator)
        response = self.client.post(
            self._create_url(),
            self._create_payload([self.principal_tag.pk]),
        )
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(persisted_tag_ids(template), {self.principal_tag.pk})

    def test_plain_staff_status_does_not_override_tag_authority(self) -> None:
        self.client.force_login(self.staff_plain)
        response = self.client.post(
            self._create_url(), self._create_payload([self.restricted_a.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReportTemplate.objects.filter(name="S1 New").exists())

    def test_catalogue_administrator_may_assign_without_membership(self) -> None:
        self.client.force_login(self.catalogue_admin)
        response = self.client.post(
            self._create_url(), self._create_payload([self.restricted_b.pk])
        )
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(persisted_tag_ids(template), {self.restricted_b.pk})

    def test_superuser_may_assign_without_membership(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.post(
            self._create_url(), self._create_payload([self.restricted_b.pk])
        )
        self.assertEqual(response.status_code, 302)
        template = ReportTemplate.objects.get(name="S1 New")
        self.assertEqual(persisted_tag_ids(template), {self.restricted_b.pk})

    def test_non_creator_non_admin_cannot_edit_tags(self) -> None:
        template = make_template(self.creator, "S1 Owned")
        template.tags.add(self.public_tag)
        self.client.force_login(self.other_doctor)
        response = self.client.post(
            self._update_url(template),
            self._update_payload(
                template,
                [self.restricted_a.pk],
                name="S1 Hijacked",
            ),
        )
        self.assertEqual(response.status_code, 403)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Owned")
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})

    def test_invalid_tag_update_is_atomic(self) -> None:
        template = make_template(self.creator, "S1 Atomic")
        template.tags.add(self.public_tag)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._update_payload(
                template,
                [self.public_tag.pk, self.restricted_b.pk],
                name="S1 Atomic Renamed",
            ),
        )
        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Atomic")
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})

    def test_stale_authorization_is_revalidated_by_the_service(self) -> None:
        from apps.reports.services.template_tags import save_template_with_tags

        template = make_template(self.creator, "S1 Stale")
        template.tags.add(self.public_tag)
        membership = self.creator.user_specialties.get(specialty=self.team_a)
        membership.is_active = False
        membership.save(update_fields=["is_active"])

        candidate = ReportTemplate.objects.get(pk=template.pk)
        candidate.name = "S1 Stale Renamed"
        with self.assertRaises(ValidationError) as context:
            save_template_with_tags(
                actor=self.creator,
                template=candidate,
                submitted_tag_ids=frozenset({self.restricted_a.pk}),
            )
        self.assertEqual(list(context.exception.messages), [GENERIC_TAG_MESSAGE])
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Stale")
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})

    def test_stale_existing_protected_tag_submission_is_rejected(
        self,
    ) -> None:
        from apps.reports.services.template_tags import save_template_with_tags

        template = make_template(self.creator, "S1 Stale Existing")
        template.tags.add(self.restricted_a)
        history_count = template.history.count()
        membership = self.creator.user_specialties.get(specialty=self.team_a)
        membership.is_active = False
        membership.save(update_fields=["is_active"])

        candidate = ReportTemplate.objects.get(pk=template.pk)
        candidate.name = "S1 Stale Existing Renamed"
        candidate.markdown_body = "Alterado: {{patient_name}}"
        with self.assertRaises(ValidationError) as context:
            save_template_with_tags(
                actor=self.creator,
                template=candidate,
                submitted_tag_ids=frozenset({self.restricted_a.pk}),
            )
        self.assertEqual(list(context.exception.messages), [GENERIC_TAG_MESSAGE])
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Stale Existing")
        self.assertEqual(template.markdown_body, BODY)
        self.assertEqual(persisted_tag_ids(template), {self.restricted_a.pk})
        self.assertEqual(template.history.count(), history_count)

    def test_deactivated_team_denies_new_assignment(self) -> None:
        from apps.reports.services.template_tags import save_template_with_tags

        template = make_template(self.creator, "S1 Inactive Team")
        template.tags.add(self.public_tag)
        history_count = template.history.count()
        self.team_a.is_active = False
        self.team_a.save(update_fields=["is_active"])

        candidate = ReportTemplate.objects.get(pk=template.pk)
        candidate.name = "S1 Inactive Team Renamed"
        with self.assertRaises(ValidationError) as context:
            save_template_with_tags(
                actor=self.creator,
                template=candidate,
                submitted_tag_ids=frozenset({self.restricted_a.pk}),
            )
        self.assertEqual(list(context.exception.messages), [GENERIC_TAG_MESSAGE])
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Inactive Team")
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})
        self.assertEqual(template.history.count(), history_count)


class TemplateTagDisplayTests(TemplateTagFixturesMixin, TestCase):
    """R5: only currently readable badges and editor choices are shown."""

    def test_editor_choices_follow_readability(self) -> None:
        self.client.force_login(self.creator)
        response = self.client.get(self._create_url())
        self.assertContains(response, "S1 Restrita A")
        self.assertNotContains(response, "S1 Restrita B")

        self.client.force_login(self.outsider)
        response = self.client.get(self._create_url())
        self.assertContains(response, "S1 Restrita B")
        self.assertNotContains(response, "S1 Restrita A")

    def test_historical_choice_is_labelled_with_lifecycle_state(self) -> None:
        template = make_template(self.creator, "S1 Historical Choice")
        template.tags.add(self.inactive_a)
        self.client.force_login(self.creator)
        response = self.client.get(self._update_url(template))
        self.assertContains(response, "S1 Inativa A")
        self.assertContains(response, "Inativa")

    def test_list_badges_follow_current_membership(self) -> None:
        template = make_template(self.creator, "S1 Listed", is_public=True)
        template.tags.add(self.restricted_a, self.public_tag)

        self.client.force_login(self.creator)
        response = self.client.get(reverse("reports:template_list"))
        self.assertContains(response, "S1 Restrita A")
        self.assertContains(response, "S1 Publica")

        self.client.force_login(self.outsider)
        response = self.client.get(reverse("reports:template_list"))
        self.assertContains(response, "S1 Listed")
        self.assertContains(response, "S1 Publica")
        self.assertNotContains(response, "S1 Restrita A")

        membership = self.creator.user_specialties.get(specialty=self.team_a)
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        self.client.force_login(self.creator)
        response = self.client.get(reverse("reports:template_list"))
        self.assertContains(response, "S1 Listed")
        self.assertNotContains(response, "S1 Restrita A")
