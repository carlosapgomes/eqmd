# Discharge Reports - Technical Specifications

## Model Design

### DischargeReport Model
```python
class DischargeReport(Event):
    """Discharge report extending the base Event model"""
    
    # Date fields
    admission_date = models.DateField(
        verbose_name="Data de Admissão",
        help_text="Data da admissão hospitalar"
    )
    discharge_date = models.DateField(
        verbose_name="Data de Alta",
        help_text="Data da alta hospitalar"
    )
    
    # Text content fields  
    admission_history = models.TextField(
        verbose_name="História da Admissão",
        help_text="História clínica da admissão"
    )
    problems_and_diagnosis = models.TextField(
        verbose_name="Problemas e Diagnósticos",
        help_text="Problemas principais e diagnósticos"
    )
    exams_list = models.TextField(
        verbose_name="Lista de Exames",
        help_text="Exames realizados durante a internação"
    )
    procedures_list = models.TextField(
        verbose_name="Lista de Procedimentos", 
        help_text="Procedimentos realizados"
    )
    inpatient_medical_history = models.TextField(
        verbose_name="História Médica da Internação",
        help_text="Evolução médica durante a internação"
    )
    discharge_status = models.TextField(
        verbose_name="Status da Alta",
        help_text="Condições do paciente na alta"
    )
    discharge_recommendations = models.TextField(
        verbose_name="Recomendações de Alta",
        help_text="Orientações e recomendações para pós-alta"
    )
    
    # Classification fields
    medical_specialty = models.CharField(
        max_length=100,
        verbose_name="Especialidade Médica",
        help_text="Especialidade responsável pela alta"
    )
    
    # Draft system
    is_draft = models.BooleanField(
        default=True,
        verbose_name="É Rascunho",
        help_text="Indica se o relatório ainda é um rascunho editável"
    )
    
    class Meta:
        verbose_name = "Relatório de Alta"
        verbose_name_plural = "Relatórios de Alta" 
        ordering = ["-event_datetime"]
```

## Database Design

### Indexes Required
```python
# Add to model Meta:
indexes = [
    models.Index(fields=['admission_date']),
    models.Index(fields=['discharge_date']),
    models.Index(fields=['is_draft', 'patient']),
    models.Index(fields=['medical_specialty']),
]
```

### Constraints
- admission_date must be <= discharge_date
- is_draft defaults to True
- All text fields should be non-null but can be empty strings

## API Design

### URL Structure
```python
# apps/dischargereports/urls.py
urlpatterns = [
    path('', views.DischargeReportListView.as_view(), 
         name='dischargereport_list'),
    path('create/', views.DischargeReportCreateView.as_view(), 
         name='dischargereport_create'),
    path('<uuid:pk>/', views.DischargeReportDetailView.as_view(), 
         name='dischargereport_detail'),
    path('<uuid:pk>/update/', views.DischargeReportUpdateView.as_view(), 
         name='dischargereport_update'),
    path('<uuid:pk>/delete/', views.DischargeReportDeleteView.as_view(), 
         name='dischargereport_delete'),
    path('<uuid:pk>/print/', views.DischargeReportPrintView.as_view(), 
         name='dischargereport_print'),
]
```

### View Classes
```python
class DischargeReportCreateView(LoginRequiredMixin, CreateView):
    """Create new discharge report"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_create.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        # Handle draft vs final save
        if 'save_final' in self.request.POST:
            form.instance.is_draft = False
        return super().form_valid(form)

class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportForm  
    template_name = 'dischargereports/dischargereport_update.html'
    
    def get_object(self):
        obj = super().get_object()
        # Check if editable (draft or within 24h window)
        if not obj.is_draft and not obj.can_be_edited:
            raise PermissionDenied("Report is no longer editable")
        return obj
```

## Form Design

### DischargeReportForm
```python
class DischargeReportForm(forms.ModelForm):
    """Form for discharge report create/update"""
    
    class Meta:
        model = DischargeReport
        fields = [
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history', 
            'discharge_status', 'discharge_recommendations'
        ]
        widgets = {
            'admission_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'discharge_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'medical_specialty': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'admission_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'problems_and_diagnosis': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'exams_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'procedures_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'inpatient_medical_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 6}
            ),
            'discharge_status': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'discharge_recommendations': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        admission_date = cleaned_data.get('admission_date')
        discharge_date = cleaned_data.get('discharge_date')
        
        if admission_date and discharge_date:
            if admission_date > discharge_date:
                raise forms.ValidationError(
                    "A data de admissão deve ser anterior à data de alta."
                )
        
        return cleaned_data
```

