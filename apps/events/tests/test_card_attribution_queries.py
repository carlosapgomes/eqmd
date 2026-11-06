"""R3: the timeline queryset supplies the approver foreign keys.

Design D4: cards that show the approver must not issue a query each, so
``PatientEventsTimelineView.get_queryset`` selects the promotion and
finalization users. Slice 001 of
``openspec/changes/add-approval-attribution-display``.
"""

from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.events.tests.card_attribution_helpers import (
    DISCHARGEREPORT_CARD,
    SIMPLENOTE_CARD,
    TIMELINE_URL_NAME,
    CardAttributionTestBase,
    footer_text,
)
from apps.events.views import PatientEventsTimelineView


class TimelineQueryContractTests(CardAttributionTestBase):
    """R3: the approver FKs come from the timeline queryset (design D4)."""

    def _timeline_events(self):
        request = RequestFactory().get(
            reverse(TIMELINE_URL_NAME, kwargs={"patient_id": self.patient.pk})
        )
        request.user = self.doctor
        view = PatientEventsTimelineView()
        view.setup(request, patient_id=self.patient.pk)
        return list(view.get_queryset())

    def test_promoted_cards_render_without_extra_queries(self):
        approved_at = timezone.now().replace(second=0, microsecond=0)
        for index in range(3):
            self._note(
                description=f"Nota promovida {index}",
                updated_by=self.doctor,
                draft_promoted_by=self.doctor,
                draft_promoted_at=approved_at,
            )
        self._discharge_report(
            updated_by=self.doctor,
            finalized_by=self.doctor,
            finalized_at=approved_at,
        )
        card_partials = {
            Event.SIMPLE_NOTE_EVENT: SIMPLENOTE_CARD,
            Event.DISCHARGE_REPORT_EVENT: DISCHARGEREPORT_CARD,
        }

        events = self._timeline_events()
        self.assertEqual(len(events), 4)

        with CaptureQueriesContext(connection) as captured:
            footers = [
                footer_text(self._render_card(card_partials[event.event_type], event))
                for event in events
            ]

        self.assertEqual(
            captured.captured_queries,
            [],
            "card rendering must not issue queries: the approver FKs belong to "
            "the timeline queryset",
        )
        for footer in footers:
            self.assertIn("Aprovado por Médico Verificação em", footer)
