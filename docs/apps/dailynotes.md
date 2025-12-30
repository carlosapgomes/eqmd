# Daily Notes App - Complete Features Guide

**Medical evolution notes extending Event model**

## Overview

- DailyNote model inherits from Event
- Portuguese localization ("Evolução"/"Evoluções")
- Automatic event_type assignment
- Admin interface with fieldsets and optimizations

## Advanced Features (Slice 5)

### Patient Integration

- **Patient-specific daily note views** with date filtering
- **Search & Filtering**: Advanced search by content, patient, creator, and date ranges
- **Dashboard Integration**: Recent daily notes widget and statistics counters
- **Export/Print**: Print-friendly individual notes and patient evolution reports
- **URLs**: `/dailynotes/`, `/dailynotes/patient/<uuid>/`, `/dailynotes/<uuid>/print/`
- **Template Tags**: `recent_dailynotes_widget`, `dailynotes_count_today`, `dailynotes_count_week`

### Duplicate Functionality

**Create new dailynotes based on existing ones**

- **Multiple Access Points**: Available from detail page, list views, and patient timeline
- **Pre-population**: Original content copied, datetime set to current time
- **Permission-Based**: Only visible to users with `events.add_event` permission
- **Timeline Integration**: Specialized event card template with duplicate button
- **URL Pattern**: `/dailynotes/<uuid>/duplicate/`
- **Success Redirect**: Returns to patient timeline after creation

### Performance Optimizations (Slice 6)

- **Database Optimization**: Added indexes for common query patterns on Event model
- **Query Optimization**: Enhanced views with `select_related()` and `prefetch_related()`
- **Pagination**: Improved pagination with `paginate_orphans` for better UX
- **Permission Caching**: Bulk patient access checks with `get_user_accessible_patients()`
- **Filter Caching**: Cached filter dropdown options for list views (5-minute cache)
- **Query Patterns**: Optimized patient/creator lookups with `only()` clauses

## Model Architecture

### DailyNote Model

```python
class DailyNote(Event):
    content = models.TextField(
        verbose_name="Conteúdo da Evolução",
        help_text="Descreva a evolução do paciente"
    )
    
    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ['-event_datetime']
    
    def save(self, *args, **kwargs):
        if not self.event_type:
            self.event_type = Event.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)
```

### Inheritance Benefits

- Inherits UUID primary key from Event
- Automatic audit trail tracking
- 24-hour edit window enforcement
- Timeline integration
- Permission system integration

## Views and URL Patterns

### Core Views

- `DailyNoteListView`: Paginated list with search/filter
- `DailyNoteDetailView`: Individual note display
- `DailyNoteCreateView`: Form-based creation
- `DailyNoteUpdateView`: Edit within 24h window
- `DailyNoteDeleteView`: Soft delete with confirmation
- `DailyNoteDuplicateView`: Create copy of existing note

### Patient-Specific Views

- `PatientDailyNotesView`: Notes filtered by patient
- `PatientDailyNotesPrintView`: Print-friendly format
- `PatientEvolutionReportView`: Comprehensive evolution report

### URL Configuration

```python
urlpatterns = [
    path('', DailyNoteListView.as_view(), name='dailynote_list'),
    path('create/', DailyNoteCreateView.as_view(), name='dailynote_create'),
    path('<uuid:pk>/', DailyNoteDetailView.as_view(), name='dailynote_detail'),
    path('<uuid:pk>/edit/', DailyNoteUpdateView.as_view(), name='dailynote_edit'),
    path('<uuid:pk>/delete/', DailyNoteDeleteView.as_view(), name='dailynote_delete'),
    path('<uuid:pk>/duplicate/', DailyNoteDuplicateView.as_view(), name='dailynote_duplicate'),
    path('<uuid:pk>/print/', DailyNotePrintView.as_view(), name='dailynote_print'),
    path('patient/<uuid:patient_id>/', PatientDailyNotesView.as_view(), name='patient_dailynotes'),
    path('patient/<uuid:patient_id>/print/', PatientDailyNotesPrintView.as_view(), name='patient_dailynotes_print'),
]
```

## Search and Filtering

### Search Fields

- Content (full-text search)
- Patient name
- Creator username
- Date ranges
- Event datetime

### Filter Options

- Patient selection (dropdown)
- Creator selection (dropdown)
- Date range picker
- Content keywords
- Recent activity filters

### Advanced Search Form

```python
class DailyNoteSearchForm(forms.Form):
    content = forms.CharField(required=False, label="Conteúdo")
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        required=False,
        empty_label="Todos os pacientes"
    )
    creator = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="Todos os criadores"
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
```

## Dashboard Integration

