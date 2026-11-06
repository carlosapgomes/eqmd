"""Shared fixtures for the timeline card footer attribution tests.

R1 (creator, design D1/D2), R2 (approver, design D3), R3 (per-type footer
snapshot and the timeline query contract) of
``openspec/changes/add-approval-attribution-display``, slice 001.

The card is the timeline card, so every assertion reads rendered HTML: the
footer text a clinician sees, not the template source.

Split plan: this module is the support half of what began as one 527-line
``test_card_attribution.py``, which crossed the 450-line hard limit in
``docs/workflows/coding-standards.md``. It is now four sibling test modules
plus this support module, split by concern:

* ``card_attribution_helpers.py`` (this module) — row builders, footer parsing,
  render helpers, stub objects and ``CardAttributionTestBase``.
* ``test_card_attribution_creator.py`` — R1: who the footer credits.
* ``test_card_attribution_approver.py`` — R2: when the approver line appears.
* ``test_card_attribution_card_partials.py`` — R3: one footer contract for
  every card partial.
* ``test_card_attribution_queries.py`` — R3: the timeline queryset supplies the
  approver foreign keys.

Keep each module under the 300-line soft limit: a new event type belongs in the
card-partials module, a new visibility rule in the approver module, and shared
row setup here.
"""

import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.events.models import Event
from apps.mediafiles.models import PhotoSeries
from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

User = get_user_model()

TIMELINE_URL_NAME = "apps.patients:patient_events_timeline"
PHOTOSERIES_CARD = "events/partials/event_card_photoseries.html"
SIMPLENOTE_CARD = "events/partials/event_card_simplenote.html"
DISCHARGEREPORT_CARD = "events/partials/event_card_dischargereport.html"

# Every card partial the timeline dispatches to (patient_timeline.html), keyed
# by the event type that selects it. ``event_card_default.html`` is the
# fallback, here pinned to an exam result type (no dedicated partial).
CARD_PARTIALS = {
    "events/partials/event_card_historyandphysical.html": Event.HISTORY_AND_PHYSICAL_EVENT,
    "events/partials/event_card_dailynote.html": Event.DAILY_NOTE_EVENT,
    SIMPLENOTE_CARD: Event.SIMPLE_NOTE_EVENT,
    "events/partials/event_card_photo.html": Event.PHOTO_EVENT,
    DISCHARGEREPORT_CARD: Event.DISCHARGE_REPORT_EVENT,
    "events/partials/event_card_prescription.html": Event.OUTPT_PRESCRIPTION_EVENT,
    "events/partials/event_card_report.html": Event.REPORT_EVENT,
    PHOTOSERIES_CARD: Event.PHOTO_SERIES_EVENT,
    "events/partials/event_card_videoclip.html": Event.VIDEO_CLIP_EVENT,
    "events/partials/event_card_pdfform.html": Event.PDF_FORM_EVENT,
    "events/partials/event_card_record_change.html": Event.RECORD_NUMBER_CHANGE_EVENT,
    "events/partials/event_card_admission.html": Event.ADMISSION_EVENT,
    "events/partials/event_card_discharge.html": Event.DISCHARGE_EVENT,
    "events/partials/event_card_transfer.html": Event.TRANSFER_EVENT,
    "events/partials/event_card_consentform.html": Event.CONSENT_FORM_EVENT,
    "events/partials/event_card_profile_change.html": Event.PATIENT_PROFILE_CHANGE_EVENT,
    "events/partials/event_card_default.html": Event.EXAM_RESULT_EVENT,
}

# Partials whose draft actions carry a review link (unchanged by this slice).
REVISAR_PARTIALS = {
    "events/partials/event_card_consentform.html",
    "events/partials/event_card_dailynote.html",
    "events/partials/event_card_historyandphysical.html",
    "events/partials/event_card_pdfform.html",
    "events/partials/event_card_photo.html",
    PHOTOSERIES_CARD,
    "events/partials/event_card_prescription.html",
    SIMPLENOTE_CARD,
    "events/partials/event_card_videoclip.html",
}

