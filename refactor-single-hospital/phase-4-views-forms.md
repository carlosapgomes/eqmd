# Phase 4: Views and Forms Cleanup

**Estimated Time:** 60-75 minutes  
**Complexity:** Medium  
**Dependencies:** Phase 3 completed

## Objectives

1. Remove hospital-related logic from all views
2. Simplify forms by removing hospital fields and validation
3. Remove hospital context from view responses
4. Update URL patterns to remove hospital-related routes

## Tasks

### 1. Update Patient Views (`apps/patients/views.py`)

**Remove hospital context logic:**
- [ ] Remove hospital filtering from patient list views
- [ ] Remove hospital context from patient detail views
- [ ] Remove hospital validation from patient create/update views
- [ ] Simplify patient search (no hospital filtering)

**Simplify patient queryset filtering:**
```python
# Before (complex hospital filtering)
def get_queryset(self):
    return get_user_accessible_patients(self.request.user).select_related(
        'current_hospital', 'created_by'
    ).prefetch_related('patienthospitalrecord_set__hospital')

# After (simple role filtering)
def get_queryset(self):
    return get_user_accessible_patients(self.request.user).select_related('created_by')
```

### 2. Update Patient Forms (`apps/patients/forms.py`)

**Remove hospital-related fields and logic:**
- [ ] Remove `current_hospital` field from patient forms
- [ ] Remove hospital selection widgets
- [ ] Remove dynamic hospital field requirements
- [ ] Remove hospital record formsets

**Simplify form validation:**
```python
# Before (complex hospital validation)
def clean(self):
    cleaned_data = super().clean()
    status = cleaned_data.get('status')
    current_hospital = cleaned_data.get('current_hospital')
    
    if status in ['inpatient', 'emergency', 'transferred']:
        if not current_hospital:
            raise ValidationError("Hospital required for this status")
    # ... complex validation logic

# After (simple status validation)
def clean(self):
    cleaned_data = super().clean()
    # Simple validations only, no hospital logic
    return cleaned_data
```

**Remove PatientHospitalRecord forms:**
- [ ] Delete `PatientHospitalRecordForm`
- [ ] Remove nested formsets for hospital records
- [ ] Remove hospital record inline forms

### 3. Update Core Views (`apps/core/views.py`)

**Remove hospital context from dashboard:**
- [ ] Remove hospital selection from dashboard
- [ ] Remove hospital-specific widgets
- [ ] Simplify dashboard statistics (no hospital filtering)

**Update context processors:**
- [ ] Remove hospital context from global template context
- [ ] Remove hospital-related template variables

### 4. Update Event Views (`apps/events/views.py`, `apps/dailynotes/views.py`)

**Remove hospital filtering from events:**
- [ ] Remove hospital context from event queries
- [ ] Simplify event access control (role-based only)
- [ ] Remove hospital filtering from event lists

**Simplify event permissions:**
```python
# Before (hospital + role check)
def dispatch(self, request, *args, **kwargs):
    if not has_hospital_context(request.user):
        return redirect('hospital_select')
    # ... complex hospital logic

# After (simple role check)
def dispatch(self, request, *args, **kwargs):
    # Simple permission check only
    return super().dispatch(request, *args, **kwargs)
```

### 5. Remove Hospital Views and URLs

**Delete hospital-specific views:**
- [ ] Delete entire `apps/hospitals/views.py`
- [ ] Remove hospital selection views
- [ ] Remove hospital context switching views
- [ ] Remove ward management views

**Update URL patterns:**
- [ ] Remove hospital URLs from main `urls.py`
- [ ] Remove hospital context URLs
- [ ] Clean up any hospital-related URL includes

### 6. Update MediaFiles Views (`apps/mediafiles/views.py`)

**Remove hospital context from media access:**
- [ ] Remove hospital filtering from media file access
- [ ] Simplify media file permissions (role-based only)
- [ ] Remove hospital context from file serving views

