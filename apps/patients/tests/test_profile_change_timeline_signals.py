"""Tests for Patient profile change timeline events (signals + model).

TDD Slice 01 — RED phase: tests written BEFORE implementation.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

from ..models import Patient
from apps.events.models import Event, PatientProfileChangeEvent

User = get_user_model()


class PatientProfileChangeTimelineSignalTests(TestCase):
    """Tests that profile changes on Patient generate timeline events."""

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
            address='Rua A, 123',
            city='São Paulo',
            state='SP',
            zip_code='01001-000',
            id_number='1234567',
            fiscal_number='123.456.789-00',
            healthcard_number='HC-001',
            created_by=self.user,
            updated_by=self.user,
        )

    # ------------------------------------------------------------------
    # Test: creates event when a monitored field changes
    # ------------------------------------------------------------------
    def test_creates_profile_change_event_when_monitored_field_changes(self):
        """Changing a monitored field (name) should create exactly one event."""
        self.patient.name = 'João Silva Jr.'
        self.patient.save()

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 1)

        event = events.first()
        self.assertEqual(event.event_type, Event.PATIENT_PROFILE_CHANGE_EVENT)
        self.assertIn('name', event.previous_values)
        self.assertIn('name', event.new_values)
        self.assertEqual(event.previous_values['name'], 'João Silva')
        self.assertEqual(event.new_values['name'], 'João Silva Jr.')

    # ------------------------------------------------------------------
    # Test: single event with multiple field diffs per save
    # ------------------------------------------------------------------
    def test_creates_single_event_with_multiple_field_diffs_per_save(self):
        """Changing several monitored fields in one save() creates one event."""
        self.patient.name = 'Maria Oliveira'
        self.patient.phone = '(21) 98888-1111'
        self.patient.city = 'Rio de Janeiro'
        self.patient.save()

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 1)

        event = events.first()
        # Should contain all three changed fields
        self.assertEqual(set(event.previous_values.keys()), {'name', 'phone', 'city'})
        self.assertEqual(set(event.new_values.keys()), {'name', 'phone', 'city'})

        self.assertEqual(event.previous_values['name'], 'João Silva')
        self.assertEqual(event.new_values['name'], 'Maria Oliveira')
        self.assertEqual(event.previous_values['phone'], '(11) 99999-0000')
        self.assertEqual(event.new_values['phone'], '(21) 98888-1111')
        self.assertEqual(event.previous_values['city'], 'São Paulo')
        self.assertEqual(event.new_values['city'], 'Rio de Janeiro')

    # ------------------------------------------------------------------
    # Test: no event when no monitored field changes
    # ------------------------------------------------------------------
    def test_does_not_create_profile_change_event_when_no_monitored_field_changes(self):
        """Saving without changing monitored fields should NOT create an event."""
        self.patient.save()  # no field changed

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 0)

    # ------------------------------------------------------------------
    # Test: no event without updated_by
    # ------------------------------------------------------------------
    def test_does_not_create_profile_change_event_without_updated_by(self):
        """If updated_by is not set, no event should be created."""
        # Manually set the _profile_changes attribute and call the signal
        # handler to verify the guard logic.
        from apps.patients.signals import create_profile_change_event

        # Simulate a profile change diff without updated_by
        self.patient._profile_changes = {
            'name': {'label': 'Nome', 'old': 'João Silva', 'new': 'Changed'},
        }
        # updated_by is the real user here, so we clear it
        old_updated_by = self.patient.updated_by
        self.patient.updated_by = None

        # Invoke the signal handler directly
        create_profile_change_event(
            sender=Patient,
            instance=self.patient,
            created=False,
        )

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 0)

        # Restore
        self.patient.updated_by = old_updated_by

    # ------------------------------------------------------------------
    # Test: gender diff uses human labels
    # ------------------------------------------------------------------
    def test_gender_diff_uses_human_labels(self):
        """Gender values in the diff should use human-readable labels."""
        self.patient.gender = Patient.GenderChoices.FEMALE
        self.patient.save()

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 1)

        event = events.first()
        self.assertEqual(event.previous_values['gender'], 'Masculino')
        self.assertEqual(event.new_values['gender'], 'Feminino')

    # ------------------------------------------------------------------
    # Hotfix tests: description must be bounded to 255 chars
    # ------------------------------------------------------------------
    def test_profile_change_event_description_is_short_and_bounded(self):
        """Event.description must never exceed 255 chars (Event.max_length)."""
        self.patient.name = 'New Name'
        self.patient.phone = 'New Phone'
        self.patient.address = 'New Address'
        self.patient.city = 'New City'
        self.patient.state = 'New State'
        self.patient.zip_code = 'New Zip'
        self.patient.id_number = 'New ID'
        self.patient.fiscal_number = 'New Fiscal'
        self.patient.healthcard_number = 'New HC'
        self.patient.gender = Patient.GenderChoices.FEMALE
        self.patient.birthday = date(2000, 1, 1)
        self.patient.save()

        event = PatientProfileChangeEvent.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(event)
        self.assertLessEqual(len(event.description), 255)

    def test_long_profile_changes_do_not_fail_event_creation(self):
        """Long field values must not cause DB DataError on event creation."""
        # Use max-length values that Patient.full_clean() will accept
        self.patient.name = 'B' * 255
        self.patient.address = 'C' * 255
        self.patient.phone = 'D' * 100
        self.patient.city = 'E' * 100
        self.patient.state = 'F' * 100
        self.patient.save()

        events = PatientProfileChangeEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 1)

        event = events.first()
        # Full diff still in structured fields
        self.assertIn('name', event.previous_values)
        self.assertIn('name', event.new_values)
        self.assertIn('address', event.previous_values)
        self.assertIn('address', event.new_values)
        # description must be safe
        self.assertLessEqual(len(event.description), 255)


