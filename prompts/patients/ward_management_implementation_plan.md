# Ward Management Implementation Plan

**Project**: EquipeMed - Ward Management Feature  
**Type**: Greenfield Implementation (Database will be wiped)  
**Target**: Add Ward model with flexible bed management  

## Overview

This plan implements a Ward-only model with flexible bed strings to match real hospital workflows. Most hospitals have dynamic bed configurations and flexible numbering systems, so we'll avoid rigid bed management and focus on ward organization with free-text bed identifiers.

## Implementation Steps

### Phase 1: Ward Model Creation

#### 1.1 Create Ward Model
**File**: `apps/patients/models.py`

Add the Ward model after the existing Tag model:

```python
class Ward(models.Model):
    """Model representing hospital wards/departments"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Nome da Ala",
        help_text="Nome completo da ala (ex: Unidade de Terapia Intensiva)"
    )
    abbreviation = models.CharField(
        max_length=10, 
        unique=True,
        verbose_name="Sigla",
        help_text="Sigla da ala (ex: UTI, CC, PS)"
    )
    description = models.TextField(
        blank=True, 
        verbose_name="Descrição",
        help_text="Descrição detalhada da ala e suas especialidades"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Ativa",
        help_text="Indica se a ala está ativa e disponível para uso"
    )
    
    # Optional ward characteristics
    floor = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Andar",
        help_text="Andar onde a ala está localizada (ex: 2º Andar, Térreo)"
    )
    capacity_estimate = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Capacidade Estimada",
        help_text="Estimativa de capacidade de leitos (informativo apenas)"
    )
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="created_wards",
        verbose_name="Criado por"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="updated_wards",
        verbose_name="Atualizado por"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Ala"
        verbose_name_plural = "Alas"

    def __str__(self):
        return f"{self.abbreviation} - {self.name}"
    
    def get_current_patients_count(self):
        """Get count of patients currently in this ward"""
        return self.patients.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
        ).count()
    
    def get_available_beds_list(self):
        """Get list of bed identifiers currently in use in this ward"""
        return list(
            self.patients.filter(
                status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
            ).exclude(bed="").values_list("bed", flat=True).distinct()
        )
```

#### 1.2 Update Patient Model
**File**: `apps/patients/models.py`

Add ward field to Patient model (after the `bed` field):

```python
# Add to Patient model fields section (around line 528)
ward = models.ForeignKey(
    Ward, 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True,
    related_name="patients",
    verbose_name="Ala",
    help_text="Ala onde o paciente está localizado"
)
```

#### 1.3 Update PatientAdmission Model
**File**: `apps/patients/models.py`

Add ward field to PatientAdmission model (after the `final_bed` field):

```python
# Add to PatientAdmission model fields section (around line 261)
ward = models.ForeignKey(
    Ward, 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True,
    related_name="admissions",
    verbose_name="Ala",
    help_text="Ala onde a internação ocorreu"
)
```

#### 1.4 Update Model Methods

Add ward-related methods to existing models:

**Patient model updates**:
```python
# Add to Patient model methods section

def update_ward_from_admission(self):
    """Update patient ward from current admission"""
    current_admission = self.get_current_admission()
    if current_admission and current_admission.ward:
        self.ward = current_admission.ward
        self.save(update_fields=["ward", "updated_at"])

def get_ward_display(self):
    """Get formatted ward display for templates"""
    if self.ward:
        return f"{self.ward.abbreviation} - {self.ward.name}"
    return "Sem ala definida"
```

**PatientAdmission model updates**:
```python
# Update admit_patient method in Patient model to include ward
def admit_patient(self, admission_datetime, admission_type, user, **kwargs):
    # ... existing code ...
    
    # Create admission record
    admission = PatientAdmission.objects.create(
        patient=self,
        admission_datetime=admission_datetime,
        admission_type=admission_type,
        initial_bed=kwargs.get("initial_bed", ""),
        ward=kwargs.get("ward"),  # Add this line
        admission_diagnosis=kwargs.get("admission_diagnosis", ""),
        created_by=user,
        updated_by=user,
    )
    
    # Update patient status and denormalized fields
    self.status = self.Status.INPATIENT
    self.current_admission_id = admission.id
    self.ward = admission.ward  # Add this line
    # ... rest of existing code ...
```

