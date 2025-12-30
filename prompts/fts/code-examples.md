# Full Text Search Code Examples

**✅ UPDATED FOR USER PREFERENCES:**

- **Boolean field**: `is_researcher` instead of Django groups
- **All-word initials**: "João da Silva Santos" → "J.D.S.S."
- **Age calculation**: Age at most recent matching note
- **New menu section**: "Pesquisa Clínica" section for researchers only

## 0. User Model Extension (NEW)

### Updated User Model (`apps/accounts/models.py`)

```python
# Add this field to the EqmdCustomUser model

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    # Research access field (NEW)
    is_researcher = models.BooleanField(
        default=False,
        verbose_name="Pesquisador Clínico",
        help_text="Permite acesso à funcionalidade de pesquisa clínica em evoluções"
    )

    # ... rest of the model ...
```

### Updated User Admin (`apps/accounts/admin.py`)

```python
# Add to the fieldsets in the admin class

@admin.register(EqmdCustomUser)
class EqmdCustomUserAdmin(UserAdmin):
    fieldsets = (
        # ... existing fieldsets ...

        ('Informações Profissionais', {
            'fields': ('profession_type', 'license_number', 'workplace'),
        }),

        # NEW SECTION
        ('Permissões de Pesquisa', {
            'fields': ('is_researcher',),
            'description': 'Controla acesso às funcionalidades de pesquisa clínica'
        }),

        ('Dados de Acesso', {
            'fields': ('is_active', 'date_joined', 'last_login'),
        }),
    )

    # Add to list display and filters if needed
    list_display = (
        # ... existing fields ...
        'is_researcher',
    )

    list_filter = (
        # ... existing filters ...
        'is_researcher',
    )
```

## 1. DailyNote Model Updates

### Updated Model (`apps/dailynotes/models.py`)

```python
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from apps.events.models import Event

class DailyNote(Event):
    """
    Daily Note model that extends the base Event model.
    Used for medical daily evolution notes.
    """
    content = models.TextField(verbose_name="Conteúdo")

    # Full text search field
    search_vector = SearchVectorField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the daily note."""
        return f"Evolução - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-event_datetime"]
        indexes = [
            GinIndex(fields=['search_vector'], name='dailynote_search_gin_idx'),
        ]
```

### Signal Handler (`apps/dailynotes/signals.py`)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import DailyNote

@receiver(post_save, sender=DailyNote)
def update_search_vector(sender, instance, created, **kwargs):
    """
    Update search vector when DailyNote is saved.
    """
    # Avoid recursion by checking if search_vector was already updated
    if hasattr(instance, '_search_vector_updated'):
        return

    # Update the search vector
    sender.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('content', config='portuguese')
    )

    # Mark as updated to avoid recursion
    instance._search_vector_updated = True
```

### Apps Configuration (`apps/dailynotes/apps.py`)

```python
from django.apps import AppConfig

class DailynotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dailynotes'
    verbose_name = 'Daily Notes'

    def ready(self):
        import apps.dailynotes.signals
```

## 2. Management Command for Initial Population

### Command (`apps/dailynotes/management/commands/populate_search_vectors.py`)

```python
from django.core.management.base import BaseCommand, CommandError
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from apps.dailynotes.models import DailyNote

class Command(BaseCommand):
    help = 'Populate search vectors for existing DailyNote records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # Count total records needing update
        total_notes = DailyNote.objects.filter(search_vector__isnull=True).count()

        if total_notes == 0:
            self.stdout.write(
                self.style.SUCCESS('All DailyNote records already have search vectors.')
            )
            return

        self.stdout.write(f'Found {total_notes} DailyNote records to update')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {total_notes} records in batches of {batch_size}')
            )
            return

        processed = 0
        failed = 0

        self.stdout.write('Starting search vector population...')

        while True:
            # Get next batch
            notes_batch = list(
                DailyNote.objects.filter(search_vector__isnull=True)[:batch_size]
            )

            if not notes_batch:
                break

            try:
                with transaction.atomic():
                    # Update search vectors for this batch
                    for note in notes_batch:
                        DailyNote.objects.filter(pk=note.pk).update(
                            search_vector=SearchVector('content', config='portuguese')
                        )

                    processed += len(notes_batch)

                    # Progress update
                    self.stdout.write(
                        f'Processed {processed}/{total_notes} records '
                        f'({(processed/total_notes)*100:.1f}%)'
                    )

            except Exception as e:
                failed += len(notes_batch)
                self.stdout.write(
                    self.style.ERROR(f'Failed to process batch: {e}')
                )
                continue

        if failed > 0:
            self.stdout.write(
                self.style.WARNING(f'Completed with {failed} failed records')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {processed} DailyNote records')
            )
