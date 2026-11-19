"""DailyNote timeline card owns the copy-dialog hook class (design D2).

The card button switches from the generic ``copy-content-btn`` to
``copy-dailynote-btn`` so the shared handler in ``assets/index.js`` can never
intercept it, while every other event card keeps the generic direct-copy
button. Assertions are scoped to the card ``<article>`` of each event.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

from ..models import DailyNote

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class DailyNoteCardCopyDialogTests(TestCase):
    """The DailyNote card uses the dialog hook; other cards keep direct copy."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.doctor = create_profession_user("dn-copy-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Copy Dialog Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_note(self, *, is_draft=False):
        return DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content="Evolução do paciente sem queixas.",
            is_draft=is_draft,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    def _create_simplenote(self):
        return SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(minutes=30),
            description="Nota de teste",
            content="Paciente em observação.",
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    def _timeline_html(self):
        self.client.force_login(self.doctor)
        response = self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _card_html(self, html, event):
        """The ``<article>`` of one event card, without its neighbours."""
        marker = f'aria-labelledby="event-{event.pk}-title"'
        marker_start = html.index(marker)
        start = html.rindex("<article", 0, marker_start)
        return html[start : html.index("</article>", start)]

    def test_final_dailynote_card_renders_dailynote_copy_button(self):
        note = self._create_note(is_draft=False)

        card = self._card_html(self._timeline_html(), note)

        self.assertIn("copy-dailynote-btn", card)
        self.assertNotIn("copy-content-btn", card)
        self.assertIn(f'data-content="{note.content}"', card)

    def test_draft_dailynote_card_renders_dailynote_copy_button(self):
        draft = self._create_note(is_draft=True)

        card = self._card_html(self._timeline_html(), draft)

        self.assertIn("copy-dailynote-btn", card)
        self.assertNotIn("copy-content-btn", card)
        self.assertIn(f'data-content="{draft.content}"', card)

    def test_simplenote_card_keeps_generic_copy_button(self):
        self._create_note(is_draft=False)
        simplenote = self._create_simplenote()

        card = self._card_html(self._timeline_html(), simplenote)

        self.assertIn("copy-content-btn", card)
        self.assertNotIn("copy-dailynote-btn", card)
