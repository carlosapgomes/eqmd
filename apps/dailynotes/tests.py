from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient
from apps.events.models import Event
from .models import DailyNote

User = get_user_model()


class DailyNoteModelTest(TestCase):
    """Test cases for DailyNote model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_daily_note_creation(self):
        """Test creating a daily note."""
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            description='Test Daily Note',
            content='This is a test daily note content.',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(daily_note.content, 'This is a test daily note content.')
        self.assertEqual(daily_note.patient, self.patient)
        self.assertEqual(daily_note.created_by, self.user)
        self.assertTrue(daily_note.id)

    def test_daily_note_event_type_auto_set(self):
        """Test that event_type is automatically set to DAILY_NOTE_EVENT."""
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            description='Test Daily Note',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(daily_note.event_type, Event.DAILY_NOTE_EVENT)

    def test_daily_note_str_representation(self):
        """Test string representation of daily note."""
        event_datetime = timezone.now()
        daily_note = DailyNote.objects.create(
            event_datetime=event_datetime,
            description='Test Daily Note',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        expected_str = f"Evolução - {self.patient.name} - {event_datetime.strftime('%d/%m/%Y %H:%M')}"
        self.assertEqual(str(daily_note), expected_str)

    def test_daily_note_inheritance_from_event(self):
        """Test that DailyNote properly inherits from Event."""
        daily_note = DailyNote.objects.create(
            event_datetime=timezone.now(),
            description='Test Daily Note',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Check that it's an instance of Event
        self.assertIsInstance(daily_note, Event)

        # Check that it has Event fields
        self.assertTrue(hasattr(daily_note, 'event_type'))
        self.assertTrue(hasattr(daily_note, 'event_datetime'))
        self.assertTrue(hasattr(daily_note, 'description'))
        self.assertTrue(hasattr(daily_note, 'patient'))
        self.assertTrue(hasattr(daily_note, 'created_by'))
        self.assertTrue(hasattr(daily_note, 'created_at'))
        self.assertTrue(hasattr(daily_note, 'updated_at'))
        self.assertTrue(hasattr(daily_note, 'updated_by'))

        # Check that it has DailyNote specific fields
        self.assertTrue(hasattr(daily_note, 'content'))

    def test_daily_note_meta_configuration(self):
        """Test Meta class configuration."""
        self.assertEqual(DailyNote._meta.verbose_name, "Evolução")
        self.assertEqual(DailyNote._meta.verbose_name_plural, "Evoluções")
        self.assertEqual(DailyNote._meta.ordering, ["-event_datetime"])
