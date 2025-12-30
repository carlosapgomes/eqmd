# Patient Status Management Refactor Plan

## Overview

Consolidate patient status changes to the Patient Details Page only, removing status from the Patient Edit Form and implementing automatic timeline event creation for all status changes.

**Note**: This is a greenfield project - no migration concerns, database will be recreated with sample data.

## Current State Analysis

### Issues to Resolve

1. **Inconsistent UX**: Status can be changed in two places with different behaviors
2. **Missing audit trail**: Edit form changes don't create timeline events
3. **Limited status options**: Details page only supports inpatient/discharged
4. **Poor medical workflow**: Status changes buried in general edit form
5. **No validation context**: Edit form doesn't show status-specific requirements

### Current Implementation

- **Patient Edit Form**: Full status dropdown, no timeline events
- **Patient Details Page**: Limited admit/discharge actions, creates timeline events

## Goals

### Primary Objectives

1. **Single source of truth**: All status changes through Details Page only
2. **Complete audit trail**: Every status change creates a timeline event
3. **Medical workflow compliance**: Prominent, intentional status change actions
4. **Role-based access**: Show only allowed actions per user profession
5. **Context-aware UX**: Show implications of status changes

### Technical Goals

1. Remove status field from Patient Edit Form
2. Expand Details Page with all 6 status types
3. Implement automatic event creation for all status changes
4. Add proper validation and permission checks
5. Create status-specific UI components

## Implementation Plan

### Phase 1: Event System Foundation

#### 1.1 Create New Event Types

**Location**: `apps/events/models.py`

Add new event types for missing status changes:

```python
# Add to Event.EVENT_TYPE_CHOICES
STATUS_CHANGE_EVENT = 15          # General status change
EMERGENCY_ADMISSION_EVENT = 16    # Emergency status
TRANSFER_EVENT = 17               # Transfer status  
DEATH_DECLARATION_EVENT = 18      # Deceased status
OUTPATIENT_STATUS_EVENT = 19      # Outpatient status
```

#### 1.2 Create Status Change Event Model

**Location**: `apps/events/models.py`

```python
class StatusChangeEvent(Event):
    """Event for tracking patient status changes in timeline"""
    
    previous_status = models.PositiveSmallIntegerField(
        choices=Patient.Status.choices,
        verbose_name="Status Anterior"
    )
    new_status = models.PositiveSmallIntegerField(
        choices=Patient.Status.choices,
        verbose_name="Novo Status"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração"
    )
    
    # Optional fields for specific status changes
    ward = models.ForeignKey(
        'patients.Ward',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Ala"
    )
    bed = models.CharField(
        max_length=20, blank=True,
        verbose_name="Leito"
    )
    discharge_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alta"
    )
    death_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Hora do Óbito"
    )
```

#### 1.3 Database Reset

**Action**: Reset database and recreate sample data with new event types
**Command**: `./reset_database.sh && python manage.py create_sample_*`

### Phase 2: Signal System Implementation

#### 2.1 Create Status Change Signal Handler

**Location**: `apps/patients/signals.py`

```python
@receiver(pre_save, sender=Patient)
def track_status_changes(sender, instance, **kwargs):
    """Track patient status changes and create timeline events"""
    
    if instance.pk:  # Only for existing patients
        try:
            old_instance = Patient.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Store for post_save signal
                instance._status_changed = True
                instance._old_status = old_instance.status
                instance._new_status = instance.status
        except Patient.DoesNotExist:
            pass

@receiver(post_save, sender=Patient)
def create_status_change_event(sender, instance, created, **kwargs):
    """Create timeline event for status changes"""
    
    if not created and getattr(instance, '_status_changed', False):
        # Create StatusChangeEvent with appropriate details
        pass
```

#### 2.2 Update Existing Signals

**Location**: `apps/patients/signals.py`

Update existing admission/discharge signals to work with new status change system.

### Phase 3: Remove Status from Edit Form

#### 3.1 Update Patient Form

**Location**: `apps/patients/forms.py`

```python
class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'birthday', 'id_number', 'fiscal_number', 
                  'healthcard_number', 'phone', 'address', 'city', 'state', 
                  'zip_code', 'ward', 'bed']  # Remove 'status'
        
    def clean(self):
        """Remove status-related validation"""
        cleaned_data = super().clean()
        # Remove bed clearing logic - will be handled by status actions
        return cleaned_data
```

