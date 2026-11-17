"""Render the actual shared controls, including developer-comment boundaries."""

import re
from pathlib import Path

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class TagFilterRenderingTests(SimpleTestCase):
    """First-load layout must not depend on another page being visited."""

    def render_filters(self, template: str, **extra: object) -> str:
        """Render empty controls without shared database or clinical fixtures."""
        return render_to_string(
            template,
            {
                "available_tags": [],
                "selected_tags": [],
                "selected_tag_ids": [],
                "available_tag_ids": [],
                "tag_filter_mode": "any",
                "discovery_selection": {"mode": "any", "is_manual": False},
                **extra,
            },
        )

    def test_report_catalogue_and_creation_never_render_comments(self) -> None:
        for creation in (False, True):
            with self.subTest(creation=creation):
                markup = self.render_filters(
                    "components/_report_template_filters.html",
                    creation_selector=creation,
                )
                self.assertNotIn("{#", markup)
                self.assertNotIn("#}", markup)
                self.assertNotIn("Catalogue branch:", markup)
                self.assertNotIn("Native historical control", markup)
                self.assertEqual(markup.count("<div"), markup.count("</div>"))

    def test_result_panel_is_inside_the_input_anchor_on_both_surfaces(self) -> None:
        for template in (
            "components/_tag_selector.html",
            "components/_report_template_tag_selector.html",
        ):
            with self.subTest(template=template):
                markup = self.render_filters(template)
                anchor = re.search(
                    r"<div[^>]*data-tag-search-anchor[^>]*>(.*?)</div>",
                    markup,
                    flags=re.DOTALL,
                )
                if anchor is None:
                    self.fail("results need an input-sized anchor")
                self.assertIn("data-tag-search", anchor.group(1))
                self.assertIn("data-tag-panel", anchor.group(1))
                self.assertNotIn("data-tag-chips", anchor.group(1))
                self.assertNotIn("data-tag-historical", anchor.group(1))

    def test_every_filter_host_uses_versioned_selector_assets(self) -> None:
        root = Path(__file__).resolve().parents[3]
        for filename in (
            "apps/patients/templates/patients/patient_list.html",
            "apps/patients/templates/patients/ward_patient_map.html",
            "apps/reports/templates/reports/reporttemplate_list.html",
            "apps/reports/templates/reports/report_create_form.html",
        ):
            with self.subTest(filename=filename):
                source = (root / filename).read_text()
                self.assertIn("{% versioned_static 'js/tag-selector.js' %}", source)
        self.assertIn(
            "{% versioned_static 'main.css' %}",
            (root / "templates/base.html").read_text(),
        )
