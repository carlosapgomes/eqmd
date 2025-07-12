# Hospital Inventory - Phase 1 Analysis Results

**Date:** 2025-07-11  
**Phase:** 1 (Analysis and Preparation)  
**Status:** Complete

## Executive Summary

Comprehensive analysis reveals extensive hospital-related architecture throughout the codebase. Key findings:

- **36 test files** require modification/removal
- **3 core models** need refactoring (User, Patient, PatientHospitalRecord)
- **1 entire app** to remove (hospitals)
- **5 permission files** need major simplification
- **34 template files** reference hospital context
- **50+ Python files** contain hospital imports/references

## Files to Remove Completely

### Hospital App (Entire Directory)
- [ ] `apps/hospitals/` - Complete removal
  - `models.py` (Hospital, Ward models)
  - `views.py` (15 hospital-related views)
  - `forms.py` (HospitalForm, WardForm)
  - `admin.py` (Hospital, Ward admin)
  - `middleware.py` (HospitalContextMiddleware)
  - `context_processors.py` (hospital_context)
  - `templatetags/hospital_tags.py`
  - `templates/hospitals/` (8 template files)
  - `tests/` (5 test files)
  - `urls.py`
  - `apps.py`
  - `migrations/` (all migration files)

### Hospital-Related Test Files
- [ ] `apps/hospitals/tests.py`
- [ ] `apps/hospitals/tests/test_*.py` (5 files)
- [ ] `apps/core/tests/test_hospital_membership.py`
- [ ] `apps/core/test_views_hospital_context.py`

### Hospital-Specific Templates
- [ ] `apps/core/templates/core/test_hospital_context*.html` (2 files)
- [ ] All templates in `apps/hospitals/templates/`

## Models to Modify

### User Model (`apps/accounts/models.py`)
**Current State:** Lines 30-43
```python
hospitals = models.ManyToManyField('hospitals.Hospital', ...)
last_hospital = models.ForeignKey('hospitals.Hospital', ...)
```

**Required Changes:**
- [ ] Remove `hospitals` M2M field
- [ ] Remove `last_hospital` ForeignKey field
- [ ] Remove `get_default_hospital()` method

**Risk Level:** HIGH - Central to authentication system

### Patient Model (`apps/patients/models.py`)
**Current State:** Lines 123-128
```python
current_hospital = models.ForeignKey("hospitals.Hospital", ...)
```

**Required Changes:**
- [ ] Remove `current_hospital` ForeignKey field
- [ ] Remove hospital-related methods:
  - `requires_hospital_assignment` property
  - `should_clear_hospital_assignment` property
  - `has_hospital_record_at()` method
  - `is_currently_admitted()` method

**Risk Level:** HIGH - Core patient management

### PatientHospitalRecord Model (`apps/patients/models.py`)
**Current State:** Lines 262-299
- Complete model for tracking patient-hospital relationships

**Required Changes:**
- [ ] **REMOVE ENTIRE MODEL** - No longer needed in single-hospital architecture

**Risk Level:** HIGH - Data loss, many FK references

## Permission System Files (Major Simplification)

### Core Permission Files
- [ ] `apps/core/permissions/utils.py`
  - Lines 72, 247-261: `has_hospital_context()` function
  - Lines 474, 493: Hospital context checks
  - Lines 98, 648: Hospital model imports
  - **Action:** Remove all hospital-aware permission logic

- [ ] `apps/core/permissions/cache.py`
  - Lines 18-35: Hospital context cache keys
  - Lines 75-81: Hospital context ID generation
  - **Action:** Simplify cache keys, remove hospital parameters

- [ ] `apps/core/permissions/decorators.py`
  - Lines 99-108: `@hospital_context_required` decorator
  - **Action:** Remove decorator entirely

- [ ] `apps/core/permissions/__init__.py`
  - Lines 16, 32, 84, 99: Hospital context exports
  - **Action:** Remove hospital-related exports

- [ ] `apps/core/permissions/queries.py`
  - Line 103: Hospital model import
  - **Action:** Remove hospital-related query optimizations

## Settings and Configuration Changes

### Django Settings (`config/settings.py`)
- [ ] Line 66: Remove `"apps.hospitals"` from INSTALLED_APPS
- [ ] Line 106: Remove `"apps.hospitals.middleware.HospitalContextMiddleware"` from MIDDLEWARE
- [ ] Line 127: Remove `"apps.hospitals.context_processors.hospital_context"` from TEMPLATES

### URL Configuration
- [ ] `config/urls.py`: Remove hospital URL includes (if any)
- [ ] Remove all hospital-related URL patterns

## Views and Forms Requiring Changes

### Major View Files (Hospital Context Dependencies)
- [ ] `apps/simplenotes/views.py` - 8 views with `@hospital_context_required`
- [ ] `apps/outpatientprescriptions/views.py` - 6 views with hospital filtering
- [ ] `apps/dailynotes/views.py` - 8 views with hospital context
- [ ] `apps/historyandphysicals/views.py` - 7 views with hospital dependencies
- [ ] `apps/patients/views.py` - Patient-hospital record management
- [ ] `apps/mediafiles/admin.py` - Hospital-based filtering

### Form Files
- [ ] `apps/patients/forms.py` - PatientHospitalRecordForm, hospital fields
- [ ] All forms referencing `current_hospital` field
- [ ] Hospital selection forms