### Phase 2: Admin Interface Updates

#### 2.1 Update Admin Configuration
**File**: `apps/patients/admin.py`

Add Ward admin and update existing admin classes:

```python
# Add Ward admin class
@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = [
        "abbreviation", 
        "name", 
        "floor", 
        "capacity_estimate", 
        "is_active",
        "current_patients_count",
        "created_at"
    ]
    list_filter = ["is_active", "floor", "created_at"]
    search_fields = ["name", "abbreviation", "description"]
    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]
    
    fieldsets = [
        ("Informações Básicas", {
            "fields": ("name", "abbreviation", "description", "is_active")
        }),
        ("Localização", {
            "fields": ("floor", "capacity_estimate"),
            "classes": ("collapse",)
        }),
        ("Auditoria", {
            "fields": ("created_at", "created_by", "updated_at", "updated_by"),
            "classes": ("collapse",)
        }),
    ]
    
    def current_patients_count(self, obj):
        return obj.get_current_patients_count()
    current_patients_count.short_description = "Pacientes Atuais"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

# Update PatientAdmin to include ward
class PatientAdmin(admin.ModelAdmin):
    # Update list_display to include ward
    list_display = [
        "name", 
        "current_record_number", 
        "status", 
        "ward",  # Add this
        "bed", 
        "last_admission_date",
        "created_at"
    ]
    
    # Update list_filter to include ward
    list_filter = [
        "status", 
        "ward",  # Add this
        "created_at", 
        "last_admission_date"
    ]
    
    # Update fieldsets to include ward
    fieldsets = [
        ("Informações Pessoais", {
            "fields": ("name", "birthday", "phone")
        }),
        ("Documentos", {
            "fields": ("healthcard_number", "id_number", "fiscal_number"),
            "classes": ("collapse",)
        }),
        ("Endereço", {
            "fields": ("address", "city", "state", "zip_code"),
            "classes": ("collapse",)
        }),
        ("Status Hospitalar", {
            "fields": ("status", "ward", "bed", "last_admission_date", "last_discharge_date")  # Add ward
        }),
        # ... rest of existing fieldsets ...
    ]

# Update PatientAdmissionAdmin to include ward
class PatientAdmissionAdmin(admin.ModelAdmin):
    # Update list_display to include ward
    list_display = [
        "patient", 
        "admission_datetime", 
        "admission_type", 
        "ward",  # Add this
        "initial_bed", 
        "is_active",
        "stay_duration_days"
    ]
    
    # Update list_filter to include ward
    list_filter = [
        "admission_type", 
        "discharge_type", 
        "ward",  # Add this
        "is_active", 
        "admission_datetime"
    ]
    
    # Update fieldsets to include ward
    fieldsets = [
        ("Informações da Internação", {
            "fields": ("patient", "admission_datetime", "admission_type")
        }),
        ("Localização", {
            "fields": ("ward", "initial_bed", "final_bed")  # Add ward
        }),
        # ... rest of existing fieldsets ...
    ]
```

### Phase 3: Forms and Views Updates

#### 3.1 Update Forms
**File**: `apps/patients/forms.py`

Update existing forms to include ward selection:

```python
# Update PatientForm to include ward
class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "name", "birthday", "healthcard_number", "id_number", "fiscal_number",
            "phone", "address", "city", "state", "zip_code", 
            "status", "ward", "bed"  # Add ward
        ]
        widgets = {
            "birthday": forms.DateInput(attrs={"type": "date"}),
            "ward": forms.Select(attrs={"class": "form-select"}),  # Add ward widget
            # ... existing widgets ...
        }

# Update admission form
class AdmissionForm(forms.ModelForm):
    class Meta:
        model = PatientAdmission
        fields = [
            "admission_datetime", "admission_type", 
            "ward", "initial_bed", "admission_diagnosis"  # Add ward
        ]
        widgets = {
            "admission_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ward": forms.Select(attrs={"class": "form-select"}),  # Add ward widget
            # ... existing widgets ...
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only active wards
        self.fields["ward"].queryset = Ward.objects.filter(is_active=True)
        # Make ward required for admissions
        self.fields["ward"].required = True

# Add new WardForm for ward management
class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = [
            "name", "abbreviation", "description", "floor", 
            "capacity_estimate", "is_active"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "abbreviation": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "floor": forms.TextInput(attrs={"class": "form-control"}),
            "capacity_estimate": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
```

