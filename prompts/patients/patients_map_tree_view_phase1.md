# Patients Map Tree View - Phase 1: Core Backend & Basic Template

## Phase 1 Overview

Implement the foundational backend logic and basic tree view template. This phase focuses on getting the core functionality working without advanced interactivity.

## Step-by-Step Implementation

### Step 1: Create the View Class ✅ DONE

**File**: `apps/patients/views.py`

Add a new view class that gathers ward and patient data:

```python
class WardPatientMapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Display a tree view of wards and their current inpatients/emergency patients
    """
    template_name = "patients/ward_patient_map.html"
    permission_required = "patients.view_patient"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all active wards
        wards = Ward.objects.filter(is_active=True).order_by('name')

        ward_data = []
        total_patients = 0

        for ward in wards:
            # Get current inpatients and emergency patients in this ward
            patients = Patient.objects.filter(
                ward=ward,
                status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY],
                is_deleted=False
            ).select_related('ward').prefetch_related(
                'patient_tags__allowed_tag'
            ).order_by('bed', 'name')

            patient_list = []
            for patient in patients:
                # Get current admission for duration info
                current_admission = patient.get_current_admission()
                admission_duration = None
                if current_admission:
                    admission_duration = current_admission.duration_display

                patient_list.append({
                    'patient': patient,
                    'bed': patient.bed or 'Sem leito',
                    'tags': patient.patient_tags.all(),
                    'admission_duration': admission_duration,
                    'status_display': patient.get_status_display(),
                })

            ward_info = {
                'ward': ward,
                'patient_count': len(patient_list),
                'capacity_estimate': ward.capacity_estimate,
                'patients': patient_list,
                'utilization_percentage': None
            }

            # Calculate utilization if capacity is known
            if ward.capacity_estimate and ward.capacity_estimate > 0:
                ward_info['utilization_percentage'] = round(
                    (len(patient_list) / ward.capacity_estimate) * 100, 1
                )

            ward_data.append(ward_info)
            total_patients += len(patient_list)

        context.update({
            'ward_data': ward_data,
            'total_patients': total_patients,
            'total_wards': len(ward_data),
            'page_title': 'Mapa de Pacientes',
        })

        return context
```

### Step 2: Add URL Route ✅ DONE

**File**: `apps/patients/urls.py`

Add the new route after the existing ward URLs:

```python
# Add this line after line 102 (ward_update URL)
path("map/", views.WardPatientMapView.as_view(), name="patient_map"),
```

### Step 3: Create the Template ✅ DONE

**File**: `apps/patients/templates/patients/ward_patient_map.html`

Create a new template with the tree structure:

