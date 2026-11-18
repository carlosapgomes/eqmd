"""Regression coverage for shared document-navigation feedback (RTFA-S1)."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase
from django.urls import reverse

from apps.patients.tests.ward_map_filter_fixtures import MapFilterFixture


class NavigationPageMarkupTests(MapFilterFixture):
    """Actual inherited pages expose one overlay and cache-safe global code."""

    def test_inherited_pages_render_one_overlay(self) -> None:
        urls = [
            reverse("reports:template_list"),
            reverse(
                "reports:report_create",
                kwargs={"patient_id": self.inpatients[0].pk},
            ),
            reverse("patients:patient_list"),
            reverse("patients:patient_map"),
        ]
        before = self.snapshot()
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.count(b'id="pageLoadingOverlay"'), 1)
        self.assertEqual(self.snapshot(), before)

    def test_base_login_renders_one_overlay(self) -> None:
        self.client.logout()
        response = self.client.get(reverse("account_login"))
        self.assertContains(response, 'id="pageLoadingOverlay"', count=1)


class NavigationEventTests(SimpleTestCase):
    """Run the real loader with deterministic event dispatch and timers."""

    @skipUnless(shutil.which("node"), "node runtime unavailable; run host harness")
    def test_navigation_event_harness(self) -> None:
        harness = Path(__file__).with_name("page_navigation_loading_harness.cjs")
        result = subprocess.run(
            [str(shutil.which("node")), str(harness)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["failed"], [])
        self.assertGreaterEqual(len(summary["passed"]), 20)
