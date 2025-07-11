# Phase 2: Database Models Refactor

**Estimated Time:** 45-60 minutes  
**Complexity:** High  
**Dependencies:** Phase 1 completed

## Objectives

1. Remove hospital-related Django models
2. Remove hospital fields from existing models
3. Create and run database migrations
4. Ensure data integrity during transition

## Tasks

### 1. Remove Hospital Models

**Remove entire `apps/hospitals/` app:**
- [ ] Delete `apps/hospitals/models.py` (Hospital, Ward models)
- [ ] Delete all hospital migrations
- [ ] Remove from `INSTALLED_APPS` in settings

### 2. Modify User Model (`apps/accounts/models.py`)

**Changes to User model:**
- [ ] Remove `hospitals = models.ManyToManyField(Hospital, blank=True)`
- [ ] Remove `last_hospital = models.ForeignKey(Hospital, null=True, blank=True)`
- [ ] Remove methods: `get_default_hospital()`, `is_hospital_member()`
- [ ] Remove hospital-related properties

**Before:**
```python
class User(AbstractUser):
    hospitals = models.ManyToManyField(Hospital, blank=True)
    last_hospital = models.ForeignKey(Hospital, null=True, blank=True)
    
    def get_default_hospital(self):
        # Complex logic
    
    def is_hospital_member(self, hospital):
        # Membership check
```

**After:**
```python
class User(AbstractUser):
    # Hospital fields removed
    # Methods removed
```

### 3. Modify Patient Model (`apps/patients/models.py`)

**Remove from Patient model:**
- [ ] `current_hospital = models.ForeignKey(Hospital, null=True, blank=True)`
- [ ] Hospital-related validation in `clean()` method
- [ ] Hospital assignment logic in `save()` method
- [ ] Methods: `requires_hospital_assignment`, `should_clear_hospital_assignment`

**Remove PatientHospitalRecord model entirely:**
- [ ] Delete entire `PatientHospitalRecord` class
- [ ] Remove related admin configurations

**Simplify patient status logic:**
- [ ] Remove hospital requirement validation
- [ ] Simplify status change logic
- [ ] Remove hospital-dependent status rules

### 4. Update Related Models

**Check and update any other models with hospital references:**
- [ ] Search for any ForeignKey(Hospital) relationships
- [ ] Remove hospital-related fields from any other models
- [ ] Update model `__str__` methods that reference hospitals

### 5. Create Database Migrations

**Migration sequence (important order):**

1. **First migration:** Remove PatientHospitalRecord model
   ```bash
   python manage.py makemigrations patients --name remove_patient_hospital_record
   ```

2. **Second migration:** Remove hospital fields from Patient
   ```bash
   python manage.py makemigrations patients --name remove_hospital_fields
   ```

3. **Third migration:** Remove hospital fields from User
   ```bash
   python manage.py makemigrations accounts --name remove_hospital_fields
   ```

4. **Fourth migration:** Remove hospitals app
   ```bash
   python manage.py makemigrations hospitals --name remove_app --empty
   ```

### 6. Update Model Admin

**Remove hospital-related admin configurations:**
- [ ] Remove hospital fields from admin forms
- [ ] Remove hospital filters from admin list views
- [ ] Update admin fieldsets to exclude hospital fields
- [ ] Remove hospital-related admin actions

### 7. Database Migration Execution

**Run migrations carefully:**
```bash
# Test migrations first
python manage.py migrate --dry-run

# Apply migrations
python manage.py migrate
```

### 8. Model Validation

**Verify models work correctly:**
- [ ] Run `python manage.py check`
- [ ] Test model creation in Django shell
- [ ] Verify no broken relationships
- [ ] Test model admin interfaces

## Critical Considerations

### Data Loss Warning
- All hospital assignments will be lost
- PatientHospitalRecord history will be deleted
- User-hospital memberships will be removed

### Migration Order
Execute migrations in the specified order to avoid foreign key constraint errors.

### Rollback Plan
Before starting:
- [ ] Create database backup
- [ ] Document current schema
- [ ] Test migration rollback procedures

## Validation Checklist

Before proceeding to Phase 3:
- [ ] All hospital models removed
- [ ] No hospital field references in models
- [ ] Migrations completed successfully
- [ ] `python manage.py check` passes
- [ ] Models can be created/queried without errors
- [ ] Admin interfaces load correctly

## Files Modified

Document all files changed in this phase:
- `apps/accounts/models.py`
- `apps/patients/models.py`
- `apps/accounts/admin.py`
- `apps/patients/admin.py`
- New migration files

## Next Phase Preparation

Ensure these items are ready for Phase 3:
- [ ] All models are hospital-free
- [ ] Database is migrated
- [ ] No import errors from removed hospital models