```

## 2. Research App Structure (UPDATED)

### Research App Configuration (`apps/research/apps.py`)

```python
from django.apps import AppConfig

class ResearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.research'
    verbose_name = 'Clinical Research'
```

### Updated Permissions (`apps/research/permissions.py`)

```python
from django.core.exceptions import PermissionDenied

def check_researcher_access(user):
    """
    Check if user has researcher access via is_researcher field.

    Args:
        user: The user to check

    Returns:
        bool: True if user has researcher access

    Raises:
        PermissionDenied: If user doesn't have access
    """
    if not user.is_authenticated:
        raise PermissionDenied("Você deve estar logado para acessar a pesquisa clínica.")

    # Check the is_researcher field
    if not getattr(user, 'is_researcher', False):
        raise PermissionDenied(
            "Você não tem permissão para acessar as funcionalidades de pesquisa clínica. "
            "Entre em contato com o administrador do sistema."
        )

    return True

def is_researcher(user):
    """
    Check if user is a researcher (non-raising version).

    Args:
        user: The user to check

    Returns:
        bool: True if user has researcher access, False otherwise
    """
    if not user.is_authenticated:
        return False

    return getattr(user, 'is_researcher', False)
```

### Search Utilities (`apps/research/utils.py`)

```python
from collections import defaultdict
import math
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from apps.dailynotes.models import DailyNote

def get_patient_initials(full_name):
    """
    Extract first letter of each word (including prepositions).
    Example: "João da Silva Santos" → "J.D.S.S."
    """
    if not full_name:
        return ""

    words = full_name.strip().split()

    # Get first letter of ALL words (including prepositions per user request)
    initials = []
    for word in words:
        if word:  # Only if word is not empty
            initials.append(word[0].upper())

    return '.'.join(initials) + '.' if initials else ""

def calculate_age_at_date(birthday, reference_date):
    """
    Calculate age at a specific reference date.
    """
    if not birthday or not reference_date:
        return None

    # Ensure reference_date is a date object
    if hasattr(reference_date, 'date'):
        reference_date = reference_date.date()

    age = reference_date.year - birthday.year

    # Adjust if birthday hasn't occurred yet in the reference year
    if (reference_date.month, reference_date.day) < (birthday.month, birthday.day):
        age -= 1

    return age

def calculate_age_at_most_recent_match(patient, matching_notes):
    """
    Calculate age at the most recent matching dailynote date.

    Args:
        patient: Patient object
        matching_notes: List of matching note dictionaries

    Returns:
        int: Age at most recent match, or None if no notes
    """
    if not matching_notes:
        return None

    # Get the most recent note from the matching results
    most_recent_note = max(matching_notes, key=lambda n: n['note_date'])
    most_recent_date = most_recent_note['note_date']

    # Ensure we have a date object
    if hasattr(most_recent_date, 'date'):
        most_recent_date = most_recent_date.date()

    return calculate_age_at_date(patient.birthday, most_recent_date)

def validate_search_query(query_text):
    """
    Validate and sanitize search query.

    Returns:
        tuple: (cleaned_query, error_message)
    """
    if not query_text or not query_text.strip():
        return None, "Query cannot be empty"

    # Remove excessive whitespace
    query_text = ' '.join(query_text.split())

    # Minimum length check
    if len(query_text) < 3:
        return None, "Query must be at least 3 characters"

    # Maximum length check
    if len(query_text) > 200:
        return None, "Query too long (maximum 200 characters)"

    return query_text, None

