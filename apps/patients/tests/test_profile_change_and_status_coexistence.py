"""Tests for coexistence of profile-change and status-change events.

TDD Slice 03 — RED phase: tests written BEFORE implementation.

Ensures that a single `save()` on Patient that modifies both a profile field
and the status field generates **two independent events**: one
`StatusChangeEvent` and one `PatientProfileChangeEvent`.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date

from ..models import Patient
from apps.events.models import (
    Event,
    StatusChangeEvent,
    PatientProfileChangeEvent,
)

User = get_user_model()


class ProfileChangeAndStatusCoexistenceTests(TestCase):
    """Verify that profile and status events coexist correctly."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.patient = Patient.objects.create(
            name='João Silva',
            birthday=date(1990, 5, 15),
            gender=Patient.GenderChoices.MALE,
            phone='(11) 99999-0000',
            created_by=self.user,
            updated_by=self.user,
            status=Patient.Status.OUTPATIENT,
        )

    # ------------------------------------------------------------------
    # Test 1: single save with both status and profile changes → 2 events
    # ------------------------------------------------------------------
    def test_single_save_with_status_and_profile_changes_creates_two_events(self):
        """When a single save() changes both status and a profile field,
        exactly two independent timeline events should be created:
        one StatusChangeEvent and one PatientProfileChangeEvent."""
        # Change both status and a profile field in one save
        self.patient.status = Patient.Status.INPATIENT
        self.patient.name = 'João Silva Jr.'
        self.patient.save()

        # Expect exactly one status change event
        status_events = StatusChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(
            status_events.count(), 1,
            f"Expected 1 StatusChangeEvent, got {status_events.count()}",
        )
        status_event = status_events.first()
        self.assertEqual(status_event.previous_status, Patient.Status.OUTPATIENT)
        self.assertEqual(status_event.new_status, Patient.Status.INPATIENT)

        # Expect exactly one profile change event
        profile_events = PatientProfileChangeEvent.objects.filter(
            patient=self.patient,
        )
        self.assertEqual(
            profile_events.count(), 1,
            f"Expected 1 PatientProfileChangeEvent, got {profile_events.count()}",
        )
        profile_event = profile_events.first()
        self.assertEqual(profile_event.event_type,
                         Event.PATIENT_PROFILE_CHANGE_EVENT)
        self.assertIn('name', profile_event.previous_values)
        self.assertEqual(profile_event.previous_values['name'], 'João Silva')
        self.assertEqual(profile_event.new_values['name'], 'João Silva Jr.')

        # Confirm they are distinct event instances
        self.assertNotEqual(status_event.pk, profile_event.pk)

    # ------------------------------------------------------------------
    # Test 2: profile change event type is in EVENT_TYPE_CHOICES
    # ------------------------------------------------------------------
    def test_profile_change_event_type_is_available_in_event_type_choices(self):
        """The PATIENT_PROFILE_CHANGE_EVENT constant must appear in
        EVENT_TYPE_CHOICES so that timeline filters can expose it."""
        choice_values = [value for value, _ in Event.EVENT_TYPE_CHOICES]
        self.assertIn(
            Event.PATIENT_PROFILE_CHANGE_EVENT,
            choice_values,
            "PATIENT_PROFILE_CHANGE_EVENT missing from EVENT_TYPE_CHOICES",
        )

        # Also verify the human label
        choice_labels = {value: label for value, label in Event.EVENT_TYPE_CHOICES}
        self.assertEqual(
            choice_labels[Event.PATIENT_PROFILE_CHANGE_EVENT],
            'Alteração de Perfil',
        )

    # ------------------------------------------------------------------
    # Test 3: timeline filter can include profile change event type
    # ------------------------------------------------------------------
    def test_timeline_filter_can_include_profile_change_event_type(self):
        """A queryset filtered by PATIENT_PROFILE_CHANGE_EVENT should return
        the created profile change event."""
        # Create a profile change event
        self.patient.name = 'Maria Oliveira'
        self.patient.save()

        # Filter events by the new event type
        filtered = Event.objects.filter(
            patient=self.patient,
            event_type=Event.PATIENT_PROFILE_CHANGE_EVENT,
        )
        self.assertEqual(filtered.count(), 1)

        # Also verify filtering by choice value from EVENT_TYPE_CHOICES works
        event_type_value = Event.PATIENT_PROFILE_CHANGE_EVENT
        self.assertTrue(
            Event.objects.filter(
                patient=self.patient,
                event_type=event_type_value,
            ).exists(),
        )