#### 3.2 Update Patient Edit Templates

**Location**: `apps/patients/templates/patients/patient_form.html`

Remove status field from form display and add notice about status changes.

### Phase 4: Expand Details Page Actions

#### 4.1 Create Status Change Views

**Location**: `apps/patients/views.py`

Create individual views for each status change:

```python
class PatientStatusChangeView(View):
    """Base view for patient status changes"""
    
class AdmitPatientView(PatientStatusChangeView):
    """Change patient status to inpatient"""
    
class DischargePatientView(PatientStatusChangeView):
    """Change patient status to discharged"""
    
class EmergencyAdmissionView(PatientStatusChangeView):
    """Change patient status to emergency"""
    
class TransferPatientView(PatientStatusChangeView):
    """Change patient status to transferred"""
    
class DeclareDeathView(PatientStatusChangeView):
    """Change patient status to deceased"""
    
class SetOutpatientView(PatientStatusChangeView):
    """Change patient status to outpatient"""
```

#### 4.2 Create Status Change Forms

**Location**: `apps/patients/forms.py`

```python
class StatusChangeForm(forms.Form):
    """Base form for status changes"""
    reason = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Motivo da Alteração"
    )

class AdmitPatientForm(StatusChangeForm):
    ward = forms.ModelChoiceField(
        queryset=Ward.objects.filter(is_active=True),
        required=True
    )
    bed = forms.CharField(max_length=20, required=False)

class DischargePatientForm(StatusChangeForm):
    discharge_reason = forms.CharField(
        widget=forms.Textarea,
        required=True,
        label="Motivo da Alta"
    )

class DeclareDeathForm(StatusChangeForm):
    death_time = forms.DateTimeField(
        required=True,
        label="Hora do Óbito"
    )
    reason = forms.CharField(
        widget=forms.Textarea,
        required=True,
        label="Causa do Óbito"
    )
```

#### 4.3 Update Patient Detail Template

**Location**: `apps/patients/templates/patients/patient_detail.html`

Add status change action buttons:

```html
<!-- Status Change Actions Section -->
<div class="card mt-4">
    <div class="card-header">
        <h5>Alterar Status do Paciente</h5>
    </div>
    <div class="card-body">
        <!-- Current Status Display -->
        <div class="current-status mb-3">
            <strong>Status Atual:</strong> 
            {% patient_status_badge patient.status %}
        </div>
        
        <!-- Action Buttons (based on permissions and current status) -->
        <div class="status-actions">
            {% if user|can_change_status:patient %}
                <!-- Conditional buttons based on current status and user permissions -->
            {% endif %}
        </div>
    </div>
</div>
```

#### 4.4 Create Status Change Modals

**Location**: `apps/patients/templates/patients/partials/status_change_modals.html`

Create modal dialogs for each status change with appropriate forms.

### Phase 5: Permission Integration

#### 5.1 Create Template Tags

**Location**: `apps/patients/templatetags/patient_tags.py`

```python
@register.filter
def can_change_status(user, patient):
    """Check if user can change patient status"""
    return can_change_patient_status(user, patient, None)

@register.filter
def available_status_actions(user, patient):
    """Get list of available status change actions for user/patient"""
    actions = []
    current_status = patient.status
    
    # Check each possible status change
    for status_value, status_label in Patient.Status.choices:
        if status_value != current_status:
            if can_change_patient_status(user, patient, status_value):
                actions.append({
                    'status': status_value,
                    'label': status_label,
                    'action_name': get_action_name(current_status, status_value)
                })
    
    return actions
```

#### 5.2 Update Permission System

**Location**: `apps/core/permissions/utils.py`

Ensure `can_change_patient_status` properly handles all 6 status types including deceased.

### Phase 6: URL Configuration

#### 6.1 Add Status Change URLs

**Location**: `apps/patients/urls.py`