def perform_fulltext_search(query_text, page=1, per_page=25):
    """
    Perform full text search and return patient-grouped results.

    Args:
        query_text: The search query
        page: Page number for pagination
        per_page: Results per page

    Returns:
        dict: Search results with pagination info
    """
    # Validate query
    clean_query, error = validate_search_query(query_text)
    if error:
        return {'error': error}

    # Create PostgreSQL search query
    search_query = SearchQuery(clean_query, config='portuguese')

    # Query matching notes with ranking and headlines
    matching_notes = DailyNote.objects.annotate(
        rank=SearchRank('search_vector', search_query),
        headline=SearchHeadline(
            'content',
            search_query,
            config='portuguese',
            max_words=30,
            min_words=10,
            start_sel='<b>',
            stop_sel='</b>'
        )
    ).filter(
        search_vector=search_query
    ).select_related('patient').order_by('-rank')

    if not matching_notes.exists():
        return {
            'patients': [],
            'total_patients': 0,
            'query': query_text,
            'message': f'Nenhum resultado encontrado para "{query_text}"'
        }

    # Group notes by patient
    patient_groups = defaultdict(list)
    for note in matching_notes:
        patient_groups[note.patient].append({
            'note': note,
            'rank': note.rank,
            'headline': note.headline,
            'note_date': note.event_datetime
        })

    # Build patient results (UPDATED)
    patient_results = []
    for patient, notes in patient_groups.items():
        # Calculate age at most recent MATCHING note (UPDATED)
        age_at_recent_match = calculate_age_at_most_recent_match(patient, notes)

        # Get top 5 matches per patient
        top_matches = sorted(notes, key=lambda x: x['rank'], reverse=True)[:5]

        patient_results.append({
            'patient': patient,
            'registration_number': patient.current_record_number or 'N/A',
            'initials': get_patient_initials(patient.name),  # UPDATED function
            'gender': patient.get_gender_display(),
            'birthday': patient.birthday,
            'age_at_most_recent_match': age_at_recent_match,  # UPDATED field name
            'matching_notes': top_matches,
            'highest_rank': max(n['rank'] for n in notes),
            'total_matches': len(notes)
        })

    # Sort by highest rank
    patient_results.sort(key=lambda x: x['highest_rank'], reverse=True)

    # Implement pagination
    total_patients = len(patient_results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_results = patient_results[start_idx:end_idx]

    return {
        'patients': paginated_results,
        'total_patients': total_patients,
        'current_page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_patients / per_page),
        'has_next': end_idx < total_patients,
        'has_previous': page > 1,
        'query': query_text
    }
```

### Search Form (`apps/research/forms.py`)

```python
from django import forms

class ClinicalSearchForm(forms.Form):
    """
    Form for clinical research full text search.
    """
    query = forms.CharField(
        max_length=200,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite os termos de busca (ex: diabetes, hipertensão, medicação)',
            'autocomplete': 'off'
        }),
        label='Busca Clínica',
        help_text='Digite pelo menos 3 caracteres para buscar nas evoluções diárias'
    )

    def clean_query(self):
        query = self.cleaned_data.get('query')
        if query:
            query = ' '.join(query.split())  # Remove extra whitespace
        return query
```

### Search View (`apps/research/views.py`)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse

from .forms import ClinicalSearchForm
from .permissions import check_researcher_access
from .utils import perform_fulltext_search

@login_required
def clinical_search(request):
    """
    Clinical research full text search view.
    """
    # Check researcher permissions
    try:
        check_researcher_access(request.user)
    except PermissionDenied as e:
        messages.error(request, str(e))
        return render(request, 'research/access_denied.html')

    form = ClinicalSearchForm()
    results = None

    if request.method == 'POST':
        form = ClinicalSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            page = request.GET.get('page', 1)

            try:
                page = int(page)
            except (ValueError, TypeError):
                page = 1

            # Perform search
            results = perform_fulltext_search(query, page=page)

            if 'error' in results:
                messages.error(request, results['error'])
                results = None
            elif results['total_patients'] == 0:
                messages.info(request, results.get('message', 'Nenhum resultado encontrado'))

    context = {
        'form': form,
        'results': results,
        'page_title': 'Pesquisa Clínica'
    }

    return render(request, 'research/search.html', context)

@login_required
def search_ajax(request):
    """
    AJAX endpoint for search (optional for future enhancement).
    """
    try:
        check_researcher_access(request.user)
    except PermissionDenied:
        return JsonResponse({'error': 'Access denied'}, status=403)

    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))

    if not query:
        return JsonResponse({'error': 'Query required'}, status=400)

    results = perform_fulltext_search(query, page=page)

    # Convert results to JSON-serializable format
    if 'patients' in results:
        for patient_result in results['patients']:
            patient_result['patient'] = {
                'id': str(patient_result['patient'].pk),
                'name': patient_result['patient'].name
            }
            for match in patient_result['matching_notes']:
                match['note_date'] = match['note_date'].isoformat()

    return JsonResponse(results)
```

