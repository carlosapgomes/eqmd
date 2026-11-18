"""RTTE-S1: existing single-field POST and bound error-state preservation."""

from apps.reports.models import ReportTemplate
from apps.reports.tests.tag_fixtures import persisted_tag_ids
from apps.reports.tests.template_tag_editor_fixtures import (
    EditorControls,
    TemplateTagEditorFixture,
)


class TemplateTagEditorSubmissionTests(TemplateTagEditorFixture):
    def test_invalid_field_keeps_changed_or_empty_native_selection_without_save(
        self,
    ) -> None:
        for tags in ([self.principal_tag.pk], []):
            with self.subTest(tags=tags):
                before = self.invariant_snapshot()
                original = persisted_tag_ids(self.model)
                history = self.model.history.count()
                response = self.client.post(
                    self._update_url(self.model),
                    self._update_payload(
                        self.model,
                        tags,
                        name="RTTE Draft",
                        markdown_body="{{forbidden_editor_placeholder}}",
                        is_active=False,
                        is_public=True,
                    ),
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(
                    EditorControls(response.content.decode()).selected,
                    list(map(str, tags)),
                )
                self.assertEqual(response.context["form"]["name"].value(), "RTTE Draft")
                self.assertEqual(
                    response.context["form"]["markdown_body"].value(),
                    "{{forbidden_editor_placeholder}}",
                )
                self.assertEqual(self.invariant_snapshot(), before)
                self.assertEqual(persisted_tag_ids(self.model), original)
                self.assertEqual(self.model.history.count(), history)

    def test_create_multiple_then_empty_and_no_duplicate_ids(self) -> None:
        before = self.invariant_snapshot()
        response = self.client.post(
            self._create_url(),
            self._create_payload(
                [self.public_tag.pk, self.public_tag.pk, self.restricted_a.pk],
                name="RTTE Criado",
            ),
        )
        self.assertEqual(response.status_code, 302)
        model = ReportTemplate.objects.get(name="RTTE Criado")
        self.assertEqual(
            persisted_tag_ids(model), {self.public_tag.pk, self.restricted_a.pk}
        )
        response = self.client.post(
            self._update_url(model), self._update_payload(model, [])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(model), set())
        self.assertEqual(self.invariant_snapshot(), before)

    def test_empty_submission_preserves_protected_links_and_audits_edit(self) -> None:
        before = self.invariant_snapshot()
        history = self.model.history.count()
        response = self.client.post(
            self._update_url(self.model), self._update_payload(self.model, [])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(self.model), {self.restricted_b.pk})
        self.assertGreater(self.model.history.count(), history)
        self.assertEqual(
            EditorControls(
                self.client.get(self._update_url(self.model)).content.decode()
            ).selected,
            [],
        )
        self.assertEqual(self.invariant_snapshot(), before)

    def test_forged_and_revoked_ids_never_become_client_options_or_save(self) -> None:
        for tag in (self.restricted_b, self.restricted_a):
            with self.subTest(tag=tag.pk):
                if tag.pk == self.restricted_a.pk:
                    self.creator.user_specialties.filter(specialty=self.team_a).update(
                        is_active=False
                    )
                    profile = self.creator.profile
                    profile.current_specialty = None
                    profile.save(update_fields=["current_specialty"])
                before = self.invariant_snapshot()
                original = persisted_tag_ids(self.model)
                history = self.model.history.count()
                response = self.client.post(
                    self._update_url(self.model),
                    self._update_payload(
                        self.model,
                        [tag.pk],
                        name="RTTE Must Not Save",
                    ),
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("tag_ids", response.context["form"].errors)
                self.assertNotIn(
                    str(tag.pk), EditorControls(response.content.decode()).selected
                )
                self.assertNotContains(response, tag.name)
                self.assertEqual(persisted_tag_ids(self.model), original)
                self.assertEqual(self.model.history.count(), history)
                self.assertEqual(self.invariant_snapshot(), before)

    def test_missing_marker_is_still_legacy_not_empty(self) -> None:
        original = persisted_tag_ids(self.model)
        payload = self._update_payload(self.model, [])
        payload.pop("tags_present")
        response = self.client.post(self._update_url(self.model), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(persisted_tag_ids(self.model), original)
