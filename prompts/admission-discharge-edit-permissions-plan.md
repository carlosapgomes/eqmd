# Admission/Discharge Edit Permissions Implementation Plan

## Overview

This plan implements granular edit permissions for patient admission and discharge records, allowing users to edit admission data within 24 hours of creation and discharge data within 24 hours of discharge, while maintaining the existing modal-based UI flow.

## Current System Analysis

### Existing Components ✅

- **Modal-based admission system** - Works well, keep as-is
- **Modal-based discharge system** - Works well, keep as-is
- **Admission history table** - Good foundation, needs action buttons
- **Status display with current admission** - Good, needs edit buttons
- **Permission system integration** - Uses `available_status_actions` template tag

### Current Permission Logic

- 24-hour edit constraint exists for Event model only
- PatientAdmission is standalone model - no automatic constraints
- Current system lacks granular admission/discharge edit permissions

## Implementation Plan

### Phase 1: Permission System Foundation

#### 1.1 Create Admission-Specific Permission Functions

**File**: `apps/core/permissions/utils.py`

Add new permission functions:

```python
def can_edit_admission_data(user, admission):
    """
    Edit admission info for active admissions.
    Rules:
    - Admission must be active (not discharged)
    - Creator has 24h window OR doctors/residents always can
    """

def can_discharge_patient(user, admission):
    """
    Add discharge information to active admission.
    Rules:
    - Admission must be active
    - Only doctors/residents can discharge
    """

def can_edit_discharge_data(user, admission):
    """
    Edit discharge info after discharge.
    Rules:
    - Admission must be completed (discharged)
    - Only doctors/residents can edit
    - Within 24h of discharge datetime
    """

def can_cancel_discharge(user, admission):
    """
    Cancel discharge and reactivate admission.
    Rules:
    - Admission must be completed (discharged)
    - Only doctors/residents can cancel
    - Within 24h of discharge datetime
    """
```

#### 1.2 Create Permission Constants

**File**: `apps/core/permissions/constants.py`

Add:

```python
ADMISSION_EDIT_TIME_LIMIT = 24  # hours
DISCHARGE_EDIT_TIME_LIMIT = 24  # hours
```

#### 1.3 Update Template Tags

**File**: `apps/patients/templatetags/patient_tags.py`

Extend `available_status_actions` to include edit actions:

```python
def get_admission_edit_actions(user, patient, admission):
    """Generate edit actions for specific admission"""
    actions = []

    if can_edit_admission_data(user, admission):
        actions.append({
            'action_name': 'edit_admission',
            'label': 'Editar Internação',
            'icon': 'edit',
            'btn_class': 'btn-outline-primary'
        })

    if can_edit_discharge_data(user, admission):
        actions.append({
            'action_name': 'edit_discharge',
            'label': 'Editar Alta',
            'icon': 'edit',
            'btn_class': 'btn-outline-warning'
        })

    # ... etc
```

### Phase 2: Forms Enhancement

#### 2.1 Create Edit Forms

**File**: `apps/patients/forms.py`

```python
class EditAdmissionForm(forms.ModelForm):
    """Form for editing admission data only"""
    class Meta:
        model = PatientAdmission
        fields = [
            'admission_datetime', 'admission_type', 'initial_bed',
            'ward', 'admission_diagnosis'
        ]

class EditDischargeForm(forms.ModelForm):
    """Form for editing discharge data only"""
    class Meta:
        model = PatientAdmission
        fields = [
            'discharge_datetime', 'discharge_type', 'final_bed',
            'discharge_diagnosis'
        ]
```

#### 2.2 Form Validation

Add custom validation to prevent:

- Editing discharge info on active admissions
- Editing admission info on completed admissions
- Invalid datetime sequences

### Phase 3: View Layer Enhancement

#### 3.1 Update Timeline View Logic

**File**: `apps/events/views.py` (or wherever the timeline view is defined)

Update timeline context to include admission permissions:

