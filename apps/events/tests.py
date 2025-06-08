from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.contrib import admin
from apps.events.models import Event
from apps.events.admin import EventAdmin
from apps.events.forms import EventForm
from apps.patients.models import Patient
import uuid

User = get_user_model()


class EventsAppConfigTest(TestCase):
    def test_app_config(self):
        from apps.events.apps import EventsConfig
        self.assertEqual(EventsConfig.name, 'apps.events')


class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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

        cls.event = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_event_creation(self):
        self.assertEqual(self.event.description, 'Test Event')
        self.assertEqual(self.event.event_type, Event.SIMPLE_NOTE_EVENT)
        self.assertEqual(self.event.patient, self.patient)

    def test_event_str_method(self):
        self.assertEqual(str(self.event), 'Test Event')

    def test_event_ordering(self):
        event2 = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event 2',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        events = Event.objects.all()
        self.assertEqual(events[0], event2)
        self.assertEqual(events[1], self.event)


class AdminSiteTest(TestCase):
    def test_event_model_registered(self):
        self.assertTrue(isinstance(admin.site._registry.get(Event), EventAdmin))

    def test_event_admin_list_display(self):
        event_admin = admin.site._registry.get(Event)
        self.assertEqual(
            event_admin.list_display,
            ('description', 'event_type', 'event_datetime', 'patient', 'created_by', 'created_at')
        )


class EventFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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

    def test_event_form_valid_data(self):
        form = EventForm(data={
            'event_type': Event.SIMPLE_NOTE_EVENT,
            'event_datetime': timezone.now(),
            'description': 'Test Event',
            'patient': self.patient.id,
        })
        self.assertTrue(form.is_valid())

    def test_event_form_invalid_data(self):
        form = EventForm(data={
            'event_type': Event.SIMPLE_NOTE_EVENT,
            'event_datetime': '',
            'description': 'Test Event',
            'patient': self.patient.id,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)


class EventViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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

        for i in range(15):
            Event.objects.create(
                event_type=Event.SIMPLE_NOTE_EVENT,
                event_datetime=timezone.now(),
                description=f'Test Event {i}',
                patient=cls.patient,
                created_by=cls.user,
                updated_by=cls.user
            )

    def setUp(self):
        self.client.login(username='testuser', password='testpass123')

    def test_patient_events_list_view(self):
        url = reverse('events:patient_events_list', args=[self.patient.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/patient_events_list.html')
        self.assertEqual(len(response.context['events']), 10)

    def test_user_events_list_view(self):
        url = reverse('events:user_events_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/user_events_list.html')
        self.assertEqual(len(response.context['events']), 10)

    def test_login_required(self):
        self.client.logout()

        patient_url = reverse('events:patient_events_list', args=[self.patient.id])
        user_url = reverse('events:user_events_list')

        patient_response = self.client.get(patient_url)
        user_response = self.client.get(user_url)

        self.assertEqual(patient_response.status_code, 302)
        self.assertEqual(user_response.status_code, 302)


class EventTemplatesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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

        cls.event = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpass123')

    def test_patient_events_list_template_content(self):
        url = reverse('events:patient_events_list', args=[self.patient.id])
        response = self.client.get(url)

        self.assertContains(response, 'Eventos do Paciente: Test Patient')
        self.assertContains(response, 'Test Event')
        self.assertContains(response, 'Nota/Observação')

    def test_user_events_list_template_content(self):
        url = reverse('events:user_events_list')
        response = self.client.get(url)

        self.assertContains(response, 'Meus Eventos')
        self.assertContains(response, 'Test Event')
        self.assertContains(response, 'Test Patient')
