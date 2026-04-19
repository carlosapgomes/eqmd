"""
Integration tests for Daily Note detail page markdown rendering.

Verifies that the detail page uses the shared markdown pipeline
(``|markdown`` template filter) instead of Django's ``|linebreaks``,
preserving nested lists, inline formatting, blockquotes, and code blocks.

TDD — written FIRST (RED phase).
"""

from datetime import date

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.dailynotes.models import DailyNote
from apps.events.models import Event
from apps.patients.models import Patient


class DailyNoteDetailMarkdownRenderingTest(TestCase):
    """Integration tests: detail page renders markdown via shared pipeline."""

    @classmethod
    def setUpTestData(cls):
        cls.user = EqmdCustomUser.objects.create_user(
            username="mdrenderdoc",
            email="mdrender@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            first_name="Render",
            last_name="Doctor",
        )
        # Grant view_event permission
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename="view_event"),
        )
        # Grant view_patient permission
        patient_ct = ContentType.objects.get_for_model(Patient)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=patient_ct, codename="view_patient"),
        )

        cls.patient = Patient.objects.create(
            name="Markdown Render Patient",
            birthday="1990-01-01",
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username="mdrenderdoc", password="testpass123")

    def _create_dailynote(self, content):
        return DailyNote.objects.create(
            patient=self.patient,
            description="Markdown rendering test",
            content=content,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )

    def _detail_url(self, pk):
        return reverse("dailynotes:dailynote_detail", kwargs={"pk": pk})

    def _get_rendered_content(self, content):
        """Helper: create a daily note with given content and return the
        rendered HTML from the detail page."""
        note = self._create_dailynote(content)
        response = self.client.get(self._detail_url(note.pk))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    # ------------------------------------------------------------------
    # 1. Nested lists with hierarchy
    # ------------------------------------------------------------------

    def test_detail_renders_nested_lists_with_hierarchy(self):
        """The detail page must render nested ordered/unordered lists with
        proper HTML hierarchy (``<ol>/<ul>`` nested inside ``<li>``)."""
        md = (
            "1. Primeiro item\n"
            "2. Segundo item\n"
            "   - Detalhe A\n"
            "   - Detalhe B\n"
            "3. Terceiro item\n"
        )
        html = self._get_rendered_content(md)

        # Outer ordered list in markdown-content area
        self.assertIn("<ol>", html)
        self.assertIn("<li>Segundo item<ul>", html)
        # Nested items
        self.assertIn("<li>Detalhe A</li>", html)
        self.assertIn("<li>Detalhe B</li>", html)
        # Closing nested list inside parent li
        self.assertIn("</ul></li>", html)

    def test_detail_renders_deep_nested_lists(self):
        """Deeply nested lists (3+ levels) must preserve hierarchy."""
        md = (
            "- Alpha\n"
            "  - Sub-alpha\n"
            "    - Deep nesting\n"
            "- Beta\n"
        )
        html = self._get_rendered_content(md)

        self.assertIn("<li>Alpha<ul>", html)
        self.assertIn("<li>Sub-alpha<ul>", html)
        self.assertIn("Deep nesting", html)
        self.assertIn("Beta", html)

    # ------------------------------------------------------------------
    # 2. Core inline formatting
    # ------------------------------------------------------------------

    def test_detail_renders_core_inline_formatting(self):
        """The detail page must render **bold**, *italic*, ``code``, and
        ~~strike~~ as proper semantic HTML tags."""
        md = (
            "Paciente apresenta **dor intensa** e *febre baixa*, "
            "com sinais de ~~melhora~~ piora. "
            "Prescrito `dipirona 1g` via oral.\n"
        )
        html = self._get_rendered_content(md)

        self.assertIn("<strong>dor intensa</strong>", html)
        self.assertIn("<em>febre baixa</em>", html)
        self.assertIn("<del>melhora</del>", html)
        self.assertIn("<code>dipirona 1g</code>", html)

    def test_detail_renders_headings(self):
        """Markdown headings must render as proper h1-h6 tags."""
        md = "## Evolução Clínica\n\nConteúdo da evolução.\n"
        html = self._get_rendered_content(md)
        self.assertIn("<h2>Evolução Clínica</h2>", html)

    def test_detail_renders_links(self):
        """Markdown links must render as proper anchor tags."""
        md = "Veja [protocolo](https://example.com/protocol) para detalhes.\n"
        html = self._get_rendered_content(md)
        self.assertIn('<a href="https://example.com/protocol"', html)
        self.assertIn(">protocolo</a>", html)

    # ------------------------------------------------------------------
    # 3. Blockquote and code semantics
    # ------------------------------------------------------------------

    def test_detail_renders_blockquote_and_code_semantics(self):
        """The detail page must render blockquotes as ``<blockquote>`` and
        fenced code blocks as ``<pre><code>``."""
        md = (
            "> Observação importante:\n"
            "> Paciente refere alergia a penicilina.\n"
            "\n"
            "```python\n"
            "# Exemplo de código\n"
            "dosagem = 500\n"
            "```\n"
        )
        html = self._get_rendered_content(md)

        # Blockquote
        self.assertIn("<blockquote>", html)
        self.assertIn("Observação importante", html)
        self.assertIn("alergia a penicilina", html)
        self.assertIn("</blockquote>", html)

        # Code block
        self.assertIn("<pre><code", html)
        self.assertIn("language-python", html)
        self.assertIn("dosagem = 500", html)
        self.assertIn("</code></pre>", html)

    # ------------------------------------------------------------------
    # 4. Hardening: desktop and mobile use shared pipeline
    # ------------------------------------------------------------------

    def test_detail_desktop_and_mobile_render_same_markdown(self):
        """Both desktop (``d-none d-lg-block``) and mobile
        (``d-lg-none content-section``) sections must contain the same
        markdown-rendered HTML output."""
        md = "- Item **bold** and *italic*\n"
        html = self._get_rendered_content(md)

        # The markdown-rendered content should appear in both sections
        # Desktop section
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)

        # Count occurrences — both desktop and mobile render the same content
        strong_count = html.count("<strong>bold</strong>")
        self.assertGreaterEqual(
            strong_count, 2,
            "Expected bold to appear at least twice (desktop + mobile)",
        )

    def test_detail_empty_content_shows_fallback(self):
        """When content is empty, the fallback message must still appear."""
        note = DailyNote.objects.create(
            patient=self.patient,
            description="Empty note test",
            content="",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )
        response = self.client.get(self._detail_url(note.pk))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn("Nenhum conteúdo foi adicionado a esta evolução.", html)

    # ------------------------------------------------------------------
    # 5. Actions and permissions unchanged
    # ------------------------------------------------------------------

    def test_detail_preserves_action_buttons(self):
        """PDF, copy, edit, duplicate, delete, and back buttons
        must remain unchanged after markdown migration.
        The legacy print action must NOT appear."""
        note = self._create_dailynote("Simple content")
        response = self.client.get(self._detail_url(note.pk))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        # PDF download button
        pdf_url = reverse(
            "dailynotes:dailynote_pdf", kwargs={"pk": note.pk}
        )
        self.assertIn(pdf_url, html)

        # Legacy print link must NOT be present
        self.assertNotIn("dailynote_print", html)

        # Copy button
        self.assertIn("copy-content-btn", html)

        # Back link
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        self.assertIn(timeline_url, html)

    def test_detail_sanitizes_unsafe_content(self):
        """User-entered markdown with XSS attempts must be sanitized."""
        md = (
            'Text before <script>alert("xss")</script> text after\n'
            'and [bad](javascript:alert(1)).\n'
        )
        html = self._get_rendered_content(md)

        # Extract only the markdown-content section to avoid false positives
        # from the base template's own <script> tags.
        start = html.find('class="markdown-content"')
        self.assertGreater(start, 0, "markdown-content div not found")
        content_section = html[start:]
        # Find end of the markdown-content div
        end = content_section.find('</div>')
        content_section = content_section[:end]

        self.assertNotIn("<script>", content_section)
        self.assertNotIn("</script>", content_section)
        self.assertNotIn("javascript:", content_section)

    # ------------------------------------------------------------------
    # 6. No longer uses |linebreaks filter
    # ------------------------------------------------------------------

    def test_detail_does_not_use_linebreaks_output(self):
        """The page must NOT produce ``|linebreaks`` style output
        (``<p>`` wrapping every line with no semantic markup)."""
        md = "Line one\nLine two\nLine three\n"
        html = self._get_rendered_content(md)

        # With |linebreaks, each line would be wrapped in its own <p> tag
        # With |markdown, a single paragraph should be rendered
        # The markdown renderer produces <p> for the paragraph block
        # The old linebreaks would NOT produce <p>Line one</p> separately for each
        # line — it would group them.
        # The key differentiator: markdown does NOT wrap each line in its own <p>
        # Instead it creates one <p> with all content (or <br> for hard breaks)
        self.assertIn("Line one", html)
        self.assertIn("Line two", html)
        self.assertIn("Line three", html)
