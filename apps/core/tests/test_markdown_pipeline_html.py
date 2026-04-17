"""
Unit tests for the HTML renderer and sanitizer in the markdown pipeline.

TDD – written FIRST (RED phase). These tests define the contract
that the HTML renderer, sanitizer, and template filter must satisfy.

Required tests (minimum):
- test_html_renderer_preserves_nested_lists
- test_html_renderer_preserves_inline_semantics
- test_html_renderer_sanitizes_unsafe_html

Hardening:
- block javascript: in href
- remove dangerous on* event attributes
- strip <script>/<style>
- deterministic output for same input
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.markdown_pipeline import parse_markdown
from apps.core.services.markdown_pipeline.html_renderer import render_html
from apps.core.services.markdown_pipeline.sanitizer import sanitize_html

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tests/fixtures/markdown/easymd_v1"
)


class HTMLRendererNestedListsTest(SimpleTestCase):
    """test_html_renderer_preserves_nested_lists"""

    def test_ordered_list_with_nesting(self):
        md = (
            "1. First item\n"
            "2. Second item\n"
            "   1. Nested item 2a\n"
            "   2. Nested item 2b\n"
            "3. Third item\n"
        )
        html = render_html(md)
        # Outer ordered list
        self.assertIn("<ol>", html)
        self.assertIn("</ol>", html)
        # Nested ordered list inside second item
        self.assertIn("<li>Second item<ol>", html)
        self.assertIn("<li>Nested item 2a</li>", html)
        self.assertIn("<li>Nested item 2b</li>", html)
        self.assertIn("</ol></li>", html)

    def test_unordered_list_with_deep_nesting(self):
        md = (
            "- Alpha\n"
            "  - Sub-alpha\n"
            "    - Deep nesting\n"
            "  - Another sub\n"
            "- Beta\n"
        )
        html = render_html(md)
        self.assertIn("<ul>", html)
        self.assertIn("<li>Alpha<ul>", html)
        self.assertIn("<li>Sub-alpha<ul>", html)
        self.assertIn("Deep nesting", html)
        self.assertIn("Another sub", html)
        self.assertIn("Beta", html)

    def test_mixed_ordered_unordered_nesting(self):
        md = (
            "1. Step one\n"
            "   - Detail A\n"
            "   - Detail B\n"
            "2. Step two\n"
        )
        html = render_html(md)
        self.assertIn("<ol>", html)
        self.assertIn("<li>Step one<ul>", html)
        self.assertIn("<li>Detail A</li>", html)
        self.assertIn("<li>Detail B</li>", html)
        self.assertIn("</ul></li>", html)

    def test_nested_list_from_fixture(self):
        fixture_path = FIXTURES_DIR / "nested_lists.md"
        md = fixture_path.read_text()
        html = render_html(md)
        # Should contain both <ol> and <ul>
        self.assertIn("<ol>", html)
        self.assertIn("<ul>", html)
        # Should preserve deep nesting text
        self.assertIn("Deep nesting", html)
        self.assertIn("Nested item 2a", html)

    def test_task_list_renders_checkboxes(self):
        md = (
            "- [ ] Pending task\n"
            "- [x] Done task\n"
        )
        html = render_html(md)
        self.assertIn("Pending task", html)
        self.assertIn("Done task", html)
        # Task list checkboxes should appear
        self.assertIn('type="checkbox"', html)
        self.assertIn("checked", html)


class HTMLRendererInlineSemanticsTest(SimpleTestCase):
    """test_html_renderer_preserves_inline_semantics"""

    def test_strong_emphasis_strike(self):
        md = "This is **bold** and *italic* and ~~strike~~ text."
        html = render_html(md)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)
        self.assertIn("<del>strike</del>", html)

    def test_inline_code(self):
        md = "Use the `parse()` function."
        html = render_html(md)
        self.assertIn("<code>parse()</code>", html)

    def test_link(self):
        md = "Visit [example](https://example.com) for info."
        html = render_html(md)
        self.assertIn('<a href="https://example.com"', html)
        self.assertIn(">example</a>", html)

    def test_link_with_title(self):
        md = '[link](https://example.com "Title")'
        html = render_html(md)
        self.assertIn('https://example.com', html)
        self.assertIn(">link</a>", html)

    def test_heading_levels(self):
        for level in range(1, 7):
            prefix = "#" * level
            md = f"{prefix} Heading {level}"
            html = render_html(md)
            tag = f"h{level}"
            self.assertIn(
                f"<{tag}>Heading {level}</{tag}>", html,
                f"Expected <{tag}> for level {level}",
            )

    def test_blockquote(self):
        md = "> This is a quote\n> With two lines"
        html = render_html(md)
        self.assertIn("<blockquote>", html)
        self.assertIn("This is a quote", html)

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        html = render_html(md)
        self.assertIn("<pre><code", html)
        self.assertIn("language-python", html)
        self.assertIn("print", html)

    def test_table(self):
        md = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| 1 | 2 |\n"
        )
        html = render_html(md)
        self.assertIn("<table>", html)
        self.assertIn("<th>", html)
        self.assertIn("<td>", html)

    def test_thematic_break(self):
        md = "Above\n\n---\n\nBelow"
        html = render_html(md)
        self.assertIn("<hr>", html)

    def test_hard_break(self):
        md = "Line one  \nLine two"
        html = render_html(md)
        self.assertIn("<br>", html)

    def test_inline_formatting_fixture(self):
        fixture_path = FIXTURES_DIR / "inline_formatting.md"
        md = fixture_path.read_text()
        html = render_html(md)
        self.assertIn("<strong>", html)
        self.assertIn("<em>", html)
        self.assertIn("<del>", html)
        self.assertIn("<code>", html)
        self.assertIn("<hr>", html)


class HTMLRendererSanitizationTest(SimpleTestCase):
    """test_html_renderer_sanitizes_unsafe_html"""

    def test_script_tag_stripped(self):
        md = 'Text before <script>alert("xss")</script> text after'
        html = render_html(md)
        # The <script> tag must not appear as a real HTML tag
        # (escaped &lt;script&gt; is safe — renders as visible text)
        self.assertNotIn("<script>", html)
        self.assertNotIn("</script>", html)

    def test_style_tag_stripped(self):
        md = "<style>body{display:none}</style>visible text"
        html = render_html(md)
        self.assertNotIn("<style", html)
        self.assertNotIn("</style>", html)

    def test_javascript_href_blocked(self):
        md = '[click](javascript:alert("xss"))'
        html = render_html(md)
        self.assertNotIn("javascript:", html)

    def test_onclick_attribute_removed(self):
        """Inline HTML with event handlers must be sanitized."""
        html = sanitize_html('<p onclick="alert(1)">text</p>')
        self.assertNotIn("onclick", html)
        self.assertIn("text", html)

    def test_onerror_attribute_removed(self):
        html = sanitize_html('<img onerror="alert(1)" src="x" />')
        self.assertNotIn("onerror", html)

    def test_data_href_blocked(self):
        md = '[click](data:text/html,<script>alert(1)</script>)'
        html = render_html(md)
        self.assertNotIn("data:", html)

    def test_safe_attributes_preserved(self):
        """href on <a> and title should be preserved when safe."""
        html = sanitize_html(
            '<a href="https://example.com" title="Example">link</a>'
        )
        self.assertIn('href="https://example.com"', html)
        self.assertIn('title="Example"', html)

    def test_safe_html_preserved(self):
        """Common safe tags should pass through."""
        html = sanitize_html(
            "<p>Hello <strong>world</strong> <em>emphasis</em></p>"
        )
        self.assertIn("<p>", html)
        self.assertIn("<strong>", html)
        self.assertIn("<em>", html)


class HTMLRendererDeterminismTest(SimpleTestCase):
    """Same input must always produce same output."""

    def test_deterministic_output(self):
        md = "## Hello\n\n- item 1\n- item 2\n"
        html1 = render_html(md)
        html2 = render_html(md)
        self.assertEqual(html1, html2)

    def test_deterministic_complex(self):
        fixture_path = FIXTURES_DIR / "mixed_clinical_note.md"
        md = fixture_path.read_text()
        html1 = render_html(md)
        html2 = render_html(md)
        self.assertEqual(html1, html2)


class HTMLRendererMixedFixtureTest(SimpleTestCase):
    """Integration-style tests using the full fixture corpus."""

    def test_mixed_clinical_note_fixture(self):
        fixture_path = FIXTURES_DIR / "mixed_clinical_note.md"
        meta_path = FIXTURES_DIR / "mixed_clinical_note.meta.json"
        md = fixture_path.read_text()
        html = render_html(md)

        # Verify key semantic elements
        self.assertIn("<h1>", html)  # Title heading
        self.assertIn("<h2>", html)
        self.assertIn("<h3>", html)
        self.assertIn("<strong>", html)
        self.assertIn("<blockquote>", html)
        self.assertIn("<pre><code", html)
        self.assertIn("<table>", html)
        self.assertIn("<hr>", html)
        self.assertIn('type="checkbox"', html)

    def test_blockquote_code_fixture(self):
        fixture_path = FIXTURES_DIR / "blockquote_code.md"
        md = fixture_path.read_text()
        html = render_html(md)
        self.assertIn("<blockquote>", html)
        self.assertIn("<pre><code", html)

    def test_tables_links_fixture(self):
        fixture_path = FIXTURES_DIR / "tables_links.md"
        md = fixture_path.read_text()
        html = render_html(md)
        self.assertIn("<table>", html)
        self.assertIn("<a ", html)


class RenderHTMLPublicAPITest(SimpleTestCase):
    """Test the public render_html convenience function."""

    def test_render_empty_string(self):
        html = render_html("")
        self.assertEqual(html, "")

    def test_render_plain_text(self):
        html = render_html("Hello world")
        self.assertIn("Hello world", html)

    def test_render_with_profile(self):
        """render_html should accept profile kwarg."""
        html = render_html("**bold**", profile="easymd_v1")
        self.assertIn("<strong>bold</strong>", html)
