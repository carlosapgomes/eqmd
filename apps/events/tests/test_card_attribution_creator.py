"""R1: the timeline card footer credits the creator, not the last editor.

Design D1 (which user the footer names) and D2 (the fallbacks when that user has
no display name or no longer resolves), slice 001 of
``openspec/changes/add-approval-attribution-display``. Row builders and the
footer parser live in ``card_attribution_helpers``.
"""

from django.template.loader import render_to_string

from apps.events.tests.card_attribution_helpers import (
    CardAttributionTestBase,
    StubEvent,
    StubUser,
    card_event_data,
    footer_text,
)


class CreatorAttributionTests(CardAttributionTestBase):
    """R1: the footer shows the creator, not the last editor (design D1)."""

    def test_footer_shows_creator_not_last_editor(self):
        note = self._note(updated_by=self.doctor)
        self._freeze_timestamps(note)

        footer = footer_text(self._timeline_html())

        self.assertIn("Criado por Estudante Verificação", footer)
        self.assertNotIn("Médico Verificação", footer)

    def test_footer_creator_falls_back_to_username(self):
        note = self._note(created_by=self.nameless, updated_by=self.nameless)
        self._freeze_timestamps(note)

        footer = footer_text(self._timeline_html())

        self.assertIn("Criado por cardattrnameless", footer)

    def test_footer_prints_creator_profession_not_editor_profession(self):
        """D1 covers both sides of the profession guard.

        ``EqmdCustomUser`` exposes ``profession_type``, not ``profession``, so
        a real row never fills the profession span; the branch is rendered with
        objects that carry the attribute to pin which side feeds it.
        """
        event = StubEvent(
            created_by=StubUser("Estudante Verificação", "student", "Estudante"),
            updated_by=StubUser("Médico Editor", "editor", "Médico"),
        )

        footer = footer_text(
            render_to_string(
                "events/partials/event_card_base.html",
                {"event": event, "event_data": card_event_data()},
            )
        )

        self.assertIn("(Estudante)", footer)
        self.assertNotIn("(Médico)", footer)

    def test_footer_creator_falls_back_to_removed_user_placeholder(self):
        """D2's last fallback, for a creator FK that no longer resolves."""
        event = StubEvent(created_by=None)

        footer = footer_text(
            render_to_string(
                "events/partials/event_card_base.html",
                {"event": event, "event_data": card_event_data()},
            )
        )

        self.assertIn("Criado por usuário removido", footer)