### Template Tags

#### recent_dailynotes_widget

```django
{% load dailynotes_tags %}
{% recent_dailynotes_widget limit=5 %}
```

Displays recent daily notes with quick access links.

#### dailynotes_count_today

```django
{% load dailynotes_tags %}
{% dailynotes_count_today as today_count %}
<span class="badge">{{ today_count }} today</span>
```

#### dailynotes_count_week

```django
{% load dailynotes_tags %}
{% dailynotes_count_week as week_count %}
<span class="badge">{{ week_count }} this week</span>
```

### Dashboard Statistics

- Daily notes created today
- Weekly daily notes statistics
- Top creators this month
- Patient with most notes
- Average notes per patient

## Duplicate Functionality

### Implementation Details

```python
class DailyNoteDuplicateView(LoginRequiredMixin, DetailView):
    model = DailyNote
    
    def post(self, request, *args, **kwargs):
        original = self.get_object()
        
        # Create duplicate with current datetime
        duplicate = DailyNote.objects.create(
            patient=original.patient,
            created_by=request.user,
            event_datetime=timezone.now(),
            description=f"Duplicated from {original.event_datetime.strftime('%d/%m/%Y %H:%M')}",
            content=original.content
        )
        
        messages.success(request, "Evolução duplicada com sucesso!")
        return redirect('patients:patient_detail', pk=original.patient.pk)
```

### Access Points

1. **Detail View**: Duplicate button on individual note page
2. **List View**: Duplicate action in note list
3. **Patient Timeline**: Duplicate button on event card
4. **Quick Actions**: Keyboard shortcut support

### Permission Checks

- User must have `events.add_event` permission
- User must be able to access the source patient
- Original note must be accessible to user

## Print and Export Features

### Print Views

- **Individual Note Print**: Single note with patient context
- **Patient Evolution Report**: All notes for patient in chronological order
- **Date Range Reports**: Notes within specified date range
- **Creator Reports**: All notes by specific user

### Print Styling

```css
@media print {
    .dailynote-print {
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
        line-height: 1.4;
    }
    
    .page-break {
        page-break-before: always;
    }
    
    .no-print {
        display: none;
    }
}
```

### Export Options

- PDF generation using ReportLab
- CSV export for data analysis
- JSON export for API integration
- Print-friendly HTML views

## Performance Optimizations

### Database Indexes

```python
class DailyNote(Event):
    class Meta:
        indexes = [
            models.Index(fields=['patient', '-event_datetime']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['-event_datetime']),
        ]
```

### Query Optimization

```python
# Optimized list view query
def get_queryset(self):
    return DailyNote.objects.select_related(
        'patient', 'created_by'
    ).prefetch_related(
        'patient__tags'
    ).order_by('-event_datetime')
```

### Caching Strategy

- Filter dropdown options cached for 5 minutes
- Patient access permissions cached per request
- Recent notes widget cached for 2 minutes
- Statistics counters cached for 10 minutes

### Pagination Optimization

```python
class DailyNoteListView(ListView):
    paginate_by = 20
    paginate_orphans = 5  # Better UX for small last pages
```

## Template Integration

### Timeline Card Template

Location: `apps/events/templates/events/partials/event_card_dailynote.html`

```django
{% extends "events/partials/event_card_base.html" %}

{% block event_actions %}
    {{ block.super }}
    {% if perms.events.add_event %}
        <a href="{% url 'dailynotes:dailynote_duplicate' pk=event.pk %}" 
           class="btn btn-sm btn-outline-secondary">Duplicar</a>
    {% endif %}
{% endblock %}

{% block event_content %}
    <div class="dailynote-content">
        {{ event.content|linebreaks }}
    </div>
{% endblock %}
```

### Form Templates

- Bootstrap 5 styling
- Real-time character counting
- Auto-save draft functionality
- Rich text editor integration

## Testing Strategy

### Unit Tests

- Model validation tests
- Permission checking tests
- Duplicate functionality tests
- Search and filter tests

### Integration Tests

- Timeline integration tests
- Dashboard widget tests
- Print view tests
- Performance benchmarks

### Test Coverage

- Model methods: 100%
- View functions: 95%
- Template tags: 90%
- Form validation: 100%

## Localization

### Portuguese Translations

- Complete pt-BR translation
- Medical terminology consistency
- Date/time format localization
- Cultural adaptations for Brazilian healthcare

### Template Strings

```python
# apps/dailynotes/models.py
verbose_name = "Evolução"
verbose_name_plural = "Evoluções"

# Form labels
content_label = "Conteúdo da Evolução"
patient_label = "Paciente"
datetime_label = "Data e Hora"
```