#### 3.2 Update Views
**File**: `apps/patients/views.py`

Add ward context to existing views and create new ward management views:

```python
# Update existing views to include ward context
class PatientListView(ListView):
    # ... existing code ...
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wards"] = Ward.objects.filter(is_active=True).order_by("name")
        # ... existing context ...
        return context

# Add new ward management views
class WardListView(LoginRequiredMixin, ListView):
    model = Ward
    template_name = "patients/ward_list.html"
    context_object_name = "wards"
    paginate_by = 20
    
    def get_queryset(self):
        return Ward.objects.filter(is_active=True).order_by("name")

class WardDetailView(LoginRequiredMixin, DetailView):
    model = Ward
    template_name = "patients/ward_detail.html"
    context_object_name = "ward"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ward = self.get_object()
        context["current_patients"] = ward.patients.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
        ).order_by("name")
        context["recent_admissions"] = ward.admissions.filter(
            is_active=True
        ).order_by("-admission_datetime")[:10]
        return context

class WardCreateView(LoginRequiredMixin, CreateView):
    model = Ward
    form_class = WardForm
    template_name = "patients/ward_form.html"
    success_url = reverse_lazy("patients:ward_list")
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

class WardUpdateView(LoginRequiredMixin, UpdateView):
    model = Ward
    form_class = WardForm
    template_name = "patients/ward_form.html"
    success_url = reverse_lazy("patients:ward_list")
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
```

### Phase 4: Templates Updates

#### 4.1 Update Patient Templates
**Files**: Update existing patient templates to show ward information

Add ward display to patient list and detail templates:
- `apps/patients/templates/patients/patient_list.html`: Add ward column
- `apps/patients/templates/patients/patient_detail.html`: Add ward section
- `apps/patients/templates/patients/patient_form.html`: Add ward field

#### 4.2 Create Ward Templates
**Files**: Create new ward management templates

Create new templates:
- `apps/patients/templates/patients/ward_list.html`: Ward listing
- `apps/patients/templates/patients/ward_detail.html`: Ward details with patient list
- `apps/patients/templates/patients/ward_form.html`: Ward creation/editing

### Phase 5: URL Configuration

#### 5.1 Update URLs
**File**: `apps/patients/urls.py`

Add ward management URLs:

```python
urlpatterns = [
    # ... existing patterns ...
    
    # Ward management URLs
    path("wards/", views.WardListView.as_view(), name="ward_list"),
    path("wards/add/", views.WardCreateView.as_view(), name="ward_create"),
    path("wards/<uuid:pk>/", views.WardDetailView.as_view(), name="ward_detail"),
    path("wards/<uuid:pk>/edit/", views.WardUpdateView.as_view(), name="ward_update"),
]
```

### Phase 6: Management Commands

#### 6.1 Create Sample Wards Command
**File**: `apps/patients/management/commands/create_sample_wards.py`

