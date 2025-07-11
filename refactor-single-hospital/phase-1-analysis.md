# Phase 1: Analysis and Preparation

**Estimated Time:** 30-45 minutes  
**Complexity:** Low  
**Dependencies:** None

## Objectives

1. Analyze the current codebase to identify all hospital-related code
2. Create a comprehensive inventory of files to modify/remove
3. Set up safety measures and backups
4. Validate the scope before proceeding

## Tasks

### 1. Code Analysis

Use grep/search tools to find all hospital-related references:

```bash
# Search for hospital-related imports
grep -r "from apps.hospitals" apps/
grep -r "import.*hospital" apps/

# Search for hospital field references
grep -r "current_hospital" apps/
grep -r "hospitals\.all" apps/
grep -r "hospital_context" apps/

# Search for hospital-related URL patterns
grep -r "hospital" */urls.py

# Search for hospital-related template references
grep -r "hospital" apps/*/templates/
```

### 2. Create Inventory Lists

Document in this file:

#### Files to Remove Completely:
- [ ] `apps/hospitals/` (entire app)
- [ ] Hospital-related migrations in other apps
- [ ] Hospital-specific templates
- [ ] Hospital-related management commands

#### Models to Modify:
- [ ] `apps/accounts/models.py` - User model (remove hospitals M2M, last_hospital)
- [ ] `apps/patients/models.py` - Patient model (remove current_hospital)
- [ ] Remove `PatientHospitalRecord` model entirely

#### Permission System Files:
- [ ] `apps/core/permissions/utils.py` - Simplify drastically
- [ ] `apps/core/permissions/cache.py` - Remove hospital-aware caching
- [ ] `apps/core/permissions/decorators.py` - Remove hospital decorators

#### Settings and Configuration:
- [ ] `eqmd/settings.py` - Remove hospital middleware, apps
- [ ] `eqmd/urls.py` - Remove hospital URL includes
- [ ] Template context processors

#### Views and Forms:
- [ ] All forms with hospital fields
- [ ] Views with hospital context logic
- [ ] Admin configurations with hospital references

### 3. Database Impact Assessment

Review current database schema:
- Identify foreign key relationships to Hospital model
- Plan migration sequence to avoid FK constraint issues
- Document data that will be lost (hospital assignments, records)

### 4. Test Impact Assessment

Count tests that will need modification:
```bash
grep -r "hospital" apps/*/tests/
```

### 5. Safety Measures

- [ ] Ensure current branch is committed
- [ ] Document current git status
- [ ] Verify backup availability
- [ ] Create inventory of critical functionality to preserve

## Validation Checklist

Before proceeding to Phase 2:
- [ ] Complete inventory created
- [ ] All hospital references catalogued
- [ ] Database impact understood
- [ ] Safety measures in place
- [ ] Estimated effort for each subsequent phase documented

## Output for Next Phase

Create `hospital-inventory.md` with:
1. Complete list of files to modify/remove
2. Database schema changes required
3. Critical dependencies identified
4. Risk assessment for each change

## Notes

- This phase is pure analysis - no code changes
- Focus on comprehensive discovery to avoid surprises later
- Document any complex dependencies that might affect later phases
- Identify any hospital-related functionality that might be critical to preserve