"""R2: the approver line, and only for currently definitive records.

Design D3: a card shows ``Aprovado por <nome> em <data>`` when the record is
definitive and carries promotion (notes) or finalization (discharge report)
metadata; drafts never show it, even when a reverted discharge report retains
``finalized_by``/``finalized_at``. Slice 001 of
``openspec/changes/add-approval-attribution-display``.
"""

from django.utils import timezone

from apps.events.tests.card_attribution_helpers import (
    CardAttributionTestBase,
    footer_text,
    local_time,
)


class ApproverAttributionTests(CardAttributionTestBase):
    """R2: approver visible only for currently definitive records (design D3)."""

    def setUp(self):
        self.approved_at = timezone.now().replace(second=0, microsecond=0)
        self.expected_when = local_time(self.approved_at)

    def test_promoted_event_shows_approver_and_promotion_date(self):
        note = self._note(
            updated_by=self.doctor,
            draft_promoted_by=self.doctor,
            draft_promoted_at=self.approved_at,
        )
        self._freeze_timestamps(note)

        footer = footer_text(self._timeline_html())

        self.assertIn(
            f"Aprovado por Médico Verificação em {self.expected_when}", footer
        )
        self.assertIn("Criado por Estudante Verificação", footer)

    def test_definitive_event_without_promotion_shows_no_approver(self):
        note = self._note(updated_by=self.doctor)
        self._freeze_timestamps(note)

        footer = footer_text(self._timeline_html())

        self.assertNotIn("Aprovado por", footer)

    def test_draft_with_retained_finalization_shows_no_approver(self):
        draft = self._note(
            is_draft=True,
            draft_promoted_by=self.doctor,
            draft_promoted_at=self.approved_at,
        )
        self._freeze_timestamps(draft)

        html = self._timeline_html()
        footer = footer_text(html)

        self.assertNotIn("Aprovado por", footer)
        self.assertIn("Criado por Estudante Verificação", footer)
        self.assertIn("draft-badge", html)

    def test_discharge_report_approver_uses_finalized_by(self):
        report = self._discharge_report(
            updated_by=self.doctor,
            finalized_by=self.doctor,
            finalized_at=self.approved_at,
        )
        self._freeze_timestamps(report)

        footer = footer_text(self._timeline_html())

        self.assertIn(
            f"Aprovado por Médico Verificação em {self.expected_when}", footer
        )

    def test_reverted_discharge_report_hides_retained_finalizer(self):
        report = self._discharge_report(
            is_draft=True,
            updated_by=self.doctor,
            finalized_by=self.doctor,
            finalized_at=self.approved_at,
        )
        self._freeze_timestamps(report)

        footer = footer_text(self._timeline_html())

        self.assertNotIn("Aprovado por", footer)

    def test_approver_falls_back_to_username(self):
        note = self._note(
            updated_by=self.nameless,
            draft_promoted_by=self.nameless,
            draft_promoted_at=self.approved_at,
        )
        self._freeze_timestamps(note)

        footer = footer_text(self._timeline_html())

        self.assertIn(f"Aprovado por cardattrnameless em {self.expected_when}", footer)