### 7. Update Admin Views

**Simplify admin interfaces:**
- [ ] Remove hospital filters from admin list views
- [ ] Remove hospital fields from admin forms
- [ ] Update admin fieldsets to exclude hospital fields
- [ ] Remove hospital-related admin actions

### 8. Update API Views (if any)

**Remove hospital context from API:**
- [ ] Remove hospital filtering from API endpoints
- [ ] Simplify API permissions
- [ ] Remove hospital context from API responses

### 9. Form Widget Cleanup

**Remove hospital-related widgets:**
- [ ] Remove hospital selection widgets
- [ ] Remove hospital autocomplete fields
- [ ] Remove hospital context from form rendering

### 10. View Permission Decorators

**Update view decorators:**
- [ ] Replace `@hospital_context_required` with simple permission checks
- [ ] Replace `@patient_hospital_access_required` with `@patient_access_required`
- [ ] Remove hospital context from permission decorators

## Critical Form Changes

### Patient Forms Simplification

**Remove from PatientCreateForm/PatientUpdateForm:**
- `current_hospital` field
- Hospital record inline formsets
- Dynamic hospital validation
- Hospital-dependent field visibility

**Simplified patient form:**
```python
class PatientCreateForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth',
            'fiscal_number', 'health_card_number',
            'status',  # No hospital validation
            'phone', 'email', 'address'
        ]
    
    # Simple validation only
    def clean_status(self):
        # Basic status validation without hospital logic
        return self.cleaned_data['status']
```

### Search Forms

**Simplify patient search:**
```python
# Before (hospital-aware search)
class PatientSearchForm(forms.Form):
    hospital = forms.ModelChoiceField(Hospital.objects.all())
    # ... complex hospital filtering

# After (simple search)
class PatientSearchForm(forms.Form):
    query = forms.CharField(max_length=100)
    status = forms.ChoiceField(choices=Patient.STATUS_CHOICES)
    # No hospital fields
```

## View Response Simplification

**Remove hospital context from view responses:**
```python
# Before (complex hospital context)
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['current_hospital'] = self.request.user.current_hospital
    context['available_hospitals'] = self.request.user.hospitals.all()
    # ... complex hospital context

# After (simple context)
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # Simple context only
    return context
```

## Files to Modify

### Primary View Files:
- [ ] `apps/patients/views.py` - Major simplification
- [ ] `apps/patients/forms.py` - Remove hospital fields
- [ ] `apps/core/views.py` - Remove hospital context
- [ ] `apps/events/views.py` - Remove hospital filtering
- [ ] `apps/dailynotes/views.py` - Remove hospital logic
- [ ] `apps/mediafiles/views.py` - Simplify permissions

### Admin Files:
- [ ] `apps/patients/admin.py` - Remove hospital filters
- [ ] `apps/accounts/admin.py` - Remove hospital fields
- [ ] All admin.py files with hospital references

### URL Files:
- [ ] `eqmd/urls.py` - Remove hospital URL includes
- [ ] Remove `apps/hospitals/urls.py`

### Context Processors:
- [ ] Remove hospital context processors
- [ ] Update template context

## Validation Checklist

Before proceeding to Phase 5:
- [ ] All views work without hospital context
- [ ] Forms validate correctly without hospital fields
- [ ] Patient creation/editing works
- [ ] Event creation works
- [ ] Admin interfaces load correctly
- [ ] No import errors from removed hospital views
- [ ] URL patterns resolve correctly

## Testing Strategy

**Test key functionality:**
- [ ] Patient CRUD operations
- [ ] Event creation and editing
- [ ] Dashboard loads correctly
- [ ] Search functionality works
- [ ] Permission decorators work
- [ ] Admin interfaces accessible

## Performance Improvements

**Expected benefits:**
- Faster form validation (no hospital checks)
- Simpler database queries (no hospital joins)
- Faster view rendering (less context)
- Reduced template complexity