## Template Structure

### Base Template Layout
```html
<!-- dischargereport_create.html -->
{% extends 'base.html' %}
{% load static %}
{% load bootstrap5 %}

{% block title %}Novo Relatório de Alta{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3>Novo Relatório de Alta</h3>
                    <small class="text-muted">Paciente: {{ patient.name }}</small>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        
                        <!-- Date Fields Row -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                {% bootstrap_field form.admission_date %}
                            </div>
                            <div class="col-md-6">
                                {% bootstrap_field form.discharge_date %}
                            </div>
                        </div>
                        
                        <!-- Specialty Field -->
                        <div class="mb-3">
                            {% bootstrap_field form.medical_specialty %}
                        </div>
                        
                        <!-- Content Sections -->
                        <div class="mb-3">
                            {% bootstrap_field form.problems_and_diagnosis %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.admission_history %}
                        </div>
                        
                        <!-- ... other fields ... -->
                        
                        <!-- Action Buttons -->
                        <div class="d-flex gap-2">
                            <button type="submit" name="save_draft" 
                                    class="btn btn-warning">
                                <i class="bi bi-floppy"></i> Salvar Rascunho
                            </button>
                            <button type="submit" name="save_final" 
                                    class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Salvar Definitivo
                            </button>
                            <a href="{% url 'patients:patient_events_timeline' patient_id=patient.pk %}" 
                               class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Firebase Import Specifications

### Command Structure
```python
class Command(BaseCommand):
    help = "Import discharge reports from Firebase"
    
    def add_arguments(self, parser):
        parser.add_argument('--credentials-file', required=True)
        parser.add_argument('--database-url', required=True) 
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--since-date', help='YYYY-MM-DD format')
        
    def handle(self, *args, **options):
        # Initialize Firebase
        # Process patientDischargeReports reference
        # Create DischargeReport and PatientAdmission objects
```

### Data Mapping
```python
FIREBASE_FIELD_MAPPING = {
    'content.admissionDate': 'admission_date',      # '2025-08-22' -> date
    'content.dischargeDate': 'discharge_date',      # '2025-09-05' -> date  
    'content.admissionHistory': 'admission_history',
    'content.problemsAndDiagnostics': 'problems_and_diagnosis',
    'content.examsList': 'exams_list',
    'content.proceduresList': 'procedures_list', 
    'content.inpatientMedicalHistory': 'inpatient_medical_history',
    'content.patientDischargeStatus': 'discharge_status',
    'content.dischargeRecommendations': 'discharge_recommendations',
    'content.specialty': 'medical_specialty',       # Firebase specialty -> medical_specialty
    'datetime': 'event_datetime',                   # epoch milliseconds -> datetime
    'patient': 'patient',                           # Firebase key -> Patient lookup
    'username': 'created_by_name',                  # For audit trail
}
```

### PatientAdmission Creation Logic
```python
def create_patient_admission(self, discharge_report_data):
    """Create PatientAdmission for imported discharge report"""
    
    admission_date = discharge_report_data['admission_date']
    discharge_date = discharge_report_data['discharge_date']
    
    # Calculate stay duration
    stay_duration = (discharge_date - admission_date).days
    
    # Create admission record
    admission = PatientAdmission.objects.create(
        patient=discharge_report_data['patient'],
        admission_datetime=datetime.combine(admission_date, time.min),
        discharge_datetime=datetime.combine(discharge_date, time.min),
        admission_type=PatientAdmission.AdmissionType.SCHEDULED,
        discharge_type=PatientAdmission.DischargeType.MEDICAL,
        initial_bed='',
        final_bed='', 
        ward=None,
        admission_diagnosis='',
        discharge_diagnosis='',
        stay_duration_days=stay_duration,
        is_active=False,
        created_by=self.import_user,
        updated_by=self.import_user,
    )
    
    return admission
```

## Print Template Specifications

### PDF Layout Requirements
```html
<!-- dischargereport_print.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Alta - {{ report.patient.name }}</title>
    <link rel="stylesheet" href="{% static 'dischargereports/css/print.css' %}">