```python
def patient_timeline(request, patient_id):
    """Patient timeline view with admission edit permissions"""
    # ... existing logic ...
    
    # Process events and add admission permissions
    processed_events = []
    for event_data in events:
        event = event_data['event']
        
        # Add admission-specific permissions for admission/discharge events
        if hasattr(event, 'admission') and event.admission:
            admission = event.admission
            admission_permissions = {
                'can_edit_admission': can_edit_admission_data(request.user, admission),
                'can_edit_discharge': can_edit_discharge_data(request.user, admission),
                'can_cancel_discharge': can_cancel_discharge(request.user, admission),
                'can_discharge': can_discharge_patient(request.user, admission),
            }
            event_data['admission_permissions'] = admission_permissions
        
        processed_events.append(event_data)
    
    # ... rest of view logic ...
```

#### 3.2 Create Edit Views

**File**: `apps/patients/views.py`

```python
@login_required
@require_http_methods(["GET", "POST"])
def edit_admission_data(request, patient_id, admission_id):
    """Edit admission data for active admission"""
    # Permission check with can_edit_admission_data
    # Form handling
    # Success redirect to patient detail

@login_required
@require_http_methods(["GET", "POST"])
def edit_discharge_data(request, patient_id, admission_id):
    """Edit discharge data for completed admission"""
    # Permission check with can_edit_discharge_data
    # Form handling
    # Success redirect to patient detail

@login_required
@require_http_methods(["POST"])
def cancel_discharge(request, patient_id, admission_id):
    """Cancel discharge and reactivate admission"""
    # Permission check with can_cancel_discharge
    # Reactivate admission logic
    # Update patient status
```

#### 3.2 URL Patterns

**File**: `apps/patients/urls.py`

```python
path('patients/<uuid:patient_id>/admissions/<uuid:admission_id>/edit/',
     views.edit_admission_data, name='edit_admission_data'),
path('patients/<uuid:patient_id>/admissions/<uuid:admission_id>/edit-discharge/',
     views.edit_discharge_data, name='edit_discharge_data'),
path('patients/<uuid:patient_id>/admissions/<uuid:admission_id>/cancel-discharge/',
     views.cancel_discharge, name='cancel_discharge'),
```

### Phase 4: Template Enhancement

#### 4.1 Update Timeline Event Cards

**Files**: 
- `apps/events/templates/events/partials/event_card_admission.html`
- `apps/events/templates/events/partials/event_card_discharge.html`

**Admission Card Actions** (`event_card_admission.html`):
```html
{% block event_actions %}
<div class="btn-group btn-group-sm">
    <!-- View button (inherited) -->
    <a href="{{ event.get_absolute_url }}" 
       class="btn btn-outline-primary btn-sm"
       title="Ver detalhes">
        <i class="bi bi-eye"></i>
    </a>
    
    <!-- Edit Admission button - show if can edit admission data -->
    {% if admission_permissions.can_edit_admission %}
    <button class="btn btn-outline-warning btn-sm"
            data-bs-toggle="modal" 
            data-bs-target="#editAdmissionModal"
            data-admission-id="{{ event.id }}"
            title="Editar Internação">
        <i class="bi bi-pencil"></i>
    </button>
    {% endif %}
    
    <!-- Discharge button - show if can discharge (active admission) -->
    {% if admission_permissions.can_discharge %}
    <button class="btn btn-outline-success btn-sm"
            data-bs-toggle="modal" 
            data-bs-target="#dischargePatientModal"
            data-admission-id="{{ event.id }}"
            title="Dar Alta">
        <i class="bi bi-door-open"></i>
    </button>
    {% endif %}
</div>
{% endblock event_actions %}
```

