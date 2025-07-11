# Phase 3: Permission System Simplification

**Estimated Time:** 60-90 minutes  
**Complexity:** High  
**Dependencies:** Phase 2 completed

## Objectives

1. Drastically simplify the permission system by removing hospital context logic
2. Remove hospital-aware caching
3. Simplify permission decorators
4. Update permission utilities to role-based only

## Tasks

### 1. Simplify Core Permission Utils (`apps/core/permissions/utils.py`)

**Current complexity:** ~756 lines with intricate hospital-dependent rules  
**Target:** ~200 lines with simple role-based permissions

**Remove hospital context logic:**
- [ ] Remove `can_access_patient()` hospital matching logic
- [ ] Remove `has_hospital_context()` checks
- [ ] Remove `get_user_accessible_patients()` hospital filtering
- [ ] Simplify to role-based access only

**Before (complex hospital logic):**
```python
def can_access_patient(user, patient):
    if patient.status in [INPATIENT, EMERGENCY, TRANSFERRED]:
        # Complex hospital matching
        if not has_hospital_context(user):
            return False
        return user.current_hospital.id == patient.current_hospital_id
    elif patient.status in [OUTPATIENT, DISCHARGED]:
        # Complex fallback logic with hospital records
        # Multiple hospital membership checks
    # ... 100+ lines of complex logic
```

**After (simple role-based):**
```python
def can_access_patient(user, patient):
    # Simple role-based access
    if user.profession == 'student':
        return patient.status in ['outpatient', 'discharged']
    return True  # All other roles can access all patients
```

**Simplified permission functions:**
- [ ] `can_access_patient(user, patient)` - Role-based only
- [ ] `can_edit_event(user, event)` - Time-based + role-based
- [ ] `can_change_patient_status(user, patient, status)` - Role-based only
- [ ] `can_change_patient_personal_data(user, patient)` - Doctor-only

### 2. Remove Hospital Context Functions

**Delete these functions entirely:**
- [ ] `has_hospital_context(user)`
- [ ] `get_user_hospitals(user)`
- [ ] `get_patients_for_hospital(hospital)`
- [ ] Any hospital membership validation functions

### 3. Simplify Permission Decorators (`apps/core/permissions/decorators.py`)

**Remove hospital-related decorators:**
- [ ] `@hospital_context_required`
- [ ] `@patient_hospital_access_required`
- [ ] Any decorators checking hospital membership

**Keep and simplify:**
- [ ] `@patient_access_required` - Remove hospital logic
- [ ] `@doctor_required` - Keep as-is
- [ ] `@nurse_required` - Keep as-is

**Example simplification:**
```python
# Before (complex hospital logic)
def patient_access_required(view_func):
    def wrapper(request, *args, **kwargs):
        patient = get_object_or_404(Patient, id=kwargs['patient_id'])
        if not can_access_patient(request.user, patient):
            # Complex hospital context checks
        # ... complex logic

# After (simple role check)
def patient_access_required(view_func):
    def wrapper(request, *args, **kwargs):
        patient = get_object_or_404(Patient, id=kwargs['patient_id'])
        if not can_access_patient(request.user, patient):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
```

### 4. Remove Hospital-Aware Caching (`apps/core/permissions/cache.py`)

**Remove hospital context from cache keys:**
- [ ] Remove hospital_id from cache key generation
- [ ] Simplify cache invalidation logic
- [ ] Remove hospital-specific cache versioning

**Simplify caching:**
```python
# Before (hospital-aware)
def get_cache_key(user, patient, action):
    hospital_id = getattr(user, 'current_hospital_id', 'none')
    return f"perm:{user.id}:{patient.id}:{action}:{hospital_id}"

# After (simple)
def get_cache_key(user, patient, action):
    return f"perm:{user.id}:{patient.id}:{action}"
```

### 5. Update Permission Backend (`apps/core/permissions/backends.py`)

**Remove hospital context logic:**
- [ ] Remove hospital membership checks
- [ ] Simplify permission checking to role-based only
- [ ] Remove hospital context from permission resolution

### 6. Simplify Patient Access Queries

**Update `get_user_accessible_patients()`:**
```python
# Before (complex hospital filtering)
def get_user_accessible_patients(user):
    if user.profession == 'student':
        return Patient.objects.filter(
            status__in=['outpatient', 'discharged'],
            # Complex hospital membership logic
        )
    # More complex logic based on hospitals

# After (simple role filtering)
def get_user_accessible_patients(user):
    if user.profession == 'student':
        return Patient.objects.filter(status__in=['outpatient', 'discharged'])
    return Patient.objects.all()
```

### 7. Update Template Tags (`apps/core/templatetags/permission_tags.py`)

**Remove hospital-related template tags:**
- [ ] Remove any hospital context template tags
- [ ] Simplify permission checking template tags
- [ ] Remove hospital membership checks

### 8. Update Management Commands

**Simplify permission-related management commands:**
- [ ] `apps/core/management/commands/permission_audit.py`
- [ ] Remove hospital context from permission reports
- [ ] Simplify user permission assignment commands

## Simplified Permission Model

### New Permission Rules (Much Simpler)

**Doctors:**
- Full access to all patients
- Can discharge patients
- Can edit patient personal data

**Residents/Physiotherapists:**
- Full access to all patients
- Cannot discharge patients

**Nurses:**
- Access to all patients
- Limited status changes (cannot discharge)
- Cannot edit patient personal data

**Students:**
- View-only access to outpatients and discharged patients only
- No access to inpatients, emergency, or transferred patients

### Time-Based Rules (Unchanged)
- 24-hour edit/delete window for events
- Role-based event editing permissions

## Critical File Changes

### Files to Modify:
- [ ] `apps/core/permissions/utils.py` - Major simplification
- [ ] `apps/core/permissions/decorators.py` - Remove hospital decorators
- [ ] `apps/core/permissions/cache.py` - Remove hospital context
- [ ] `apps/core/permissions/backends.py` - Simplify permission backend
- [ ] `apps/core/templatetags/permission_tags.py` - Remove hospital tags

### Files to Delete:
- [ ] Any hospital-specific permission modules
- [ ] Hospital context management utilities

## Testing Strategy

**Test the simplified permissions:**
```python
# Test basic role access
def test_doctor_access_all_patients():
    # Doctor can access any patient

def test_student_access_outpatients_only():
    # Student can only access outpatients

def test_role_based_patient_operations():
    # Test status changes by role
```

## Validation Checklist

Before proceeding to Phase 4:
- [ ] Permission system reduced to ~200 lines
- [ ] No hospital context references in permission code
- [ ] All permission decorators work without hospital logic
- [ ] Cache system simplified
- [ ] Basic permission tests pass
- [ ] No import errors from removed hospital functions

## Performance Impact

**Expected improvements:**
- Faster permission checks (no hospital context lookups)
- Simpler database queries
- Reduced cache complexity
- Faster user authentication

## Risk Mitigation

**Ensure security is maintained:**
- [ ] Role-based restrictions still enforced
- [ ] Time-based edit windows preserved
- [ ] Student access properly limited
- [ ] No accidental permission escalation