### URLs (`apps/research/urls.py`)

```python
from django.urls import path
from . import views

app_name = 'research'

urlpatterns = [
    path('', views.clinical_search, name='clinical_search'),
    path('search-ajax/', views.search_ajax, name='search_ajax'),
]
```

## 3. Updated Navigation Menu (UPDATED)

### Updated Base App Template (`templates/base_app.html`)

Add after Patient Management section (around line 158):

```html
<!-- Patient Management -->
<h6 class="sidebar-heading">Gestão de Pacientes</h6>
<ul class="nav flex-column">
  <!-- ... existing patient menu items ... -->
</ul>

<!-- Clinical Research Section (NEW) -->
{% if user.is_researcher %}
<h6 class="sidebar-heading">Pesquisa Clínica</h6>
<ul class="nav flex-column">
  <li class="nav-item">
    <a class="nav-link" href="{% url 'apps.research:clinical_search' %}">
      <i class="bi bi-search"></i>
      Busca em Evoluções
    </a>
  </li>
</ul>
{% endif %}
```

And in the mobile offcanvas section (around line 337):

```html
<!-- Patient Management -->
<h6 class="sidebar-heading">Gestão de Pacientes</h6>
<ul class="nav flex-column">
  <!-- ... existing patient menu items ... -->
</ul>

<!-- Clinical Research Section (Mobile - NEW) -->
{% if user.is_researcher %}
<h6 class="sidebar-heading">Pesquisa Clínica</h6>
<ul class="nav flex-column">
  <li class="nav-item">
    <a class="nav-link" href="{% url 'apps.research:clinical_search' %}">
      <i class="bi bi-search"></i>
      Busca em Evoluções
    </a>
  </li>
</ul>
{% endif %}
```

## 5. Database Migration

### Migration File (`apps/dailynotes/migrations/XXXX_add_search_vector.py`)

```python
from django.db import migrations
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Migration(migrations.Migration):
    dependencies = [
        ('dailynotes', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailynote',
            name='search_vector',
            field=SearchVectorField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='dailynote',
            index=GinIndex(
                fields=['search_vector'],
                name='dailynote_search_gin_idx'
            ),
        ),
    ]
```

## 6. Template Examples

### Main Search Template (`apps/research/templates/research/search.html`)