## Template Impact (34 Files)

### Critical Template Changes
- [ ] `apps/patients/templates/patients/patient_form.html` - Hospital field removal
- [ ] `apps/patients/templates/patients/patient_list.html` - Hospital column removal
- [ ] Print templates in multiple apps showing hospital info
- [ ] Dashboard widgets showing hospital context

### Template Tags Requiring Updates
- [ ] `apps/simplenotes/templatetags/simplenote_tags.py` - Hospital filtering
- [ ] `apps/dailynotes/templatetags/dailynote_tags.py` - Hospital context
- [ ] `apps/historyandphysicals/templatetags/historyandphysical_tags.py` - Hospital filtering

## Database Schema Impact

### Foreign Key Relationships to Remove
1. **User.hospitals** (M2M) → Hospital
2. **User.last_hospital** (FK) → Hospital  
3. **Patient.current_hospital** (FK) → Hospital
4. **PatientHospitalRecord.hospital** (FK) → Hospital
5. **PatientHospitalRecord.patient** (FK) → Patient
6. **Ward.hospital** (FK) → Hospital

### Migration Strategy
Since this is a greenfield project:
- [ ] Delete all existing migrations in affected apps
- [ ] Create fresh initial migrations after model changes
- [ ] No data preservation required

## Test Files Impact (36 Files)

### Files Requiring Major Changes
- [ ] 34 test files with hospital imports/references
- [ ] 2 standalone test files in hospitals app
- [ ] All factory files creating hospital objects
- [ ] Permission tests validating hospital context

### Test Categories to Update
1. **Permission Tests** - Remove hospital context validation
2. **Model Tests** - Remove hospital relationship tests  
3. **View Tests** - Remove hospital filtering tests
4. **Integration Tests** - Simplify multi-hospital scenarios
5. **Form Tests** - Remove hospital field validation

## Management Commands

### Commands Requiring Updates
- [ ] `apps/core/management/commands/setup_groups.py` - Hospital model references
- [ ] `apps/core/management/commands/assign_users_to_hospitals.py` - **REMOVE ENTIRELY**
- [ ] `apps/core/management/commands/populate_sample_data.py` - Hospital data creation

## Risk Assessment

### High Risk Changes
1. **User Model** - Central authentication impacts
2. **Patient Model** - Core business logic
3. **Permission System** - Security implications
4. **PatientHospitalRecord** - Data relationships

### Medium Risk Changes
1. **View Logic** - Business rule changes
2. **Template Updates** - UI consistency
3. **Test Suite** - Comprehensive updates needed

### Low Risk Changes
1. **Hospital App Removal** - Self-contained
2. **Settings Updates** - Configuration only
3. **Management Commands** - Utility functions

## Critical Dependencies Identified

### Inter-App Dependencies
1. **accounts** ↔ **hospitals** (User.hospitals M2M)
2. **patients** ↔ **hospitals** (Patient.current_hospital FK)
3. **core.permissions** ↔ **hospitals** (context middleware)
4. **All event apps** ↔ **hospitals** (permission filtering)

### Business Logic Dependencies
1. **Patient Status Logic** - Hospital assignment rules
2. **Permission Filtering** - Hospital-based access control
3. **Dashboard Widgets** - Hospital context display
4. **Report Generation** - Hospital-specific data

## Estimated Effort per Subsequent Phase

### Phase 2 (Models) - HIGH
- 8-12 hours
- Complex migration handling
- Data model restructuring

### Phase 3 (Permissions) - HIGH  
- 6-8 hours
- Security-critical changes
- Extensive testing required

### Phase 4 (Views/Forms) - MEDIUM
- 4-6 hours
- Business logic updates
- Form validation changes

### Phase 5 (Templates) - MEDIUM
- 3-4 hours  
- UI consistency updates
- Template tag modifications

### Phase 6 (Settings) - LOW
- 1-2 hours
- Configuration changes
- Middleware removal

### Phase 7 (Testing) - HIGH
- 6-8 hours
- 36 test files to update
- New test scenarios

### Phase 8 (Documentation) - LOW
- 2-3 hours
- CLAUDE.md updates
- Documentation consistency

## Safety Measures Completed

- [x] Current branch committed and tracked
- [x] Git status documented
- [x] Backup available in `prescriptions` branch
- [x] Comprehensive inventory created
- [x] Dependencies mapped
- [x] Risk assessment completed

## Next Phase Prerequisites

Before proceeding to Phase 2:
- [x] Complete inventory created ✓
- [x] All hospital references catalogued ✓  
- [x] Database impact understood ✓
- [x] Safety measures in place ✓
- [x] Estimated effort documented ✓

## Critical Notes for Implementation

1. **Order Matters**: Remove PatientHospitalRecord model before Patient.current_hospital field
2. **Permission Impact**: Simplification may temporarily break access control
3. **Test Coverage**: Maintain equivalent test coverage without hospital context
4. **Business Rules**: Preserve patient status logic without hospital dependencies
5. **Migration Strategy**: Fresh migrations preferred over complex field removals

## Success Metrics

After refactor completion:
- [ ] 40-60% codebase size reduction achieved
- [ ] No hospital-related imports remain
- [ ] All tests pass with simplified logic
- [ ] Permission system maintains security without hospital context
- [ ] Single-hospital configuration working