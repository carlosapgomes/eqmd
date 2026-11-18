"""Content-versioned URLs keep cached selector code compatible with markup."""

import re
from html import unescape
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.template import Context, Template
from django.test import SimpleTestCase


class VersionedStaticTests(SimpleTestCase):
    """Versions follow the built content, rather than browser visit order."""

    def render_asset(self) -> str:
        """Render the same tag used by the filter pages."""
        return unescape(
            Template(
                "{% load static_assets %}{% versioned_static 'js/tag-selector.js' %}"
            ).render(Context())
        )

    def test_unchanged_content_keeps_the_same_version(self) -> None:
        with TemporaryDirectory() as directory:
            asset = Path(directory) / "selector.js"
            asset.write_text("current selector")
            with patch(
                "apps.core.templatetags.static_assets.finders.find",
                return_value=str(asset),
            ):
                first = self.render_asset()
                self.assertEqual(first, self.render_asset())
                self.assertTrue(parse_qs(urlsplit(first).query)["v"])

    def test_changed_content_invalidates_the_legacy_cache_key(self) -> None:
        with TemporaryDirectory() as directory:
            asset = Path(directory) / "selector.js"
            asset.write_text("legacy")
            with patch(
                "apps.core.templatetags.static_assets.finders.find",
                return_value=str(asset),
            ):
                before = self.render_asset()
                asset.write_text("current panel-aware selector")
                after = self.render_asset()
                self.assertNotEqual(before, after)
                self.assertEqual(urlsplit(before).path, urlsplit(after).path)

    def test_existing_storage_query_is_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            asset = Path(directory) / "selector.js"
            asset.write_text("selector")
            with (
                patch(
                    "apps.core.templatetags.static_assets.finders.find",
                    return_value=str(asset),
                ),
                patch(
                    "apps.core.templatetags.static_assets.static",
                    return_value="/static/selector.js?existing=1",
                ),
            ):
                url = self.render_asset()
                self.assertEqual(parse_qs(urlsplit(url).query)["existing"], ["1"])
                self.assertIn("v", parse_qs(urlsplit(url).query))

    def test_base_bundle_version_follows_built_content(self) -> None:
        with TemporaryDirectory() as directory:
            asset = Path(directory) / "main-bundle.js"
            asset.write_text("previous global loader")
            with patch(
                "apps.core.templatetags.static_assets.finders.find",
                return_value=str(asset),
            ):
                before = Template("{% extends 'base.html' %}").render(Context())
                asset.write_text("corrected navigation listener")
                after = Template("{% extends 'base.html' %}").render(Context())
        pattern = r'src="(/static/main-bundle.js[^"]*)"'
        before_urls = re.findall(pattern, before)
        after_urls = re.findall(pattern, after)
        self.assertEqual(len(before_urls), 1)
        self.assertEqual(len(after_urls), 1)
        self.assertIn("v", parse_qs(urlsplit(before_urls[0]).query))
        self.assertNotEqual(before_urls, after_urls)

    def test_missing_asset_preserves_storage_url(self) -> None:
        with (
            patch(
                "apps.core.templatetags.static_assets.finders.find", return_value=None
            ),
            patch(
                "apps.core.templatetags.static_assets.staticfiles_storage.path",
                side_effect=NotImplementedError,
            ),
        ):
            self.assertEqual(self.render_asset(), "/static/js/tag-selector.js")