```html
{% extends "base_app.html" %}
{% load static %}

{% block extra_css %}
<style>
.search-snippet {
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-left: 3px solid #007bff;
    border-radius: 0.25rem;
    font-size: 0.9rem;
}

.search-snippet b {
    background-color: #ffeb3b;
    padding: 0.1rem 0.3rem;
    border-radius: 0.2rem;
    font-weight: bold;
}

.search-stats {
    background-color: #e3f2fd;
    border: 1px solid #bbdefb;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1.5rem;
}

.patient-row:hover {
    background-color: #f8f9fa;
}
</style>
{% endblock extra_css %}

{% block app_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><i class="bi bi-search me-2"></i>{{ page_title }}</h1>
</div>

<!-- Search Form -->
<div class="card mb-4">
    <div class="card-body">
        <form method="post" class="mb-0">
            {% csrf_token %}
            <div class="row align-items-end">
                <div class="col-md-10">
                    <label for="{{ form.query.id_for_label }}" class="form-label fw-bold">
                        {{ form.query.label }}
                    </label>
                    {{ form.query }}
                    {% if form.query.help_text %}
                        <div class="form-text">{{ form.query.help_text }}</div>
                    {% endif %}
                    {% if form.query.errors %}
                        <div class="text-danger">
                            {% for error in form.query.errors %}
                                <small>{{ error }}</small>
                            {% endfor %}
                        </div>
                    {% endif %}
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="bi bi-search me-1"></i>Buscar
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Search Results -->
{% if results %}
    <!-- Search Statistics -->
    <div class="search-stats">
        <div class="row">
            <div class="col-md-6">
                <h6 class="mb-1">Resultados da Busca</h6>
                <p class="mb-0">
                    <strong>{{ results.total_patients }}</strong> paciente{{ results.total_patients|pluralize }}
                    encontrado{{ results.total_patients|pluralize }} para "<em>{{ results.query }}</em>"
                </p>
            </div>
            <div class="col-md-6 text-md-end">
                <small class="text-muted">
                    Página {{ results.current_page }} de {{ results.total_pages }}
                </small>
            </div>
        </div>
    </div>

    <!-- Results Table -->
    <div class="card">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Prontuário</th>
                            <th>Iniciais</th>
                            <th>Sexo</th>
                            <th>Nascimento</th>
                            <th>Idade no Resultado</th> <!-- UPDATED -->
                            <th>Trechos Encontrados</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for patient_result in results.patients %}
                            <tr class="patient-row">
                                <td>
                                    <code>{{ patient_result.registration_number }}</code>
                                </td>
                                <td>
                                    <strong>{{ patient_result.initials }}</strong>
                                </td>
                                <td>{{ patient_result.gender }}</td>
                                <td>{{ patient_result.birthday|date:"d/m/Y" }}</td>
                                <td>
                                    <!-- UPDATED: Show age at most recent match -->
                                    {% if patient_result.age_at_most_recent_match %}
                                        {{ patient_result.age_at_most_recent_match }} anos
                                    {% else %}
                                        -
                                    {% endif %}
                                </td>
                                <td>
                                    {% for match in patient_result.matching_notes %}
                                        <div class="search-snippet">
                                            {{ match.headline|safe }}
                                            <div class="mt-1">
                                                <small class="text-muted">
                                                    <i class="bi bi-calendar3 me-1"></i>
                                                    {{ match.note_date|date:"d/m/Y H:i" }}
                                                </small>
                                            </div>
                                        </div>
                                    {% endfor %}
                                    {% if patient_result.total_matches > 5 %}
                                        <small class="text-muted">
                                            <i class="bi bi-three-dots me-1"></i>
                                            +{{ patient_result.total_matches|add:"-5" }} resultado{{ patient_result.total_matches|add:"-5"|pluralize }} adiciona{{ patient_result.total_matches|add:"-5"|pluralize:"l,is" }}
                                        </small>
                                    {% endif %}
                                </td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Pagination -->
    {% if results.total_pages > 1 %}
        <nav aria-label="Search results pagination" class="mt-4">
            <ul class="pagination justify-content-center">
                <!-- Previous Page -->
                {% if results.has_previous %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ results.current_page|add:"-1" }}">
                            <i class="bi bi-chevron-left"></i> Anterior
                        </a>
                    </li>
                {% else %}
                    <li class="page-item disabled">
                        <span class="page-link">
                            <i class="bi bi-chevron-left"></i> Anterior
                        </span>
                    </li>
                {% endif %}

                <!-- Page Numbers -->
                {% for page_num in results.total_pages|range %}
                    {% if page_num == results.current_page %}
                        <li class="page-item active">
                            <span class="page-link">{{ page_num }}</span>
                        </li>
                    {% else %}
                        <li class="page-item">
                            <a class="page-link" href="?page={{ page_num }}">{{ page_num }}</a>
                        </li>
                    {% endif %}
                {% endfor %}

                <!-- Next Page -->
                {% if results.has_next %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ results.current_page|add:"1" }}">
                            Próxima <i class="bi bi-chevron-right"></i>
                        </a>
                    </li>
                {% else %}
                    <li class="page-item disabled">
                        <span class="page-link">
                            Próxima <i class="bi bi-chevron-right"></i>
                        </span>
                    </li>
                {% endif %}
            </ul>
        </nav>
    {% endif %}

{% else %}
    <!-- No Search Performed Yet -->
    <div class="text-center py-5">
        <div class="text-muted">
            <i class="bi bi-search display-1"></i>
            <h4 class="mt-3">Pesquisa Clínica</h4>
            <p class="lead">Digite termos de busca para encontrar pacientes com evoluções relacionadas.</p>
            <div class="mt-4">
                <small class="text-muted">
                    <strong>Exemplos:</strong> diabetes, hipertensão, medicação, dor abdominal
                </small>
            </div>
        </div>
    </div>
{% endif %}

{% endblock app_content %}
```

This comprehensive set of code examples provides all the necessary components to implement the full text search functionality for clinical research in the EquipeMed system.