</head>
<body>
    <!-- Header (repeated on each page) -->
    <div class="header">
        <div class="hospital-info">
            {% hospital_logo %}
            <h1>{% hospital_name %}</h1>
            <h2>Relatório de Alta - {{ report.medical_specialty }}</h2>
        </div>
    </div>
    
    <!-- Patient Info -->
    <div class="patient-info">
        <div class="info-row">
            <span>Nome: {{ report.patient.name }}</span>
            <span>Prontuário: {{ report.patient.current_record_number }}</span>
        </div>
        <div class="info-row">
            <span>Nascimento: {{ report.patient.birthday|date:"d/m/Y" }}</span>
            <span>Gênero: {{ report.patient.get_gender_display }}</span>
            <span>Idade: {{ report.patient.age }} anos</span>
        </div>
        <div class="info-row">
            <span>Data de Admissão: {{ report.admission_date|date:"d/m/Y" }}</span>
            <span>Data de Alta: {{ report.discharge_date|date:"d/m/Y" }}</span>
        </div>
    </div>
    
    <!-- Content Sections -->
    <div class="content-section">
        <h3>Problemas e Diagnósticos</h3>
        <p>{{ report.problems_and_diagnosis|linebreaks }}</p>
    </div>
    
    <div class="content-section">
        <h3>História da Admissão</h3>
        <p>{{ report.admission_history|linebreaks }}</p>
    </div>
    
    <!-- ... other sections ... -->
    
    <!-- Footer -->
    <div class="footer">
        <p>Relatório gerado em {{ now|date:"d/m/Y às H:i" }}</p>
        <p>Por: {{ user.get_full_name|default:user.username }}</p>
    </div>
</body>
</html>
```

## Event Card Integration

### Event Card Template
```html
<!-- event_card_dischargereport.html -->
{% extends "events/partials/event_card_base.html" %}

{% block event_actions %}
<div class="btn-group btn-group-sm">
    <!-- View Button -->
    <a href="{{ event.get_absolute_url }}" 
       class="btn btn-outline-primary btn-sm">
        <i class="bi bi-eye"></i>
    </a>
    
    <!-- Print Button -->
    <a href="{% url 'apps.dischargereports:dischargereport_print' pk=event.pk %}" 
       class="btn btn-outline-secondary btn-sm" target="_blank">
        <i class="bi bi-printer"></i>
    </a>
    
    <!-- Edit Button (draft or within 24h) -->
    {% if event.is_draft or event_data.can_edit %}
        <a href="{{ event.get_edit_url }}" 
           class="btn btn-outline-warning btn-sm">
            <i class="bi bi-pencil"></i>
        </a>
    {% endif %}
</div>
{% endblock %}

{% block event_content %}
<div class="discharge-report-summary">
    <div class="mb-2">
        <strong>{{ event.medical_specialty }}</strong>
        {% if event.is_draft %}
            <span class="badge bg-warning ms-2">Rascunho</span>
        {% endif %}
    </div>
    <div class="text-muted small">
        <i class="bi bi-calendar-plus"></i> {{ event.admission_date|date:"d/m/Y" }}
        <i class="bi bi-arrow-right mx-2"></i>
        <i class="bi bi-door-open"></i> {{ event.discharge_date|date:"d/m/Y" }}
    </div>
    {% if event.problems_and_diagnosis %}
        <div class="mt-2">
            <small>{{ event.problems_and_diagnosis|truncatewords:20 }}</small>
        </div>
    {% endif %}
</div>
{% endblock %}
```

## Testing Strategy

### Model Tests
```python
class DischargeReportModelTests(TestCase):
    def test_save_sets_event_type(self):
        report = DischargeReport.objects.create(...)
        self.assertEqual(report.event_type, Event.DISCHARGE_REPORT_EVENT)
    
    def test_date_validation(self):
        # Test admission_date > discharge_date raises error
        
    def test_draft_default(self):
        # Test is_draft defaults to True
        
    def test_string_representation(self):
        # Test __str__ method
```

### View Tests  
```python
class DischargeReportViewTests(TestCase):
    def test_create_view_requires_login(self):
    def test_create_saves_draft(self):
    def test_create_saves_final(self):
    def test_update_only_allows_draft_or_24h(self):
    def test_delete_only_allows_draft(self):
```

This technical specification provides the detailed implementation guidelines needed to build the discharge reports feature according to the requirements while maintaining consistency with the existing codebase architecture.