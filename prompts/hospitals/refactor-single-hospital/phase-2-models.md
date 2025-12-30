# Phase 2: Database Models Refactor

**Estimated Time:** 30-45 minutes  
**Complexity:** Medium  
**Dependencies:** Phase 1 completed

## Objectives

1. Remove hospital-related Django models
2. Remove hospital fields from existing models
3. Create fresh initial migrations with simplified schema
4. No data migration needed (greenfield project)

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

### 5. Fresh Migration Strategy (Greenfield Approach)

**Delete existing migrations and create fresh ones:**

1. **Remove existing migration files:**

   ```bash
   # Delete all existing migrations (keep __init__.py files)
   find apps/*/migrations/ -name "*.py" ! -name "__init__.py" -delete
   ```

2. **Create fresh initial migrations:**

   ```bash
   uv run python manage.py makemigrations accounts
   uv run python manage.py makemigrations patients
   uv run python manage.py makemigrations events
   uv run python manage.py makemigrations dailynotes
   uv run python manage.py makemigrations mediafiles
   uv run python manage.py makemigrations sample_content
   # Note: No hospitals app migrations needed
   ```

3. **Recreate database (development only):**

   ```bash
   # Drop and recreate database
   rm db.sqlite3  # or drop PostgreSQL database
   uv run python manage.py migrate
   ```

### 6. Update Model Admin

**Remove hospital-related admin configurations:**

- [ ] Remove hospital fields from admin forms
- [ ] Remove hospital filters from admin list views
- [ ] Update admin fieldsets to exclude hospital fields
- [ ] Remove hospital-related admin actions

### 7. Create Superuser and Test Data

**Set up fresh database:**

```bash
# Create superuser
uv run python manage.py createsuperuser

# Create initial data (optional)
uv run python manage.py setup_groups
uv run python manage.py create_sample_tags
uv run python manage.py create_sample_content
```

### 8. Model Validation

**Verify models work correctly:**

- [ ] Run `uv run python manage.py check`
- [ ] Test model creation in Django shell
- [ ] Verify no broken relationships
- [ ] Test model admin interfaces

## Critical Considerations

### Fresh Start Approach

- This approach creates a completely fresh database schema
- No existing data is preserved (appropriate for greenfield projects)
- Much simpler than step-by-step migration approach
- Clean git history with simplified migrations

### Rollback Plan

- Original multi-hospital implementation remains in `prescriptions` branch
- To rollback: `git checkout prescriptions` and recreate database
- No complex data migration rollback needed

## Validation Checklist

Before proceeding to Phase 3:

- [ ] All hospital models removed
- [ ] No hospital field references in models
- [ ] Migrations completed successfully
- [ ] `uv run python manage.py check` passes
- [ ] Models can be created/queried without errors
- [ ] Admin interfaces load correctly

## Files Modified

Document all files changed in this phase:

- `apps/accounts/models.py` - Remove hospital fields and methods
- `apps/patients/models.py` - Remove hospital fields and PatientHospitalRecord model
- `apps/accounts/admin.py` - Remove hospital admin configurations
- `apps/patients/admin.py` - Remove hospital admin configurations
- **Deleted:** All existing migration files
- **Created:** Fresh initial migration files for all apps (except hospitals)

## Next Phase Preparation

Ensure these items are ready for Phase 3:

- [ ] All models are hospital-free
- [ ] Database is migrated
- [ ] No import errors from removed hospital models