```python
# Add new URL patterns for status changes
path('patients/<uuid:pk>/admit/', AdmitPatientView.as_view(), name='admit_patient'),
path('patients/<uuid:pk>/discharge/', DischargePatientView.as_view(), name='discharge_patient'),
path('patients/<uuid:pk>/emergency/', EmergencyAdmissionView.as_view(), name='emergency_admission'),
path('patients/<uuid:pk>/transfer/', TransferPatientView.as_view(), name='transfer_patient'),
path('patients/<uuid:pk>/declare-death/', DeclareDeathView.as_view(), name='declare_death'),
path('patients/<uuid:pk>/set-outpatient/', SetOutpatientView.as_view(), name='set_outpatient'),
```

### Phase 7: Frontend Implementation

#### 7.1 Create JavaScript for Status Changes

**Location**: `static/js/patient_status.js`

Handle modal displays, form submissions, and AJAX requests for status changes.

#### 7.2 Update CSS Styling

**Location**: `static/css/patients.css`

Add styles for:

- Status action buttons
- Status change modals
- Success/error notifications
- Status-specific indicators

### Phase 8: Testing

#### 8.1 Update Existing Tests

**Files to update**:

- `apps/patients/tests/test_forms.py` - Remove status field tests
- `apps/patients/tests/test_views.py` - Update patient edit tests
- `apps/core/tests/test_permissions/` - Update permission tests

#### 8.2 Create New Tests

**New test files**:

- `apps/patients/tests/test_status_changes.py` - Status change view tests
- `apps/patients/tests/test_status_events.py` - Timeline event creation tests
- `apps/patients/tests/test_status_permissions.py` - Permission integration tests

#### 8.3 Test Scenarios

1. **Permission Tests**: Each role can only access allowed status changes
2. **Event Creation**: Every status change creates appropriate timeline event
3. **Validation Tests**: Invalid status changes are properly rejected
4. **Signal Tests**: Status change signals work correctly
5. **UI Tests**: Modal forms and button states work properly

### Phase 9: Documentation and Sample Data

#### 9.1 Update Documentation

**Files to update**:

- `CLAUDE.md` - Update status change documentation
- `docs/patients/patient_management.md` - Update user guide

#### 9.2 Update Sample Data Creation

**Files to update**:

- `apps/core/management/commands/populate_sample_data.py` - Include status change events
- `apps/patients/management/commands/create_sample_*.py` - Generate realistic status transitions

#### 9.3 User Communication

- Update user training materials
- Create changelog entry

## Implementation Order

### Phase 1: Foundation (Day 1)

1. Create new event types and StatusChangeEvent model
2. Reset database with new structure
3. Implement basic signal structure

### Phase 2: Backend (Day 2)

1. Remove status from Patient Edit Form
2. Create status change views and forms
3. Implement signal handlers for event creation

### Phase 3: Frontend (Day 3)

1. Update Patient Detail template
2. Create status change modals
3. Implement JavaScript functionality

### Phase 4: Integration (Day 4)

1. Add permission checks and template tags
2. Configure URLs
3. Update CSS styling

### Phase 5: Testing & Polish (Day 5)

1. Update existing tests
2. Create new test coverage
3. Fix any bugs and polish UX
4. Reset database and generate comprehensive sample data

## Risk Mitigation

### Potential Issues

1. **Data consistency**: Status changes might bypass validation
2. **Permission complexity**: Multiple status changes need proper permission checks
3. **User confusion**: Major workflow change requires user education
4. **Performance**: Additional event creation might impact performance

### Mitigation Strategies

1. **Comprehensive testing**: Full test coverage for all status changes
2. **Fresh database**: Clean slate approach eliminates migration complexity
3. **User training**: Update documentation and provide training materials
4. **Monitoring**: Monitor event creation performance
5. **Iterative development**: Test each phase thoroughly before proceeding

## Success Criteria

### Functional Requirements

- ✅ All status changes go through Patient Details Page only
- ✅ Every status change creates a timeline event
- ✅ Proper permission enforcement for all status types
- ✅ Status-specific forms and validation
- ✅ Clean removal of status from edit form

### User Experience Requirements

- ✅ Intuitive status change workflow
- ✅ Clear indication of available actions
- ✅ Proper feedback for status changes
- ✅ No confusion about where to change status
- ✅ Mobile-responsive status change interface

### Technical Requirements

- ✅ Clean database structure with new event types
- ✅ Proper event creation for audit trail
- ✅ Performance impact minimal
- ✅ Full test coverage maintained
- ✅ Clean, maintainable code structure
- ✅ Comprehensive sample data for testing