FOOTER_RE = re.compile(r"<footer\b.*?</footer>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def local_time(value):
    """Format a datetime the way the card footer renders it (local timezone)."""
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def footer_text(html):
    """Visible text of the card footer, tags stripped and whitespace collapsed."""
    footer = FOOTER_RE.search(html)
    assert footer, "rendered card has no <footer> block"
    text = TAG_RE.sub(" ", footer.group(0))
    return re.sub(r"\s+", " ", text).strip()


def card_event_data(can_edit=True):
    return {
        "event": None,
        "can_edit": can_edit,
        "can_delete": can_edit,
        "excerpt": "Trecho do evento",
        "tag_audit": None,
        "can_duplicate_pdf_submission": False,
    }


class StubUser:
    """Minimal user stand-in for footer branches no real row can reach."""

    def __init__(self, full_name="", username="", profession=""):
        self._full_name = full_name
        self.username = username
        self.profession = profession

    def get_full_name(self):
        return self._full_name


class StubEvent:
    """Event stand-in used only by the unreachable-branch render tests."""

    pk = "00000000-0000-0000-0000-000000000000"
    event_type = Event.SIMPLE_NOTE_EVENT
    created_at = timezone.now()
    updated_at = timezone.now()
    is_draft = False

    def __init__(self, created_by, updated_by=None):
        self.created_by = created_by
        self.updated_by = updated_by or created_by

    def finalizer(self):
        return None

    def finalization_anchor(self):
        return None


class CardAttributionTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = cls._create_user(
            "cardattrstudent", User.STUDENT, "Estudante", "Verificação"
        )
        cls.doctor = cls._create_user(
            "cardattrdoctor", User.MEDICAL_DOCTOR, "Médico", "Verificação"
        )
        cls.nameless = cls._create_user("cardattrnameless", User.NURSE)
        cls.patient = Patient.objects.create(
            name="Card Attribution Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    @classmethod
    def _create_user(cls, username, profession_type, first_name="", last_name=""):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=profession_type,
            first_name=first_name,
            last_name=last_name,
        )

    def _note(self, description="Nota de atribuição", **extra):
        return SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description=description,
            content="Conteúdo da nota",
            created_by=extra.pop("created_by", self.student),
            updated_by=extra.pop("updated_by", self.student),
            **extra,
        )

    def _event(self, event_type, **extra):
        return Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Evento de atribuição",
            event_type=event_type,
            created_by=extra.pop("created_by", self.student),
            updated_by=extra.pop("updated_by", self.student),
            **extra,
        )

    def _photoseries(self, **extra):
        return PhotoSeries.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Série de fotos de atribuição",
            created_by=extra.pop("created_by", self.student),
            updated_by=extra.pop("updated_by", self.student),
            **extra,
        )

    def _discharge_report(self, **extra):
        return DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Relatório de alta de atribuição",
            admission_date=date(2026, 1, 1),
            discharge_date=date(2026, 1, 5),
            admission_history="História",
            problems_and_diagnosis="Diagnóstico",
            exams_list="Exames",
            procedures_list="Procedimentos",
            inpatient_medical_history="Evolução",
            discharge_status="Alta",
            discharge_recommendations="Recomendações",
            medical_specialty="Clínica Médica",
            # DischargeReport.__init__ drafts a new row unless told otherwise.
            is_draft=extra.pop("is_draft", False),
            created_by=extra.pop("created_by", self.student),
            updated_by=extra.pop("updated_by", self.student),
            **extra,
        )

    def _freeze_timestamps(self, event, *, edited=False):
        """Pin created_at/updated_at so the ``Editado em`` branch is explicit."""
        created_at = event.created_at
        updated_at = created_at + timedelta(hours=1) if edited else created_at
        type(event).all_objects.filter(pk=event.pk).update(
            created_at=created_at, updated_at=updated_at
        )
        event.refresh_from_db()
        return event

    def _render_card(self, partial, event, can_edit=True):
        event_data = card_event_data(can_edit)
        event_data["event"] = event
        return render_to_string(partial, {"event": event, "event_data": event_data})

    def _timeline_html(self, user=None):
        self.client.force_login(user or self.doctor)
        response = self.client.get(
            reverse(TIMELINE_URL_NAME, kwargs={"patient_id": self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()
