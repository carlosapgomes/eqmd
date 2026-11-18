"""RTTE-S1: shared enhanced editor markup and requester-safe field choices."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.urls import reverse

from apps.patients.models import AllowedTag
from apps.reports.tests.template_tag_editor_fixtures import (
    EditorControls,
    TemplateTagEditorFixture,
)


class TemplateTagEditorMarkupTests(TemplateTagEditorFixture):
    def test_both_editors_have_one_enabled_field_and_progressive_controls(self) -> None:
        for url in (self._create_url(), self._update_url(self.model)):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                body = response.content.decode()
                fields = EditorControls(body)
                self.assertEqual(len(fields.selects), 1)
                self.assertNotIn("disabled", fields.selects[0])
                self.assertIn("multiple", fields.selects[0])
                self.assertEqual(body.count("data-template-tag-editor"), 1)
                self.assertIn("data-editor-search", body)
                self.assertIn("data-editor-chips", body)
                self.assertIn("data-editor-native", body)
                self.assertIn("Ctrl", body)
                self.assertIn("Cmd", body)
                self.assertEqual(
                    len(
                        [
                            i
                            for i in fields.inputs
                            if i.get("name") == "tags_present" and i.get("value") == "1"
                        ]
                    ),
                    1,
                )
                self.assertFalse(
                    [i for i in fields.inputs if i.get("name") == "tag_ids"]
                )

    def test_create_has_no_automatic_classification_despite_real_defaults(self) -> None:
        response = self.client.get(self._create_url())
        self.assertEqual(EditorControls(response.content.decode()).selected, [])

    def test_update_seeds_only_editable_active_and_historical_values(self) -> None:
        response = self.client.get(self._update_url(self.model))
        self.assertEqual(
            set(EditorControls(response.content.decode()).selected),
            {
                str(self.public_tag.pk),
                str(self.restricted_a.pk),
                str(self.inactive_a.pk),
                str(self.archived_a.pk),
            },
        )
        self.assertContains(response, "Inativa")
        self.assertContains(response, "Arquivada")
        self.assertNotContains(response, self.restricted_b.name)
        self.assertNotContains(response, self.foreign_principal.name)

    def test_labels_escape_and_no_shared_discovery_hooks_or_transport(self) -> None:
        response = self.client.get(self._create_url())
        self.assertContains(response, "&lt;b&gt;seguro&lt;/b&gt;")
        self.assertNotContains(response, "<b>seguro</b>")
        self.assertNotContains(response, "data-tag-selector")
        self.assertNotContains(response, "data-catalogue-filter-form")
        self.assertNotContains(response, "tag-selector.js")
        self.assertNotContains(response, "report-template-discovery.js")

    def test_only_editor_pages_load_the_new_asset(self) -> None:
        for url in (self._create_url(), self._update_url(self.model)):
            body = self.client.get(url).content.decode()
            self.assertEqual(
                len(
                    re.findall(
                        r'<script[^>]+src="[^"]*report-template-tag-editor.js[^"]*"[^>]*defer',
                        body,
                    )
                ),
                1,
            )
        self.assertNotContains(
            self.client.get(reverse("reports:template_list")),
            "report-template-tag-editor.js",
        )

    def test_no_authorized_choices_has_generic_explanation(self) -> None:
        AllowedTag.all_objects.filter(
            pk__in=[self.public_tag.pk, self.long_tag.pk]
        ).update(is_active=False)
        self.client.force_login(self.other_doctor)
        response = self.client.get(self._create_url())
        self.assertEqual(list(response.context["form"].fields["tag_ids"].choices), [])
        self.assertContains(response, "Nenhuma tag disponível para seleção.")
        self.assertNotContains(response, self.restricted_b.name)

    def test_ownership_and_create_authority_stay_unchanged(self) -> None:
        self.client.force_login(self.other_doctor)
        self.assertEqual(self.client.get(self._update_url(self.model)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self._create_url()).status_code, 403)

    @skipUnless(shutil.which("node"), "node runtime unavailable; run host harness")
    def test_real_editor_source_harness(self) -> None:
        harness = Path(__file__).with_name("template_tag_editor_harness.cjs")
        result = subprocess.run(
            [str(shutil.which("node")), str(harness)],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["failed"], [])