```html
{% extends "patients/patient_base.html" %} 
{% load hospital_tags %} 
{% block title %}
{{ page_title }} | {% hospital_name %}
{% endblock title %} 
{% block patient_content %}
<div class="container-fluid">
  <!-- Header Section -->
  <div class="row mb-4">
    <div class="col-12">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h2 class="mb-1">
            <i class="bi bi-diagram-3-fill text-medical-primary me-2"></i>
            Mapa de Pacientes
          </h2>
          <p class="text-muted mb-0">
            Visão geral da distribuição de pacientes pelas alas do hospital
          </p>
        </div>
        <div class="text-end">
          <div class="bg-light rounded p-3">
            <div class="row text-center">
              <div class="col">
                <div class="h4 mb-0 text-medical-primary">
                  {{ total_patients }}
                </div>
                <small class="text-muted">Pacientes</small>
              </div>
              <div class="col">
                <div class="h4 mb-0 text-medical-secondary">
                  {{ total_wards }}
                </div>
                <small class="text-muted">Alas Ativas</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Tree View Section -->
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          {% if ward_data %}
          <div class="ward-tree">
            {% for ward_info in ward_data %}
            <div class="ward-branch mb-4">
              <!-- Ward Header -->
              <div class="ward-header p-3 bg-light rounded">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="d-flex align-items-center">
                    <button
                      class="btn btn-sm btn-link p-0 me-2 ward-toggle"
                      type="button"
                      data-ward="{{ ward_info.ward.id }}"
                      aria-expanded="true"
                    >
                      <i class="bi bi-chevron-down"></i>
                    </button>
                    <i class="bi bi-building text-medical-primary me-2"></i>
                    <div>
                      <h5 class="mb-0">
                        {{ ward_info.ward.abbreviation }} - {{
                        ward_info.ward.name }}
                      </h5>
                      {% if ward_info.ward.floor %}
                      <small class="text-muted"
                        >{{ ward_info.ward.floor }}</small
                      >
                      {% endif %}
                    </div>
                  </div>
                  <div class="d-flex align-items-center">
                    <span class="badge bg-medical-primary me-2">
                      {{ ward_info.patient_count }} {% if
                      ward_info.capacity_estimate %} / {{
                      ward_info.capacity_estimate }} {% endif %} pacientes
                    </span>
                    {% if ward_info.utilization_percentage %}
                    <span
                      class="badge {% if ward_info.utilization_percentage > 90 %}bg-danger{% elif ward_info.utilization_percentage > 75 %}bg-warning{% else %}bg-success{% endif %}"
                    >
                      {{ ward_info.utilization_percentage }}%
                    </span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <!-- Patients List -->
              <div
                class="ward-patients collapse show"
                id="ward-{{ ward_info.ward.id }}"
              >
                {% if ward_info.patients %}
                <div class="ps-4 pt-2">
                  {% for patient_info in ward_info.patients %}
                  <div class="patient-item p-2 mb-2 bg-white border rounded">
                    <div
                      class="d-flex justify-content-between align-items-center"
                    >
                      <div class="d-flex align-items-center">
                        <i
                          class="bi bi-hospital text-medical-secondary me-2"
                        ></i>
                        <div>
                          <div class="d-flex align-items-center">
                            <strong>{{ patient_info.bed }}</strong>
                            <span class="mx-2">-</span>
                            <span>{{ patient_info.patient.name }}</span>
                            {% if patient_info.admission_duration %}
                            <small class="text-muted ms-2"
                              >({{ patient_info.admission_duration }})</small
                            >
                            {% endif %}
                          </div>
                          {% if patient_info.tags %}
                          <div class="mt-1">
                            {% for tag in patient_info.tags %}
                            <span
                              class="badge"
                              style="background-color: {{ tag.color }}; font-size: 0.7rem;"
                            >
                              {{ tag.name }}
                            </span>
                            {% endfor %}
                          </div>
                          {% endif %}
                        </div>
                      </div>
                      <div class="d-flex align-items-center">
                        <span
                          class="badge 
                                  {% if patient_info.patient.status == 2 %}bg-success{% endif %}
                                  {% if patient_info.patient.status == 3 %}bg-warning{% endif %}
                                  me-2"
                        >
                          {{ patient_info.status_display }}
                        </span>
                        <a
                          href="{% url 'apps.patients:patient_events_timeline' patient_id=patient_info.patient.pk %}"
                          class="btn btn-sm btn-outline-medical-primary"
                        >
                          <i class="bi bi-clock-history me-1"></i>
                          Timeline
                        </a>
                      </div>
                    </div>
                  </div>
                  {% endfor %}
                </div>
                {% else %}
                <div class="ps-4 pt-2">
                  <div class="text-muted fst-italic p-3">
                    <i class="bi bi-info-circle me-2"></i>
                    Nenhum paciente internado nesta ala
                  </div>
                </div>
                {% endif %}
              </div>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <div class="text-center py-5">
            <i class="bi bi-building display-4 text-muted mb-3"></i>
            <h4>Nenhuma ala cadastrada</h4>
            <p class="text-muted">
              Configure as alas do hospital para visualizar o mapa de pacientes.
            </p>
            {% if perms.patients.add_ward %}
            <a
              href="{% url 'apps.patients:ward_create' %}"
              class="btn btn-medical-primary"
            >
              <i class="bi bi-plus-circle me-2"></i>
              Adicionar Ala
            </a>
            {% endif %}
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Basic JavaScript for tree toggle -->
<script>
  document.addEventListener("DOMContentLoaded", function () {
    // Basic toggle functionality
    const toggleButtons = document.querySelectorAll(".ward-toggle");

    toggleButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const wardId = this.dataset.ward;
        const target = document.getElementById("ward-" + wardId);
        const icon = this.querySelector("i");

        if (target.classList.contains("show")) {
          target.classList.remove("show");
          icon.classList.remove("bi-chevron-down");
          icon.classList.add("bi-chevron-right");
          this.setAttribute("aria-expanded", "false");
        } else {
          target.classList.add("show");
          icon.classList.remove("bi-chevron-right");
          icon.classList.add("bi-chevron-down");
          this.setAttribute("aria-expanded", "true");
        }
      });
    });
  });
</script>

<style>
  .ward-tree .ward-branch {
    border-left: 3px solid var(--bs-medical-primary);
    margin-left: 1rem;
    padding-left: 1rem;
  }

  .ward-header {
    border: 1px solid var(--bs-border-color);
  }

  .patient-item {
    border-left: 2px solid var(--bs-medical-secondary) !important;
    transition: box-shadow 0.2s ease;
  }

  .patient-item:hover {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .ward-toggle {
    color: var(--bs-medical-primary);
    text-decoration: none;
  }

  .ward-toggle:hover {
    color: var(--bs-medical-primary-dark);
  }

  .collapse {
    transition: height 0.3s ease;
  }

  .collapse.show {
    display: block;
  }

  .collapse:not(.show) {
    display: none;
  }
</style>
{% endblock %}
```

