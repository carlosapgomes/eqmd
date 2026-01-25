from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient
from ..models import SimpleNote
from ..forms import SimpleNoteForm

User = get_user_model()


class SimpleNoteModelTests(TestCase):
    """Test cases for SimpleNote model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            fiscal_number="12345678901",
            created_by=self.user,
            updated_by=self.user
        )

    def test_create_simple_note(self):
        """Test creating a simple note."""
        simple_note = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="Test simple note content",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(simple_note.patient, self.patient)
        self.assertEqual(simple_note.content, "Test simple note content")
        self.assertEqual(simple_note.created_by, self.user)
        self.assertEqual(simple_note.event_type, SimpleNote.SIMPLE_NOTE_EVENT)

    def test_simple_note_str(self):
        """Test string representation of simple note."""
        simple_note = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="Test content",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        expected_str = f"Nota - {self.patient.name} - {simple_note.event_datetime.strftime('%d/%m/%Y %H:%M')}"
        self.assertEqual(str(simple_note), expected_str)

    def test_simple_note_ordering(self):
        """Test that simple notes are ordered by event_datetime descending."""
        note1 = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="First note",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user
        )
        note2 = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="Second note",
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        notes = list(SimpleNote.objects.all())
        self.assertEqual(notes[0], note2)  # Most recent first
        self.assertEqual(notes[1], note1)


class SimpleNoteFormTests(TestCase):
    """Test cases for SimpleNoteForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            fiscal_number="12345678901",
            created_by=self.user,
            updated_by=self.user
        )

    def test_valid_form(self):
        """Test form with valid data."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'This is a valid simple note content with more than 10 characters.'
        }
        form = SimpleNoteForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_content_too_short(self):
        """Test form validation with content too short."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'Too short'
        }
        form = SimpleNoteForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_future_datetime(self):
        """Test form validation with future datetime."""
        future_datetime = timezone.now() + timezone.timedelta(days=1)
        form_data = {
            'event_datetime': future_datetime,
            'content': 'Valid content with enough characters to pass validation.'
        }
        form = SimpleNoteForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)

    def test_form_save(self):
        """Test form save functionality."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'This is a valid simple note content for testing save functionality.'
        }
        form = SimpleNoteForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        # Test creating new instance
        simple_note = form.save(commit=False)
        simple_note.patient = self.patient
        simple_note.description = "Nota/Observação"
        simple_note.save()
        
        self.assertEqual(simple_note.created_by, self.user)
        self.assertEqual(simple_note.updated_by, self.user)