**Discharge Card Actions** (`event_card_discharge.html`):
```html
{% block event_actions %}
<div class="btn-group btn-group-sm">
    <!-- View button (inherited) -->
    <a href="{{ event.get_absolute_url }}" 
       class="btn btn-outline-primary btn-sm"
       title="Ver detalhes">
        <i class="bi bi-eye"></i>
    </a>
    
    <!-- Edit Discharge button - show if can edit discharge data -->
    {% if admission_permissions.can_edit_discharge %}
    <button class="btn btn-outline-warning btn-sm"
            data-bs-toggle="modal" 
            data-bs-target="#editDischargeModal"
            data-admission-id="{{ event.id }}"
            title="Editar Alta">
        <i class="bi bi-pencil"></i>
    </button>
    {% endif %}
    
    <!-- Cancel Discharge button - show if can cancel discharge -->
    {% if admission_permissions.can_cancel_discharge %}
    <button class="btn btn-outline-danger btn-sm"
            data-bs-toggle="modal" 
            data-bs-target="#cancelDischargeModal"
            data-admission-id="{{ event.id }}"
            title="Cancelar Alta">
        <i class="bi bi-arrow-clockwise"></i>
    </button>
    {% endif %}
</div>
{% endblock event_actions %}
```

#### 4.2 Add Edit Modals to Timeline Template

**File**: `apps/events/templates/events/patient_timeline.html`

Add at end of template (before closing body tag):

```html
<!-- Edit Admission Modal -->
<div class="modal fade" id="editAdmissionModal" tabindex="-1">
  <!-- Pre-populated form with existing admission data -->
</div>

<!-- Edit Discharge Modal -->
<div class="modal fade" id="editDischargeModal" tabindex="-1">
  <!-- Pre-populated form with existing discharge data -->
</div>

<!-- Cancel Discharge Modal -->
<div class="modal fade" id="cancelDischargeModal" tabindex="-1">
  <!-- Confirmation dialog for discharge cancellation -->
</div>

<!-- Discharge Patient Modal (for active admissions) -->
<div class="modal fade" id="dischargePatientModal" tabindex="-1">
  <!-- Standard discharge form -->
</div>
```

#### 4.2 Enhance Current Admission Display

**Location**: Lines 54-84 in admission_section.html

Add edit button to current admission alert:

```html
<div class="alert alert-success">
  <!-- existing content -->
  <div class="mt-2">
    {% if can_edit_admission_data %}
    <button
      class="btn btn-sm btn-outline-primary"
      data-bs-toggle="modal"
      data-bs-target="#editAdmissionModal"
    >
      <i class="fas fa-edit"></i> Editar Internação
    </button>
    {% endif %}
  </div>
</div>
```

#### 4.3 Enhanced Admission History Table

**Location**: Lines 137-178 in admission_section.html

Add "Actions" column:

```html
<table class="table table-sm">
  <thead>
    <tr>
      <!-- existing columns -->
      <th>Ações</th>
    </tr>
  </thead>
  <tbody>
    {% for admission in admissions %}
    <tr>
      <!-- existing data -->
      <td>
        {% get_admission_edit_actions user patient admission as actions %} {%
        for action in actions %}
        <button
          class="btn btn-sm {{ action.btn_class }}"
          data-bs-toggle="modal"
          data-bs-target="#{{ action.action_name }}Modal"
          data-admission-id="{{ admission.id }}"
        >
          <i class="fas fa-{{ action.icon }}"></i>
        </button>
        {% endfor %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

### Phase 5: JavaScript Enhancement

#### 5.1 Modal Population Script

Add to admission_section.html:

```javascript
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Modal population handlers
    document.querySelectorAll('[data-bs-target="#editAdmissionModal"]').forEach(button => {
        button.addEventListener('click', function() {
            const admissionId = this.dataset.admissionId;
            populateEditAdmissionModal(admissionId);
        });
    });

    // Similar handlers for edit discharge modal
});

