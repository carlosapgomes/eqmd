# Events App Implementation Plan

## Vertical Slice 1: App Setup and Basic Configuration

### Step 1: Create and Configure the Events App

1. Create the events app structure:

   ```bash
   python manage.py startapp events apps/events
   ```

2. Add the app to INSTALLED_APPS in config/settings.py:

```python path=config/settings.py mode=EDIT
INSTALLED_APPS = [
    # ...
    'apps.events',
    # ...
]
```

1. Verify app configuration:

   ```bash
   python manage.py shell -c "from apps.events import apps; print(apps.EventsConfig)"
   ```

### Step 2: Basic App Configuration Verification

1. Create a simple test to verify app configuration:

```python path=apps/events/tests.py mode=EDIT
from django.test import TestCase

class EventsAppConfigTest(TestCase):
    def test_app_config(self):
        """Test that the events app is properly configured"""
        from apps.events.apps import EventsConfig
        self.assertEqual(EventsConfig.name, 'apps.events')
```

1. Run the test to verify configuration:

   ```bash
   pytest apps/events/tests.py::EventsAppConfigTest -v
   ```

## Vertical Slice 2: Event Model Implementation

### Step 1: Create the Event Model

```python path=apps/events/models.py mode=EDIT
import uuid
from django.db import models
from django.conf import settings
from model_utils.managers import InheritanceManager

class Event(models.Model):
    HISTORY_AND_PHYSICAL_EVENT = 0
    DAILY_NOTE_EVENT = 1
    SIMPLE_NOTE_EVENT = 2
    PHOTO_EVENT = 3
    EXAM_RESULT_EVENT = 4
    EXAMS_REQUEST_EVENT = 5
    DISCHARGE_REPORT_EVENT = 6
    OUTPT_PRESCRIPTION_EVENT = 7
    REPORT_EVENT = 8
    PHOTO_SERIES_EVENT = 9

    EVENT_TYPE_CHOICES = (
        (HISTORY_AND_PHYSICAL_EVENT, "Anamnese e Exame Físico"),
        (DAILY_NOTE_EVENT, "Evolução"),
        (SIMPLE_NOTE_EVENT, "Nota/Observação"),
        (PHOTO_EVENT, "Imagem"),
        (EXAM_RESULT_EVENT, "Resultado de Exame"),
        (EXAMS_REQUEST_EVENT, "Requisição de Exame"),
        (DISCHARGE_REPORT_EVENT, "Relatório de Alta"),
        (OUTPT_PRESCRIPTION_EVENT, "Receita"),
        (REPORT_EVENT, "Relatório"),
        (PHOTO_SERIES_EVENT, "Série de Fotos"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.PositiveSmallIntegerField(
        choices=EVENT_TYPE_CHOICES, verbose_name="Tipo de Evento"
    )
    event_datetime = models.DateTimeField(verbose_name="Data e Hora do Evento")
    description = models.CharField(max_length=255, verbose_name="Descrição")
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, verbose_name="Paciente"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_set",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_updated",
        verbose_name="Atualizado por",
    )

    objects = InheritanceManager()

    def __str__(self):
        return str(self.description)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        permissions = [
            ("edit_own_event_24h", "Can edit own events within 24 hours"),
            ("delete_own_event_24h", "Can delete own events within 24 hours"),
        ]
```

### Step 2: Verify Model Configuration

1. Create migrations:

   ```bash
   python manage.py makemigrations events
   ```

2. Verify model can be imported:

   ```bash
   python manage.py shell -c "from apps.events.models import Event; print(Event.EVENT_TYPE_CHOICES)"
   ```

### Step 3: Create Model Tests

```python path=apps/events/tests.py mode=EDIT
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.events.models import Event
from apps.patients.models import Patient
import uuid

User = get_user_model()

class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test patient
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,  # Assuming 1 is a valid status
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create a test event
        cls.event = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_event_creation(self):
        """Test the basic event creation"""
        self.assertEqual(self.event.description, 'Test Event')
        self.assertEqual(self.event.event_type, Event.SIMPLE_NOTE_EVENT)
        self.assertEqual(self.event.patient, self.patient)

    def test_event_str_method(self):
        """Test the string representation of an event"""
        self.assertEqual(str(self.event), 'Test Event')

    def test_event_ordering(self):
        """Test that events are ordered by created_at in descending order"""
        # Create a second event
        event2 = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event 2',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        events = Event.objects.all()
        self.assertEqual(events[0], event2)  # Newest event should be first
        self.assertEqual(events[1], self.event)
```

