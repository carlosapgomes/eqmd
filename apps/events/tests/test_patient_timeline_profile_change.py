"""Tests for Patient profile change event rendering in the timeline.

TDD Slice 02 — RED phase: tests written BEFORE implementation.
These tests verify that the timeline renders a dedicated card for
PatientProfileChangeEvent with field-level diffs.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.events.models import Event, PatientProfileChangeEvent


class PatientTimelineProfileChangeTests(TestCase):
    """Tests for profile change event card rendering in the patient timeline."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data shared across all test methods."""
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        # Add necessary permissions
        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient',
        )
        cls.user.user_permissions.add(view_permission)

        event_content_type = ContentType.objects.get_for_model(Event)
        add_event_permission = Permission.objects.get(
            content_type=event_content_type,
            codename='add_event',
        )
        cls.user.user_permissions.add(add_event_permission)

        cls.patient = Patient.objects.create(
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
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def _get_timeline_response(self):
        """Helper: GET the patient timeline page."""
        url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )
        return self.client.get(url)

    def _create_profile_change_event(self, **overrides):
        """Helper: create a PatientProfileChangeEvent directly."""
        defaults = {
            'patient': self.patient,
            'event_datetime': '2025-01-15T10:30:00Z',
            'description': 'Alteração de perfil: Nome',
            'created_by': self.user,
            'updated_by': self.user,
            'changed_fields': 'name',
            'change_summary': 'Nome: João Silva → João Silva Jr.',
            'previous_values': {'name': 'João Silva'},
            'new_values': {'name': 'João Silva Jr.'},
        }
        defaults.update(overrides)
        return PatientProfileChangeEvent.objects.create(**defaults)

    # ------------------------------------------------------------------
    # Test 1: timeline renders profile change event with dedicated card
    # ------------------------------------------------------------------
    def test_timeline_renders_profile_change_event_with_dedicated_card(self):
        """Profile change event should render using the dedicated partial."""
        self._create_profile_change_event()

        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        # The profile change partial has a data-event-card="profile-change" attribute
        self.assertContains(
            response,
            'data-event-card="profile-change"',
            msg_prefix='Timeline should include the profile change card partial',
        )

    # ------------------------------------------------------------------
    # Test 2: card renders all changed fields with old/new values
    # ------------------------------------------------------------------
    def test_profile_change_card_renders_all_changed_fields_with_old_new_values(self):
        """Card should display each changed field with old → new diff."""
        self._create_profile_change_event(
            changed_fields='name,phone',
            change_summary='Nome: João Silva → João Silva Jr.; Telefone: (11) 99999-0000 → (21) 98888-1111',
            previous_values={'name': 'João Silva', 'phone': '(11) 99999-0000'},
            new_values={'name': 'João Silva Jr.', 'phone': '(21) 98888-1111'},
        )

        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        # Should display old value
        self.assertContains(response, 'João Silva')
        # Should display new value
        self.assertContains(response, 'João Silva Jr.')
        # Should display old phone
        self.assertContains(response, '(11) 99999-0000')
        # Should display new phone
        self.assertContains(response, '(21) 98888-1111')
        # Should display the arrow separator
        self.assertContains(response, '→')
        # Should display field label
        self.assertContains(response, 'Nome')

    # ------------------------------------------------------------------
    # Test 3: uses expected badge and short label
    # ------------------------------------------------------------------
    def test_profile_change_event_uses_expected_badge_and_short_label(self):
        """Profile change card should use the correct badge class and short label."""
        self._create_profile_change_event()

        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        # Short display label for profile change is "Perfil"
        self.assertContains(response, 'Perfil')

        # Badge class should be bg-info (as defined in get_event_type_badge_class)
        self.assertContains(response, 'bg-info')

        # Icon should be bi-person-gear (as defined in get_event_type_icon)
        self.assertContains(response, 'bi-person-gear')

    # ------------------------------------------------------------------
    # Test 4: profile change card is informational (no view/edit actions)
    # ------------------------------------------------------------------
    def test_profile_change_card_shows_informational_action_text(self):
        """Profile change card should show informational text instead of action buttons."""
        self._create_profile_change_event()

        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Evento informativo')
        self.assertNotContains(response, 'aria-label="Visualizar Alteração de Perfil completo"')
        self.assertNotContains(response, 'aria-label="Editar Alteração de Perfil"')