function populateEditAdmissionModal(admissionId) {
    // Fetch admission data and populate form fields
    // Handle via AJAX or embed data in template
}
</script>
```

### Phase 6: Testing Strategy

#### 6.1 Permission Tests

**File**: `apps/patients/tests/test_admission_permissions.py`

```python
class AdmissionEditPermissionTests(TestCase):
    def test_can_edit_admission_data_creator_within_24h(self):
        """Creator can edit admission data within 24h"""

    def test_cannot_edit_admission_data_creator_after_24h(self):
        """Creator cannot edit admission data after 24h"""

    def test_doctor_can_always_edit_active_admission(self):
        """Doctors/residents can always edit active admissions"""

    def test_can_edit_discharge_data_within_24h(self):
        """Doctors/residents can edit discharge data within 24h"""

    def test_cannot_edit_discharge_data_after_24h(self):
        """Cannot edit discharge data after 24h window"""
```

#### 6.2 Integration Tests

**File**: `apps/patients/tests/test_admission_edit_views.py`

```python
class AdmissionEditViewTests(TestCase):
    def test_edit_admission_data_success(self):
        """Successful admission data edit"""

    def test_edit_discharge_data_success(self):
        """Successful discharge data edit"""

    def test_cancel_discharge_success(self):
        """Successful discharge cancellation"""
```

#### 6.3 UI Tests

Test modal population, form submission, permission-based button visibility.

### Phase 7: Documentation

#### 7.1 Update CLAUDE.md

Document new commands and testing approaches:

```bash
# Test admission edit permissions
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_permissions.py

# Test admission edit views
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_admission_edit_views.py
```

#### 7.2 Create User Guide

Document the new edit capabilities for medical staff.

## Timeline Event Cards Integration

The timeline system already has dedicated cards for admission and discharge events. This implementation will enhance them with proper permission-based action buttons:

### Admission Timeline Card
- **View button** (always visible) 
- **Edit Admission button** (if `can_edit_admission_data`)
- **Discharge button** (if `can_discharge_patient` and admission is active)

### Discharge Timeline Card  
- **View button** (always visible)
- **Edit Discharge button** (if `can_edit_discharge_data`)
- **Cancel Discharge button** (if `can_cancel_discharge`)

### Modal Integration
- Same modals will be shared between patient detail page and timeline
- JavaScript will handle modal population based on `data-admission-id` 
- Forms will submit to same view endpoints

This creates a **consistent editing experience** across both the patient detail page and timeline view.

## Implementation Sequence

### Sprint 1: Foundation (1-2 days)

- Phase 1: Permission System Foundation
- Phase 2: Forms Enhancement
- Basic testing

### Sprint 2: Views & URLs (1 day)

- Phase 3: View Layer Enhancement
- URL pattern updates
- Permission integration testing

### Sprint 3: UI Enhancement (2 days)

- Phase 4: Template Enhancement
- Phase 5: JavaScript Enhancement
- UI/UX testing

### Sprint 4: Testing & Polish (1 day)

- Phase 6: Comprehensive Testing
- Phase 7: Documentation
- Final integration testing

## Risk Mitigation

### Data Integrity

- Form validation prevents invalid state transitions
- Database constraints ensure data consistency
- Audit trail preserves edit history

### Permission Security

- All edit actions require explicit permission checks
- Time-based constraints prevent stale edits
- Role-based restrictions maintain medical workflow integrity

### UI/UX Consistency

- Maintains existing modal-based interaction patterns
- Preserves current styling and layout
- Enhances rather than replaces existing functionality

## Success Criteria

1. **Functional**:

   - Users can edit admission data within 24h of creation
   - Doctors/residents can edit discharge data within 24h of discharge
   - Permission system correctly enforces time and role constraints

2. **Technical**:

   - All tests pass with >90% coverage
   - No breaking changes to existing functionality
   - Performance impact <100ms per page load

3. **User Experience**:
   - Intuitive edit buttons in admission history
   - Clear feedback for permission restrictions
   - Smooth modal-based editing workflow

## Future Enhancements

- Audit log viewer for admission edit history
- Batch edit capabilities for multiple admissions
- Advanced permission rules (department-based, etc.)
- Mobile-optimized edit interface