## Vertical Slice 3: Admin Interface

### Step 1: Create Admin Interface

```python path=apps/events/admin.py mode=EDIT
from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('description', 'event_type', 'event_datetime', 'patient', 'created_by', 'created_at')
    list_filter = ('event_type', 'created_at', 'event_datetime')
    search_fields = ('description', 'patient__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_queryset(self, request):
        # Use InheritanceManager to get the actual subclass instances
        return super().get_queryset(request).select_related(
            'patient', 'created_by', 'updated_by'
        )
```

### Step 2: Verify Admin Interface

1. Run the development server:

   ```bash
   python manage.py runserver
   ```

2. Access the admin interface at <http://localhost:8000/admin/> and verify the Event model is registered.

3. Create a test for admin registration:

```python path=apps/events/tests.py mode=EDIT
from django.contrib import admin
from apps.events.models import Event
from apps.events.admin import EventAdmin

class AdminSiteTest(TestCase):
    def test_event_model_registered(self):
        """Test that the Event model is registered with the admin site"""
        self.assertTrue(isinstance(admin.site._registry.get(Event), EventAdmin))

    def test_event_admin_list_display(self):
        """Test the list_display in the EventAdmin"""
        event_admin = admin.site._registry.get(Event)
        self.assertEqual(
            event_admin.list_display,
            ('description', 'event_type', 'event_datetime', 'patient', 'created_by', 'created_at')
        )
```

## Vertical Slice 4: Forms Implementation

### Step 1: Create Forms

```python path=apps/events/forms.py mode=EDIT
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['event_type', 'event_datetime', 'description', 'patient']
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-primary'))

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        self.helper.layout = Layout(
            Row(
                Column('event_type', css_class='form-group col-md-6 mb-0'),
                Column('event_datetime', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            'patient',
        )
```

### Step 2: Test Forms

```python path=apps/events/tests.py mode=EDIT
from django.utils import timezone
from apps.events.forms import EventForm

class EventFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test patient
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_event_form_valid_data(self):
        """Test form with valid data"""
        form = EventForm(data={
            'event_type': Event.SIMPLE_NOTE_EVENT,
            'event_datetime': timezone.now(),
            'description': 'Test Event',
            'patient': self.patient.id,
        })
        self.assertTrue(form.is_valid())

    def test_event_form_invalid_data(self):
        """Test form with invalid data"""
        form = EventForm(data={
            'event_type': Event.SIMPLE_NOTE_EVENT,
            'event_datetime': '',  # Missing required field
            'description': 'Test Event',
            'patient': self.patient.id,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)
```

## Vertical Slice 5: URLs and Views Implementation

### Step 1: Create URLs

```python path=apps/events/urls.py mode=EDIT
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('patient/<uuid:patient_id>/', views.patient_events_list, name='patient_events_list'),
    path('user/', views.user_events_list, name='user_events_list'),
]
```

### Step 2: Add URLs to Main URLs Configuration

```python path=config/urls.py mode=EDIT
# Add to existing urlpatterns
path('events/', include('apps.events.urls', namespace='events')),
```

### Step 3: Create Views

```python path=apps/events/views.py mode=EDIT
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Event
from apps.patients.models import Patient

@login_required
def patient_events_list(request, patient_id):
    """
    Display a list of events for a specific patient with pagination.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    events_list = Event.objects.filter(patient=patient).select_subclasses()

    # Pagination
    paginator = Paginator(events_list, 10)  # Show 10 events per page
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    return render(request, 'events/patient_events_list.html', {
        'patient': patient,
        'events': events,
    })

@login_required
def user_events_list(request):
    """
    Display a list of events created or updated by the current user with pagination.
    """
    # Get events created or updated by the current user
    events_list = Event.objects.filter(
        created_by=request.user
    ).select_subclasses() | Event.objects.filter(
        updated_by=request.user
    ).select_subclasses().distinct()

    # Pagination
    paginator = Paginator(events_list, 10)  # Show 10 events per page
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    return render(request, 'events/user_events_list.html', {
        'events': events,
    })
```