```python
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.patients.models import Ward

User = get_user_model()

class Command(BaseCommand):
    help = "Create sample wards for development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Delete existing wards before creating new ones",
        )

    def handle(self, *args, **options):
        if options["delete_existing"]:
            Ward.objects.all().delete()
            self.stdout.write("Deleted existing wards")

        # Get superuser for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No users found. Create a user first.")
            )
            return

        wards_data = [
            {
                "name": "Unidade de Terapia Intensiva",
                "abbreviation": "UTI",
                "description": "Unidade de cuidados intensivos para pacientes críticos",
                "floor": "3º Andar",
                "capacity_estimate": 12,
            },
            {
                "name": "Pronto Socorro",
                "abbreviation": "PS",
                "description": "Atendimento de emergência e urgência",
                "floor": "Térreo",
                "capacity_estimate": 8,
            },
            {
                "name": "Clínica Médica",
                "abbreviation": "CM",
                "description": "Internação clínica geral",
                "floor": "2º Andar",
                "capacity_estimate": 20,
            },
            {
                "name": "Clínica Cirúrgica",
                "abbreviation": "CC",
                "description": "Internação de pacientes cirúrgicos",
                "floor": "2º Andar",
                "capacity_estimate": 15,
            },
            {
                "name": "Pediatria",
                "abbreviation": "PED",
                "description": "Atendimento pediátrico",
                "floor": "1º Andar",
                "capacity_estimate": 10,
            },
            {
                "name": "Maternidade",
                "abbreviation": "MAT",
                "description": "Atendimento obstétrico e neonatal",
                "floor": "1º Andar",
                "capacity_estimate": 12,
            },
        ]

        created_count = 0
        for ward_data in wards_data:
            ward, created = Ward.objects.get_or_create(
                abbreviation=ward_data["abbreviation"],
                defaults={
                    **ward_data,
                    "created_by": admin_user,
                    "updated_by": admin_user,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created ward: {ward}")
            else:
                self.stdout.write(f"Ward already exists: {ward}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} wards")
        )
```

#### 6.2 Update populate_sample_data Command
**File**: `apps/core/management/commands/populate_sample_data.py`

Add ward creation to the existing sample data command:

```python
# Add this import at the top
from apps.patients.models import Ward

# Add this to the handle method after hospital creation
def create_sample_wards(self):
    self.stdout.write("Creating sample wards...")
    
    admin_user = self.get_admin_user()
    
    wards_data = [
        # ... same wards_data as above ...
    ]
    
    created_count = 0
    for ward_data in wards_data:
        ward, created = Ward.objects.get_or_create(
            abbreviation=ward_data["abbreviation"],
            defaults={
                **ward_data,
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )
        if created:
            created_count += 1

    self.stdout.write(f"Created {created_count} sample wards")

# Update the handle method to call create_sample_wards
def handle(self, *args, **options):
    # ... existing code ...
    self.create_sample_wards()  # Add this line
    # ... rest of existing code ...
```

### Phase 7: Documentation Updates

#### 7.1 Update Database Reset Documentation
**File**: `docs/database-reset.md`

Update Step 7 to include ward creation:

```markdown
### Step 7: Set Up Initial Data

```bash
# Create permission groups
uv run python manage.py setup_groups

# Create sample wards (new)
uv run python manage.py create_sample_wards

# Create sample tags (optional)
uv run python manage.py create_sample_tags

# Create comprehensive sample data (hospitals, users, patients, daily notes, drug templates, prescriptions)
uv run python manage.py populate_sample_data
```

#### 7.2 Update Reset Script
**File**: `reset_database.sh`

Update the initialize_data function:

```bash
initialize_data() {
  print_header "STEP 6: INITIALIZING APPLICATION DATA"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would set up permission groups..."
    print_status "[DRY RUN] Would create sample wards..."  # Add this line
    print_status "[DRY RUN] Would create sample tags..."
    # ... existing dry run messages ...
    return 0
  fi

  print_status "Setting up permission groups..."
  if uv run python manage.py setup_groups; then
    print_success "Permission groups created successfully"
  else
    print_error "Failed to create permission groups"
    exit 1
  fi

  print_status "Creating sample wards..."  # Add this block
  if uv run python manage.py create_sample_wards; then
    print_success "Sample wards created successfully"
  else
    print_error "Failed to create sample wards"
    exit 1
  fi

  # ... rest of existing code ...
}

# Update display_completion function
display_completion() {
  # ... existing code ...
  
  print_status "Available sample data:"
  echo "  • Multiple hospitals with wards"
  echo "  • Hospital wards (UTI, PS, CM, CC, PED, MAT)"  # Add this line
  echo "  • Medical staff with different profession types"
  # ... existing data list ...
}
```

### Phase 8: Template Tags and Context Processors

#### 8.1 Create Ward Template Tags
**File**: `apps/patients/templatetags/ward_tags.py`

```python
from django import template
from apps.patients.models import Ward

register = template.Library()

@register.inclusion_tag("patients/partials/ward_badge.html")
def ward_badge(ward):
    """Display a ward badge with abbreviation and name"""
    return {"ward": ward}

