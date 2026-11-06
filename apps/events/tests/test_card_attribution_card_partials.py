"""R3: every card partial keeps the same footer contract.

Design D4: the attribution is footer-level, so all 17 timeline card partials
render it the same way, drafts keep their badge/tint/review link, and the
``Editado em`` line is untouched. Slice 001 of
``openspec/changes/add-approval-attribution-display``.
"""

from django.urls import reverse
from django.utils import timezone

from apps.events.tests.card_attribution_helpers import (
    CARD_PARTIALS,
    DISCHARGEREPORT_CARD,
    PHOTOSERIES_CARD,
    REVISAR_PARTIALS,
    TIMELINE_URL_NAME,
    CardAttributionTestBase,
    footer_text,
    local_time,
)


class PerTypeFooterSnapshotTests(CardAttributionTestBase):
    """R3: every card partial keeps the same footer contract (design D4)."""

    def setUp(self):
        self.approved_at = timezone.now().replace(second=0, microsecond=0)

    def _card_event(self, partial, event_type, **extra):
        """Row for one card partial.

        The card *body* links to a detail page, which only a concrete subclass
        resolves; the footer under test does not read those URLs, so they are
        pinned on the instance and every partial stays renderable.
        """
        if partial == PHOTOSERIES_CARD:
            event = self._photoseries(**extra)
        elif partial == DISCHARGEREPORT_CARD:
            event = self._discharge_report(**extra)
        else:
            event = self._event(event_type, **extra)
        event.get_absolute_url = lambda: reverse(
            TIMELINE_URL_NAME, kwargs={"patient_id": self.patient.pk}
        )
        event.get_edit_url = lambda: f"/eventos/{event.pk}/editar/"
        return event

    def _expected_creator_line(self, partial):
        line = "Criado por Estudante Verificação"
        if partial == PHOTOSERIES_CARD:
            # The photo-count badge lives inside the attribution line.
            line += " 0 fotos"
        return line

    def test_definitive_card_without_promotion_has_no_approver(self):
        for partial, event_type in CARD_PARTIALS.items():
            with self.subTest(partial=partial):
                event = self._card_event(partial, event_type, updated_by=self.doctor)
                self._freeze_timestamps(event)

                footer = footer_text(self._render_card(partial, event))

                self.assertEqual(footer, self._expected_creator_line(partial))

    def test_draft_card_keeps_badge_tint_and_review_link(self):
        for partial, event_type in CARD_PARTIALS.items():
            with self.subTest(partial=partial):
                event = self._card_event(partial, event_type, is_draft=True)
                self._freeze_timestamps(event)

                html = self._render_card(partial, event)

                self.assertIn("timeline-card-draft", html)
                self.assertIn("draft-badge", html)
                self.assertIn("Rascunho", html)
                self.assertNotIn("Aprovado por", footer_text(html))
                revisar = 'aria-label="Revisar rascunho' in html
                self.assertEqual(
                    revisar,
                    partial in REVISAR_PARTIALS,
                    f"Revisar link changed for {partial}",
                )

    def test_promoted_card_of_every_type_shows_the_approver_line(self):
        for partial, event_type in CARD_PARTIALS.items():
            with self.subTest(partial=partial):
                event = self._card_event(
                    partial,
                    event_type,
                    updated_by=self.doctor,
                    draft_promoted_by=self.doctor,
                    draft_promoted_at=self.approved_at,
                )
                self._freeze_timestamps(event)

                footer = footer_text(self._render_card(partial, event))

                self.assertIn(
                    f"Aprovado por Médico Verificação em "
                    f"{local_time(self.approved_at)}",
                    footer,
                )
                self.assertIn(self._expected_creator_line(partial), footer)

    def test_edited_timestamp_line_is_unchanged(self):
        for partial, event_type in CARD_PARTIALS.items():
            with self.subTest(partial=partial):
                event = self._card_event(partial, event_type, updated_by=self.doctor)
                self._freeze_timestamps(event, edited=True)

                footer = footer_text(self._render_card(partial, event))

                self.assertIn(f"Editado em {local_time(event.updated_at)}", footer)
                self.assertIn(self._expected_creator_line(partial), footer)