### Step 4: Test Views

```python path=apps/events/tests.py mode=EDIT
from django.urls import reverse

class EventViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test patient
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create multiple test events
        for i in range(15):  # Create 15 events to test pagination
            Event.objects.create(
                event_type=Event.SIMPLE_NOTE_EVENT,
                event_datetime=timezone.now(),
                description=f'Test Event {i}',
                patient=cls.patient,
                created_by=cls.user,
                updated_by=cls.user
            )

    def setUp(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass123')

    def test_patient_events_list_view(self):
        """Test the patient events list view"""
        url = reverse('events:patient_events_list', args=[self.patient.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/patient_events_list.html')
        self.assertEqual(len(response.context['events']), 10)  # First page should have 10 items

    def test_user_events_list_view(self):
        """Test the user events list view"""
        url = reverse('events:user_events_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/user_events_list.html')
        self.assertEqual(len(response.context['events']), 10)  # First page should have 10 items

    def test_login_required(self):
        """Test that login is required for views"""
        # Log out the user
        self.client.logout()

        # Try to access the views
        patient_url = reverse('events:patient_events_list', args=[self.patient.id])
        user_url = reverse('events:user_events_list')

        patient_response = self.client.get(patient_url)
        user_response = self.client.get(user_url)

        # Should redirect to login page
        self.assertEqual(patient_response.status_code, 302)
        self.assertEqual(user_response.status_code, 302)
```

## Vertical Slice 6: Templates Implementation

### Step 1: Create Base Templates Directory

```bash
mkdir -p apps/events/templates/events
```

### Step 2: Create Patient Events List Template

