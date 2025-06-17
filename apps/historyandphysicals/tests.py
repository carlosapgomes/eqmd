from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django import forms
from apps.patients.models import Patient
from apps.events.models import Event
from .models import HistoryAndPhysical
from .forms import HistoryAndPhysicalForm

User = get_user_model()


class HistoryAndPhysicalModelTest(TestCase):
    """Test cases for HistoryAndPhysical model."""

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

    def test_historyandphysical_creation(self):
        """Test creating a history and physical."""
        historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Test History and Physical',
            content='This is a test history and physical content.',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(historyandphysical.content, 'This is a test history and physical content.')
        self.assertEqual(historyandphysical.patient, self.patient)
        self.assertEqual(historyandphysical.created_by, self.user)
        self.assertTrue(historyandphysical.id)

    def test_historyandphysical_event_type_auto_set(self):
        """Test that event_type is automatically set to HISTORY_AND_PHYSICAL_EVENT."""
        historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Test History and Physical',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(historyandphysical.event_type, Event.HISTORY_AND_PHYSICAL_EVENT)

    def test_historyandphysical_str_representation(self):
        """Test string representation of history and physical."""
        event_datetime = timezone.now()
        historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=event_datetime,
            description='Test History and Physical',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        expected_str = f"Anamnese e Exame Físico - {self.patient.name} - {event_datetime.strftime('%d/%m/%Y %H:%M')}"
        self.assertEqual(str(historyandphysical), expected_str)

    def test_historyandphysical_inheritance_from_event(self):
        """Test that HistoryAndPhysical properly inherits from Event."""
        historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Test History and Physical',
            content='Test content',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Check that it's an instance of Event
        self.assertIsInstance(historyandphysical, Event)

        # Check that it has Event fields
        self.assertTrue(hasattr(historyandphysical, 'event_type'))
        self.assertTrue(hasattr(historyandphysical, 'event_datetime'))
        self.assertTrue(hasattr(historyandphysical, 'description'))
        self.assertTrue(hasattr(historyandphysical, 'patient'))
        self.assertTrue(hasattr(historyandphysical, 'created_by'))
        self.assertTrue(hasattr(historyandphysical, 'created_at'))
        self.assertTrue(hasattr(historyandphysical, 'updated_at'))
        self.assertTrue(hasattr(historyandphysical, 'updated_by'))

        # Check that it has HistoryAndPhysical specific fields
        self.assertTrue(hasattr(historyandphysical, 'content'))

    def test_historyandphysical_meta_configuration(self):
        """Test Meta class configuration."""
        self.assertEqual(HistoryAndPhysical._meta.verbose_name, "Anamnese e Exame Físico")
        self.assertEqual(HistoryAndPhysical._meta.verbose_name_plural, "Anamneses e Exames Físicos")
        self.assertEqual(HistoryAndPhysical._meta.ordering, ["-event_datetime"])


class HistoryAndPhysicalFormTest(TestCase):
    """Test cases for HistoryAndPhysicalForm."""

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

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'This is a test history and physical content with enough characters.'
        }
        form = HistoryAndPhysicalForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_invalid_data_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = HistoryAndPhysicalForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)

    def test_form_invalid_future_datetime(self):
        """Test form validation for future datetime."""
        future_datetime = timezone.now() + timezone.timedelta(days=1)
        form_data = {
            'event_datetime': future_datetime,
            'content': 'This is a test history and physical content with enough characters.'
        }
        form = HistoryAndPhysicalForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)

    def test_form_invalid_short_content(self):
        """Test form validation for content that's too short."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'Short'  # Less than 10 characters
        }
        form = HistoryAndPhysicalForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_form_save_with_user(self):
        """Test form save method with user."""
        form_data = {
            'event_datetime': timezone.now(),
            'content': 'This is a test history and physical content with enough characters.'
        }
        form = HistoryAndPhysicalForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

        historyandphysical = form.save()
        self.assertEqual(historyandphysical.created_by, self.user)
        self.assertEqual(historyandphysical.updated_by, self.user)

    def test_form_crispy_helper_configuration(self):
        """Test crispy forms helper configuration."""
        form = HistoryAndPhysicalForm(user=self.user)
        self.assertIsNotNone(form.helper)
        self.assertEqual(form.helper.form_method, 'post')
        self.assertEqual(form.helper.form_class, 'needs-validation')

    def test_form_field_configuration(self):
        """Test form field configuration."""
        form = HistoryAndPhysicalForm(user=self.user)

        # Test help text
        self.assertEqual(form.fields['content'].help_text, "Conteúdo detalhado da anamnese e exame físico (suporte a Markdown)")

        # Test widget configuration - check if widget is DateTimeInput
        self.assertIsInstance(form.fields['event_datetime'].widget, forms.DateTimeInput)
        self.assertEqual(form.fields['content'].widget.attrs['id'], 'id_content')