### Step 4: Add Navigation Menu Item ✅ DONE

**File**: `templates/base_app.html`

Add the new menu item in the "Gestão de Pacientes" section. Insert after line 139 (after the tag management link):

```html
{% if perms.patients.view_patient %}
<li class="nav-item">
  <a class="nav-link" href="{% url 'apps.patients:patient_map' %}">
    <i class="bi bi-diagram-3-fill"></i>
    Mapa de Pacientes
  </a>
</li>
{% endif %}
```

### Step 5: Update Patient Base Template (if needed)

Verify that `apps/patients/templates/patients/patient_base.html` exists and extends the main application template properly. If it doesn't exist, create it:

```html
{% extends "base_app.html" %} {% block content %}
<div class="patient-app">{% block patient_content %} {% endblock %}</div>
{% endblock %}
```

## Phase 1 Testing

### Manual Testing Steps

1. **Access Test**

   - Navigate to `/patients/map/`
   - Verify page loads without errors
   - Check that proper permissions are enforced

2. **Data Display Test**

   - Verify all active wards are shown
   - Confirm only INPATIENT and EMERGENCY patients appear
   - Check patient counts are accurate
   - Verify bed information displays correctly

3. **Navigation Test**

   - Test ward expand/collapse functionality
   - Verify timeline links work correctly
   - Check responsive behavior on mobile

4. **Permission Test**
   - Test with different user roles
   - Verify menu item appears only for authorized users

### Expected Database Queries

- 1 query for all active wards
- 1 query for all relevant patients (with prefetch_related)
- Minimal additional queries for admissions

### Performance Considerations

- Use `select_related('ward')` to avoid N+1 queries
- Use `prefetch_related('patient_tags__allowed_tag')` for tags
- Consider caching for high-traffic scenarios (Phase 3)

## Phase 1 Completion Criteria

- ✅ Tree view displays all active wards
- ✅ Shows correct patient counts and information
- ✅ Basic expand/collapse functionality works
- ✅ Navigation integration is complete
- ✅ Responsive design works on mobile
- ✅ Page loads within 2 seconds for typical data volume
- ✅ All links and actions function correctly

## Transition to Phase 2

Once Phase 1 is complete and tested, proceed to Phase 2 for enhanced JavaScript interactivity, search functionality, and improved styling.