```html path=apps/events/templates/events/patient_events_list.html mode=EDIT
{% extends "base.html" %} {% load static %} {% block title %}Eventos do Paciente
- {{ patient.name }}{% endblock %} {% block content %}
<div class="container mt-4">
  <div class="row mb-4">
    <div class="col">
      <h1>Eventos do Paciente: {{ patient.name }}</h1>
      <p class="text-muted">
        Visualizando todos os eventos registrados para este paciente.
      </p>
    </div>
  </div>

  <div class="card shadow-sm mb-4">
    <div class="card-header bg-light">
      <h5 class="card-title mb-0">Lista de Eventos</h5>
    </div>
    <div class="card-body">
      {% if events %}
      <div class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Data e Hora</th>
              <th>Descrição</th>
              <th>Criado por</th>
              <th>Criado em</th>
            </tr>
          </thead>
          <tbody>
            {% for event in events %}
            <tr>
              <td>{{ event.get_event_type_display }}</td>
              <td>{{ event.event_datetime|date:"d/m/Y H:i" }}</td>
              <td>{{ event.description }}</td>
              <td>
                {{
                event.created_by.get_full_name|default:event.created_by.username
                }}
              </td>
              <td>{{ event.created_at|date:"d/m/Y H:i" }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {% if events.has_other_pages %}
      <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
          {% if events.has_previous %}
          <li class="page-item">
            <a
              class="page-link"
              href="?page={{ events.previous_page_number }}"
              aria-label="Previous"
            >
              <span aria-hidden="true">&laquo;</span>
            </a>
          </li>
          {% else %}
          <li class="page-item disabled">
            <span class="page-link" aria-hidden="true">&laquo;</span>
          </li>
          {% endif %} {% for num in events.paginator.page_range %} {% if
          events.number == num %}
          <li class="page-item active">
            <span class="page-link">{{ num }}</span>
          </li>
          {% else %}
          <li class="page-item">
            <a class="page-link" href="?page={{ num }}">{{ num }}</a>
          </li>
          {% endif %} {% endfor %} {% if events.has_next %}
          <li class="page-item">
            <a
              class="page-link"
              href="?page={{ events.next_page_number }}"
              aria-label="Next"
            >
              <span aria-hidden="true">&raquo;</span>
            </a>
          </li>
          {% else %}
          <li class="page-item disabled">
            <span class="page-link" aria-hidden="true">&raquo;</span>
          </li>
          {% endif %}
        </ul>
      </nav>
      {% endif %} {% else %}
      <div class="alert alert-info">
        Nenhum evento encontrado para este paciente.
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

### Step 3: Create User Events List Template

```html path=apps/events/templates/events/user_events_list.html mode=EDIT
{% extends "base.html" %} {% load static %} {% block title %}Meus Eventos{%
endblock %} {% block content %}
<div class="container mt-4">
  <div class="row mb-4">
    <div class="col">
      <h1>Meus Eventos</h1>
      <p class="text-muted">
        Visualizando todos os eventos que você criou ou atualizou.
      </p>
    </div>
  </div>

  <div class="card shadow-sm mb-4">
    <div class="card-header bg-light">
      <h5 class="card-title mb-0">Lista de Eventos</h5>
    </div>
    <div class="card-body">
      {% if events %}
      <div class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Data e Hora</th>
              <th>Descrição</th>
              <th>Paciente</th>
              <th>Criado em</th>
            </tr>
          </thead>
          <tbody>
            {% for event in events %}
            <tr>
              <td>{{ event.get_event_type_display }}</td>
              <td>{{ event.event_datetime|date:"d/m/Y H:i" }}</td>
              <td>{{ event.description }}</td>
              <td>{{ event.patient.name }}</td>
              <td>{{ event.created_at|date:"d/m/Y H:i" }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {% if events.has_other_pages %}
      <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
          {% if events.has_previous %}
          <li class="page-item">
            <a
              class="page-link"
              href="?page={{ events.previous_page_number }}"
              aria-label="Previous"
            >
              <span aria-hidden="true">&laquo;</span>
            </a>
          </li>
          {% else %}
          <li class="page-item disabled">
            <span class="page-link" aria-hidden="true">&laquo;</span>
          </li>
          {% endif %} {% for num in events.paginator.page_range %} {% if
          events.number == num %}
          <li class="page-item active">
            <span class="page-link">{{ num }}</span>
          </li>
          {% else %}
          <li class="page-item">
            <a class="page-link" href="?page={{ num }}">{{ num }}</a>
          </li>
          {% endif %} {% endfor %} {% if events.has_next %}
          <li class="page-item">
            <a
              class="page-link"
              href="?page={{ events.next_page_number }}"
              aria-label="Next"
            >
              <span aria-hidden="true">&raquo;</span>
            </a>
          </li>
          {% else %}
          <li class="page-item disabled">
            <span class="page-link" aria-hidden="true">&raquo;</span>
          </li>
          {% endif %}
        </ul>
      </nav>
      {% endif %} {% else %}
      <div class="alert alert-info">
        Você ainda não criou ou atualizou nenhum evento.
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

### Step 4: Test Templates

```python path=apps/events/tests.py mode=EDIT
class EventTemplatesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create a test patient
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create a test event
        cls.event = Event.objects.create(
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description='Test Event',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass123')

    def test_patient_events_list_template_content(self):
        """Test the content of the patient events list template"""
        url = reverse('events:patient_events_list', args=[self.patient.id])
        response = self.client.get(url)

        self.assertContains(response, 'Eventos do Paciente: Test Patient')
        self.assertContains(response, 'Test Event')
        self.assertContains(response, 'Nota/Observação')  # Event type display name

    def test_user_events_list_template_content(self):
        """Test the content of the user events list template"""
        url = reverse('events:user_events_list')
        response = self.client.get(url)

        self.assertContains(response, 'Meus Eventos')
        self.assertContains(response, 'Test Event')
        self.assertContains(response, 'Test Patient')  # Patient name
```

## Vertical Slice 7: Documentation and Final Testing

### Step 1: Create Documentation

````markdown path=docs/events/index.md mode=EDIT
# Events App Documentation

The Events app provides a base structure for all event types in the EquipeMed system. Events represent various medical records and activities related to patients.

## Event Types

The system supports the following event types:

- **Anamnese e Exame Físico** (History and Physical)
- **Evolução** (Daily Note)
- **Nota/Observação** (Simple Note)
- **Imagem** (Photo)
- **Resultado de Exame** (Exam Result)
- **Requisição de Exame** (Exams Request)
- **Relatório de Alta** (Discharge Report)
- **Receita** (Outpatient Prescription)
- **Relatório** (Report)
- **Série de Fotos** (Photo Series)

## Base Event Model

The `Event` model serves as a base model from which all specific event types will inherit. It contains common fields like:

- Event type
- Event date and time
- Description
- Patient reference
- Creation and update information

## Views

The Events app provides two main views:

1. **Patient Events List**: Displays all events for a specific patient
2. **User Events List**: Displays all events created or updated by the current user

Both views include pagination for better performance with large datasets.

## Permissions

The Events app includes custom permissions:

- `edit_own_event_24h`: Allows users to edit their own events within 24 hours of creation
- `delete_own_event_24h`: Allows users to delete their own events within 24 hours of creation

## Extending the Events App

Specific event types should be implemented in separate apps that extend the base `Event` model. For example:

```python
from apps.events.models import Event

class DailyNote(Event):
    # Additional fields specific to daily notes
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        self.event_type = self.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)
```
````

### Step 2: Create Test Documentation

````markdown path=docs/events/testing.md mode=EDIT
# Events App Testing Guide

## Test Configuration

### Test Settings

Ensure the events app is properly included in test settings:

```python
# In config/test_settings.py
INSTALLED_APPS = [
    # ...
    'apps.events',
    # ...
]
```

### Verifying App Configuration

You can verify the app is properly configured using the Django shell:

```bash
python manage.py shell -c "from apps.events.models import Event"
```

If no error occurs, the app is properly configured.

## Running Tests

### Using pytest (Recommended)

```bash
pytest apps/events/tests.py -v --no-cov
```

### Using Django Test Runner (Alternative)

```bash
python manage.py test apps.events.tests
```

## Test Coverage

The tests cover:

1. **Model Tests**:

   - Basic model creation
   - String representation
   - Ordering

2. **Admin Tests**:

   - Admin registration
   - Admin configuration

3. **Form Tests**:

   - Form validation with valid data
   - Form validation with invalid data

4. **View Tests**:

   - Authentication requirements
   - Context data
   - Pagination
   - Template usage

5. **Template Tests**:
   - Content rendering
   - Pagination controls
   - Empty state handling

## Writing Tests for Event Subclasses

When creating a new event type that extends the base Event model, follow this pattern:

```python
from django.test import TestCase
from apps.events.models import Event
from .models import YourEventType

class YourEventTypeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test data
        # ...

    def test_event_type_set_correctly(self):
        """Test that the event_type is set correctly on save"""
        event = YourEventType.objects.create(
            # required fields
        )
        self.assertEqual(event.event_type, Event.YOUR_EVENT_TYPE)
```
````

### Step 3: Create Deployment Documentation

````markdown path=docs/events/deployment.md mode=EDIT
# Events App Deployment Guide

## Pre-Deployment Checklist

- [ ] Run all tests and verify they pass:
  ```bash
  pytest apps/events/
  ```
- [ ] Check for any pending migrations:
  ```bash
  python manage.py showmigrations events
  ```
- [ ] Verify permissions are correctly set up:
  ```bash
  python manage.py shell -c "from django.contrib.auth.models import Permission; print(Permission.objects.filter(codename__in=['edit_own_event_24h', 'delete_own_event_24h']).values('codename', 'name'))"
  ```

## Deployment Steps

1. **Update Code**

   - [ ] Pull latest code from repository
   - [ ] Install any new dependencies: `uv sync`

2. **Database Updates**

   - [ ] Run migrations: `python manage.py migrate events`

3. **Static Files**

   - [ ] Collect static files: `python manage.py collectstatic --noinput`

4. **Restart Services**
   - [ ] Restart web server: `sudo systemctl restart gunicorn`
   - [ ] Restart web server: `sudo systemctl restart nginx`

## Post-Deployment Verification

- [ ] Verify the events app is accessible
- [ ] Test viewing patient events
- [ ] Test viewing user events
- [ ] Check permissions work correctly for different user roles
- [ ] Monitor error logs for any issues:
  ```bash
  tail -f /var/log/nginx/error.log
  tail -f /path/to/django/logs/error.log
  ```

## Rollback Plan

If issues are encountered during deployment:

1. **Revert Database Changes**

   - [ ] Roll back migrations: `python manage.py migrate events 0001_initial`

2. **Revert Code**

   - [ ] Check out previous version: `git checkout <previous-commit>`
   - [ ] Reinstall dependencies: `uv sync`

3. **Restart Services**
   - [ ] Restart web server: `sudo systemctl restart gunicorn`
   - [ ] Restart web server: `sudo systemctl restart nginx`
````

### Step 4: Final Integration Tests

```python path=apps/events/tests/test_integration.py mode=EDIT
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()

class EventsIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test users
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        cls.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )

        # Create test patients
        cls.patient1 = Patient.objects.create(
            name='Patient One',
            birthday='1990-01-01',
            status=1,
            created_by=cls.admin_user,
            updated_by=cls.admin_user
        )

        cls.patient2 = Patient.objects.create(
            name='Patient Two',
            birthday='1985-05-15',
            status=1,
            created_by=cls.admin_user,
            updated_by=cls.admin_user
        )

        # Create events for each patient
        for i in range(5):
            Event.objects.create(
                event_type=Event.SIMPLE_NOTE_EVENT,
                event_datetime=timezone.now(),
                description=f'Patient One Event {i}',
                patient=cls.patient1,
                created_by=cls.admin_user,
                updated_by=cls.admin_user
            )

            Event.objects.create(
                event_type=Event.DAILY_NOTE_EVENT,
                event_datetime=timezone.now(),
                description=f'Patient Two Event {i}',
                patient=cls.patient2,
                created_by=cls.regular_user,
                updated_by=cls.regular_user
            )

    def test_admin_can_see_all_events(self):
        """Test that admin users can see all events"""
        self.client.login(username='admin', password='adminpass123')

        # Check admin can see all their events
        url = reverse('events:user_events_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)  # Should see their 5 events

        # Check admin can see patient1's events
        url = reverse('events:patient_events_list', args=[self.patient1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)

        # Check admin can see patient2's events
        url = reverse('events:patient_events_list', args=[self.patient2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)

    def test_regular_user_can_see_own_events(self):
        """Test that regular users can see their own events"""
        self.client.login(username='regular', password='regularpass123')

        # Check regular user can see all their events
        url = reverse('events:user_events_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)  # Should see their 5 events

        # Check regular user can see patient2's events (which they created)
        url = reverse('events:patient_events_list', args=[self.patient2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)

        # Check regular user can see patient1's events (which they didn't create)
        url = reverse('events:patient_events_list', args=[self.patient1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 5)
```

### Step 5: Update README.md with Events App Information

```markdown path=README.md mode=EDIT
# EquipeMed

EquipeMed is a Django 5-based medical team collaboration platform for tracking patients across multiple hospitals.

## Events App

The Events app provides a foundation for all medical record events in the system:

- Base Event model for all medical record types
- Support for multiple event types (notes, exams, prescriptions, etc.)
- Patient-centric event views
- User-centric event views
- Custom permissions for event management
- Extensible architecture for specialized event types

## Patients App

The Patients app provides comprehensive patient management functionality:

- Patient registration and tracking
- Hospital record management
- Patient status tracking (inpatient, outpatient, deceased)
- Tagging system for patient categorization
- Dashboard integration with patient statistics
```

### Step 6: Final Verification

1. Run all tests to ensure everything works:

   ```bash
   pytest apps/events/
   ```

2. Check for any missing migrations:

   ```bash
   python manage.py makemigrations --check
   ```

3. Verify the app is properly registered:

   ```bash
   python manage.py shell -c "from django.apps import apps; print(apps.is_installed('apps.events'))"
   ```

4. Run the development server and manually test the views:

   ```bash
   python manage.py runserver
   ```

## Vertical Slice 8: Event Extension Example

### Step 1: Create a Sample Event Extension

```python path=apps/events/examples.py mode=EDIT
"""
This module provides examples of how to extend the base Event model.
These are not meant to be used in production, but serve as reference
implementations for developers creating new event types.
"""

from django.db import models
from .models import Event

class DailyNoteEvent(Event):
    """
    Example implementation of a Daily Note event type.
    """
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        # Always set the correct event type
        self.event_type = self.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"


class ExamResultEvent(Event):
    """
    Example implementation of an Exam Result event type.
    """
    exam_type = models.CharField(max_length=100, verbose_name="Tipo de Exame")
    result = models.TextField(verbose_name="Resultado")
    attachment = models.FileField(upload_to='exam_results/', blank=True, null=True,
                                 verbose_name="Anexo")

    def save(self, *args, **kwargs):
        # Always set the correct event type
        self.event_type = self.EXAM_RESULT_EVENT
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Resultado de Exame"
        verbose_name_plural = "Resultados de Exames"
```

### Step 2: Create Extension Documentation

````markdown path=docs/events/extending.md mode=EDIT
# Extending the Events App

The Events app is designed to be extended with specific event types. This guide explains how to create new event types that inherit from the base `Event` model.

## Creating a New Event Type

To create a new event type:

1. Create a new model that inherits from `Event`
2. Add fields specific to your event type
3. Override the `save()` method to set the correct `event_type`
4. Register the model with the admin site

## Example Implementation

Here's an example of a Daily Note event type:

```python
from django.db import models
from apps.events.models import Event

class DailyNoteEvent(Event):
    """
    Implementation of a Daily Note event type.
    """
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        # Always set the correct event type
        self.event_type = self.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
```

## Admin Registration

Register your new event type with the admin site:

```python
from django.contrib import admin
from .models import DailyNoteEvent

@admin.register(DailyNoteEvent)
class DailyNoteEventAdmin(admin.ModelAdmin):
    list_display = ('description', 'event_datetime', 'patient', 'created_by', 'created_at')
    list_filter = ('event_datetime', 'created_at')
    search_fields = ('description', 'content', 'patient__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
```

## Form Implementation

Create a form for your event type:

```python
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import DailyNoteEvent

class DailyNoteEventForm(forms.ModelForm):
    class Meta:
        model = DailyNoteEvent
        fields = ['event_datetime', 'description', 'patient', 'content']
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'content': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-primary'))

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
```

## View Implementation

Create views for your event type:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from .models import DailyNoteEvent
from .forms import DailyNoteEventForm

@login_required
def create_daily_note(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = DailyNoteEventForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.created_by = request.user
            note.updated_by = request.user
            note.save()
            return redirect('events:patient_events_list', patient_id=patient.id)
    else:
        form = DailyNoteEventForm(initial={'patient': patient})

    return render(request, 'events/daily_note_form.html', {
        'form': form,
        'patient': patient,
    })
```

## Template Implementation

Create templates for your event type:

```html
{% extends "base.html" %} {% load crispy_forms_tags %} {% block title %}Nova
Evolução - {{ patient.name }}{% endblock %} {% block content %}
<div class="container mt-4">
  <div class="row mb-4">
    <div class="col">
      <h1>Nova Evolução</h1>
      <p class="text-muted">Paciente: {{ patient.name }}</p>
    </div>
  </div>

  <div class="card shadow-sm mb-4">
    <div class="card-header bg-light">
      <h5 class="card-title mb-0">Formulário de Evolução</h5>
    </div>
    <div class="card-body">{% crispy form %}</div>
  </div>
</div>
{% endblock %}
```
````

This completes the implementation plan for the Events app with all the necessary components:

1. Basic app setup and configuration
2. Event model implementation
3. Admin interface
4. Forms implementation
5. URLs and views implementation
6. Templates implementation
7. Documentation and testing
8. Event extension example

The implementation follows a vertical slicing approach, where each slice represents a complete, testable feature set. The app provides a solid foundation for all medical record events in the system and can be easily extended with specific event types.
