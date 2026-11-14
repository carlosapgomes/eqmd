"""S1 R4/R5: template tag audit history and safe admin history display."""

from __future__ import annotations

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import EqmdCustomUser, MedicalSpecialty
from apps.events.models import Event, TagAddedEvent, TagRemovedEvent
from apps.patients.models import AllowedTag
from apps.reports.admin import ReportTemplateAdmin
from apps.reports.models import ReportTemplate
from apps.reports.tests.tag_fixtures import (
    join_team,
    make_specialty,
    make_tag,
    make_template,
    make_user,
    persisted_tag_ids,
)

BODY = "Paciente: {{patient_name}}"


def history_tag_snapshots(template: ReportTemplate) -> list[set[int]]:
    """Return tag-id snapshots from each template history record, oldest first."""
    snapshots: list[set[int]] = []
    for record in template.history.order_by("history_date", "history_id"):
        snapshots.append({row.allowedtag_id for row in record.tags.all()})
    return snapshots


class TemplateTagHistoryTests(TestCase):
    """R4: attributable, reconstructible, atomic tag history."""

    team: MedicalSpecialty
    creator: EqmdCustomUser
    public_tag: AllowedTag
    restricted: AllowedTag
    other_tag: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = make_specialty("S1HT")
        cls.creator = make_user("s1-history-creator")
        join_team(cls.creator, cls.team)
        cls.public_tag = make_tag(cls.creator, "S1 Hist Publica")
        cls.restricted = make_tag(
            cls.creator,
            "S1 Hist Restrita",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.other_tag = make_tag(cls.creator, "S1 Hist Outra")

    def _update_url(self, template: ReportTemplate) -> str:
        return reverse("reports:template_update", kwargs={"pk": template.pk})

    def _payload(self, template, tag_ids, **overrides):
        payload = {
            "name": template.name,
            "markdown_body": BODY,
            "is_active": True,
            "is_public": False,
            "tags_present": "1",
            "tag_ids": [str(tag_id) for tag_id in tag_ids],
        }
        payload.update(overrides)
        return payload

    def test_tag_only_edit_is_attributable_in_history(self) -> None:
        template = make_template(self.creator, "S1 Hist")
        template.tags.add(self.public_tag)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._payload(template, [self.public_tag.pk, self.restricted.pk]),
        )
        self.assertEqual(response.status_code, 302)
        latest = template.history.order_by("-history_date", "-history_id").first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.history_user, self.creator)
        self.assertEqual(
            {row.allowedtag_id for row in latest.tags.all()},
            {self.public_tag.pk, self.restricted.pk},
        )

    def test_replacement_delta_is_reconstructible_from_snapshots(self) -> None:
        template = make_template(self.creator, "S1 Hist Delta")
        template.tags.add(self.public_tag)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._payload(template, [self.other_tag.pk]),
        )
        self.assertEqual(response.status_code, 302)
        snapshots = history_tag_snapshots(template)
        self.assertIn({self.public_tag.pk}, snapshots)
        self.assertEqual(snapshots[-1], {self.other_tag.pk})

    def test_noop_tag_save_does_not_invent_a_tag_change(self) -> None:
        template = make_template(self.creator, "S1 Hist Noop")
        template.tags.add(self.public_tag, self.restricted)
        before = history_tag_snapshots(template)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._payload(template, [self.public_tag.pk, self.restricted.pk]),
        )
        self.assertEqual(response.status_code, 302)
        after = history_tag_snapshots(template)
        self.assertTrue(after)
        self.assertEqual(after[-1], before[-1])
        self.assertEqual(
            persisted_tag_ids(template),
            {self.public_tag.pk, self.restricted.pk},
        )

    def test_failed_tag_change_leaves_no_partial_history(self) -> None:
        outsider_tag = make_tag(
            self.creator,
            "S1 Hist Estrangeira",
            specialty=make_specialty("S1HX"),
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        template = make_template(self.creator, "S1 Hist Atomic")
        template.tags.add(self.public_tag)
        history_count = template.history.count()
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._payload(
                template,
                [self.public_tag.pk, outsider_tag.pk],
                name="S1 Hist Atomic Renamed",
            ),
        )
        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Hist Atomic")
        self.assertEqual(template.history.count(), history_count)
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})

    def test_failure_after_persistence_rolls_back_everything(self) -> None:
        from django.apps import apps as django_apps
        from django.db.models.signals import m2m_changed

        from apps.reports.services.template_tags import save_template_with_tags

        template = make_template(self.creator, "S1 Hist Rollback")
        template.tags.add(self.public_tag)
        history_count = template.history.count()
        snapshots_before = history_tag_snapshots(template)
        historical_tags = django_apps.get_model(
            "reports", "historicalreporttemplate_tags"
        )
        historical_tags_count = historical_tags.objects.count()

        def _raise_after_add(
            sender, instance, action, reverse, model, pk_set, **kwargs
        ):
            if action == "post_add":
                raise RuntimeError("injected failure after persistence")

        through = ReportTemplate.tags.through
        m2m_changed.connect(
            _raise_after_add, sender=through, dispatch_uid="s1-test-rollback-failure"
        )
        try:
            candidate = ReportTemplate.objects.get(pk=template.pk)
            candidate.name = "S1 Hist Rollback Renamed"
            candidate.markdown_body = "Alterado: {{patient_name}}"
            with self.assertRaises(RuntimeError):
                save_template_with_tags(
                    actor=self.creator,
                    template=candidate,
                    submitted_tag_ids=frozenset(
                        {self.public_tag.pk, self.restricted.pk}
                    ),
                )
        finally:
            m2m_changed.disconnect(
                receiver=_raise_after_add,
                sender=through,
                dispatch_uid="s1-test-rollback-failure",
            )
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Hist Rollback")
        self.assertEqual(template.markdown_body, BODY)
        self.assertEqual(persisted_tag_ids(template), {self.public_tag.pk})
        self.assertEqual(template.history.count(), history_count)
        self.assertEqual(history_tag_snapshots(template), snapshots_before)
        self.assertEqual(historical_tags.objects.count(), historical_tags_count)

    def test_tag_classification_creates_no_patient_events(self) -> None:
        events_before = Event.objects.count()
        added_before = TagAddedEvent.objects.count()
        removed_before = TagRemovedEvent.objects.count()
        template = make_template(self.creator, "S1 Hist No Events")
        template.tags.add(self.public_tag)
        self.client.force_login(self.creator)
        response = self.client.post(
            self._update_url(template),
            self._payload(template, [self.restricted.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Event.objects.count(), events_before)
        self.assertEqual(TagAddedEvent.objects.count(), added_before)
        self.assertEqual(TagRemovedEvent.objects.count(), removed_before)


class TemplateTagAdminHistoryTests(TestCase):
    """R4/R5: admin keeps tag controls absent and history deltas safe."""

    team: MedicalSpecialty
    creator: EqmdCustomUser
    admin_user: EqmdCustomUser
    restricted: AllowedTag
    public_tag: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = make_specialty("S1HA")
        cls.creator = make_user("s1-admin-creator")
        join_team(cls.creator, cls.team)
        cls.admin_user = make_user(
            "s1-admin-user",
            profession_type=None,
            is_staff=True,
            is_superuser=True,
        )
        cls.restricted = make_tag(
            cls.creator,
            "S1 Admin Restrita",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.public_tag = make_tag(cls.creator, "S1 Admin Publica")

    def _change_url(self, template: ReportTemplate) -> str:
        return reverse("admin:reports_reporttemplate_change", args=[template.pk])

    def _history_url(self, template: ReportTemplate) -> str:
        return reverse("admin:reports_reporttemplate_history", args=[template.pk])

    def test_admin_change_form_has_no_tag_controls(self) -> None:
        template = make_template(self.creator, "S1 Admin Form")
        template.tags.add(self.restricted)
        self.client.force_login(self.admin_user)
        response = self.client.get(self._change_url(template))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="tags"')
        self.assertNotContains(response, "S1 Admin Restrita")

    def test_admin_form_fields_exclude_tags(self) -> None:
        from django.test import RequestFactory

        template = make_template(self.creator, "S1 Admin Fields")
        model_admin = ReportTemplateAdmin(ReportTemplate, admin.site)
        request = RequestFactory().get("/admin/reports/reporttemplate/")
        request.user = self.admin_user
        form_class = model_admin.get_form(request, template)
        self.assertNotIn("tags", form_class.base_fields)
        flat_fieldsets = [
            field
            for _title, options in model_admin.fieldsets
            for field in options["fields"]
        ]
        self.assertNotIn("tags", flat_fieldsets)

    def test_admin_history_list_omits_m2m_delta(self) -> None:
        template = make_template(self.creator, "S1 Admin History")
        template.tags.add(self.restricted)
        self.client.force_login(self.admin_user)
        response = self.client.get(self._history_url(template))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "S1 Admin Restrita")

    def test_admin_historical_record_detail_omits_restricted_tags(self) -> None:
        template = make_template(self.creator, "S1 Admin Detail")
        template.tags.add(self.restricted)
        record = template.history.order_by("-history_date", "-history_id").first()
        self.assertIsNotNone(record)
        detail_url = reverse(
            "admin:reports_reporttemplate_simple_history",
            args=[template.pk, record.history_id],
        )
        self.client.force_login(self.admin_user)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "S1 Admin Restrita")
        self.assertNotContains(response, f'value="{self.restricted.pk}"')

    def test_admin_text_save_preserves_links(self) -> None:
        template = make_template(self.creator, "S1 Admin Preserve")
        template.tags.add(self.restricted, self.public_tag)
        self.client.force_login(self.admin_user)
        response = self.client.post(
            self._change_url(template),
            {
                "name": "S1 Admin Preserve Renamed",
                "markdown_body": BODY,
                "is_active": "on",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.name, "S1 Admin Preserve Renamed")
        self.assertEqual(
            persisted_tag_ids(template),
            {self.restricted.pk, self.public_tag.pk},
        )