@register.simple_tag
def ward_patient_count(ward):
    """Get current patient count for a ward"""
    return ward.get_current_patients_count()

@register.simple_tag
def get_active_wards():
    """Get all active wards"""
    return Ward.objects.filter(is_active=True).order_by("name")
```

#### 8.2 Update Context Processors
**File**: `apps/patients/context_processors.py`

Add ward statistics to existing context processors:

```python
def ward_stats(request):
    """Add ward statistics to template context"""
    if not request.user.is_authenticated:
        return {}
    
    from apps.patients.models import Ward
    
    wards = Ward.objects.filter(is_active=True)
    ward_stats = []
    
    for ward in wards:
        ward_stats.append({
            "ward": ward,
            "patient_count": ward.get_current_patients_count(),
            "beds_in_use": len(ward.get_available_beds_list()),
        })
    
    return {
        "ward_statistics": ward_stats,
        "total_active_wards": wards.count(),
    }
```

Update `config/settings.py` to include the new context processor:

```python
TEMPLATES = [
    {
        # ... existing config ...
        "OPTIONS": {
            "context_processors": [
                # ... existing context processors ...
                "apps.patients.context_processors.ward_stats",  # Add this line
            ],
        },
    },
]
```

### Phase 9: Testing

#### 9.1 Create Ward Tests
**File**: `apps/patients/tests/test_ward_models.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Ward, Patient

User = get_user_model()

class WardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        
    def test_ward_creation(self):
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            description="Test description",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(ward.name, "Test Ward")
        self.assertEqual(ward.abbreviation, "TW")
        self.assertTrue(ward.is_active)
        
    def test_ward_str_representation(self):
        ward = Ward.objects.create(
            name="Intensive Care Unit",
            abbreviation="ICU",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(str(ward), "ICU - Intensive Care Unit")
        
    def test_ward_patient_count(self):
        ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Create inpatient
        patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(ward.get_current_patients_count(), 1)
```

### Phase 10: Migration and Database Update

Since this is a greenfield project with database wipe:

#### 10.1 Update CLAUDE.md
**File**: `CLAUDE.md`

Add ward management to the essential commands section:

```markdown
# Sample data
uv run python manage.py create_sample_tags
uv run python manage.py create_sample_wards  # Add this line
uv run python manage.py create_sample_content
uv run python manage.py create_sample_pdf_forms
```

## Implementation Checklist

- [ ] **Phase 1**: Ward model creation and Patient/PatientAdmission updates
- [ ] **Phase 2**: Admin interface updates for ward management
- [ ] **Phase 3**: Forms and views updates to include ward selection
- [ ] **Phase 4**: Template updates to display ward information
- [ ] **Phase 5**: URL configuration for ward management
- [ ] **Phase 6**: Management commands for sample ward creation
- [ ] **Phase 7**: Documentation updates (database-reset.md, reset_database.sh)
- [ ] **Phase 8**: Template tags and context processors
- [ ] **Phase 9**: Test creation for ward functionality
- [ ] **Phase 10**: Final documentation updates

## Benefits of This Implementation

1. **Realistic Hospital Workflow**: Matches how hospitals actually organize departments
2. **Flexible Bed Management**: No rigid bed constraints - users can enter any bed identifier
3. **Organizational Structure**: Clear departmental organization (ICU, Emergency, Medical, etc.)
4. **Easy Reporting**: Filter and report by ward regardless of specific bed numbers
5. **Future Extensibility**: Foundation for future features like ward-specific permissions or workflows
6. **Backward Compatibility**: Existing bed fields remain functional
7. **Performance Friendly**: Simple model structure with efficient queries

## Post-Implementation Usage Examples

- **Ward Assignment**: Select "UTI" ward, enter bed "01" or "Bed A" or leave blank
- **Patient Search**: Filter patients by ward to see all ICU patients
- **Reporting**: Generate ward occupancy reports without tracking specific beds
- **Flexibility**: Each hospital can use their own bed numbering system
- **Scalability**: Easy to add new wards without complex bed management

This implementation provides the organizational benefits of ward management while maintaining the flexibility that real hospitals need for their diverse bed numbering and management systems.