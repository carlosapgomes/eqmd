# Phase 9: Documentation Audit & Update

**Estimated Time:** 90-120 minutes  
**Complexity:** Medium-High  
**Dependencies:** Phase 8 completed

## Objectives

1. Conduct comprehensive audit of all documentation in `docs/` folder
2. Update hospital-related documentation for single-hospital architecture  
3. Verify documentation accuracy against current codebase
4. Remove obsolete documentation files
5. Update all Django commands to use `uv run`
6. Ensure documentation consistency and quality

## Tasks

### 1. Critical Documentation Updates (Hospital-Related)

**🚨 Files requiring major updates/removal:**

#### `docs/patients/hospital_records.md` - **REMOVE COMPLETELY**
- [ ] **Action:** Delete file entirely
- [ ] **Reason:** Documents PatientHospitalRecord model being removed
- [ ] **Content:** Completely obsolete with single-hospital architecture

#### `docs/patients/patient_management.md` - **MAJOR UPDATE**
- [ ] Remove hospital assignment sections
- [ ] Update patient status management (no hospital requirements)
- [ ] Simplify patient creation workflows
- [ ] Remove current_hospital field references

#### `docs/permissions/README.md` - **MAJOR REWRITE**
- [ ] Remove "Hospital Context Management" section
- [ ] Update to reflect simplified 2-tier permission model (Doctors/Residents vs Others)
- [ ] Remove hospital-related permission utilities documentation
- [ ] Update role-based permission descriptions

#### `docs/sample-data-population.md` - **SIGNIFICANT UPDATE**
- [ ] Remove hospital creation documentation
- [ ] Update to reflect environment-based hospital configuration
- [ ] Remove user-hospital assignment references
- [ ] Update sample data structure documentation

### 2. Command Updates (Use `uv run`)

**Update all Django commands in documentation:**
- [ ] `docs/TESTING.md`
- [ ] `docs/database-reset.md`
- [ ] `docs/sample-data-population.md`
- [ ] `docs/permissions/user-guide.md`
- [ ] Any other files with `python manage.py` commands

**Pattern to apply:**
```bash
# Before
python manage.py <command>

# After  
uv run python manage.py <command>
```

### 3. Documentation Accuracy Audit

**Cross-reference each doc file against current codebase:**

#### `docs/mediafiles/` folder - **VERIFY ACCURACY**
- [ ] Check if `database_schema.md` reflects current MediaFile models
- [ ] Verify `security_implementation.md` matches current security measures
- [ ] Validate `videoclip_current_state.md` against actual VideoClip implementation
- [ ] Check if migration plans match actual implemented state

#### `docs/permissions/` folder - **VERIFY & UPDATE**
- [ ] `api-reference.md` - Update permission function signatures
- [ ] `user-guide.md` - Update workflows to remove hospital context
- [ ] Verify decorator documentation matches actual implementations

#### `docs/patients/` folder - **VERIFY & UPDATE**
- [ ] `api.md` - Remove hospital-related API endpoints
- [ ] `deployment.md` - Update for single-hospital deployment
- [ ] `tags_management.md` - Verify against current tag system
- [ ] Check Portuguese translations are consistent

#### `docs/sample_content/` folder - **VERIFY ACCURACY**
- [ ] `README.md` - Check if sample content system matches docs
- [ ] `api.md` - Verify API endpoints are accurately documented

### 4. Testing Documentation Updates

#### `docs/TESTING.md` - **UPDATE**
- [ ] Remove hospital-related test scenarios
- [ ] Update permission testing guidelines
- [ ] Add new simplified permission test examples
- [ ] Update test command examples with `uv run`

#### `docs/testing-strategy.md` - **UPDATE**
- [ ] Remove hospital context testing strategies
- [ ] Update test data creation strategies (no hospitals)
- [ ] Simplify permission testing approaches

### 5. General Documentation Quality Audit

**For each documentation file:**
- [ ] Check for broken internal links
- [ ] Verify code examples actually work
- [ ] Ensure consistent formatting and style
- [ ] Update outdated references or screenshots
- [ ] Check if documented features actually exist in codebase

### 6. New Documentation Needs

**Consider adding:**
- [ ] `docs/hospital-configuration.md` - Document environment-based hospital setup
- [ ] `docs/single-hospital-benefits.md` - Explain simplified architecture benefits
- [ ] Update main documentation index/README

### 7. Portuguese Documentation

**Update Portuguese (.pt-BR) files:**
- [ ] `docs/patients/api.pt-BR.md`
- [ ] `docs/patients/deployment.pt-BR.md`  
- [ ] `docs/patients/hospital_records.pt-BR.md` - **DELETE**
- [ ] `docs/patients/index.pt-BR.md`
- [ ] `docs/patients/patient_management.pt-BR.md`
- [ ] `docs/patients/tags_management.pt-BR.md`

## Files to Review/Update

### High Priority (Hospital-Related)
- [ ] `docs/patients/hospital_records.md` - **DELETE**
- [ ] `docs/patients/hospital_records.pt-BR.md` - **DELETE**
- [ ] `docs/patients/patient_management.md` - **MAJOR UPDATE**
- [ ] `docs/patients/patient_management.pt-BR.md` - **MAJOR UPDATE**
- [ ] `docs/permissions/README.md` - **MAJOR REWRITE**
- [ ] `docs/permissions/user-guide.md` - **MAJOR UPDATE**
- [ ] `docs/sample-data-population.md` - **SIGNIFICANT UPDATE**

### Medium Priority (Command Updates + Accuracy Check)
- [ ] `docs/TESTING.md`
- [ ] `docs/database-reset.md`
- [ ] `docs/testing-strategy.md`
- [ ] `docs/permissions/api-reference.md`
- [ ] `docs/patients/api.md`
- [ ] `docs/patients/deployment.md`

### Lower Priority (Accuracy Verification)
- [ ] `docs/mediafiles/*.md` - Verify accuracy
- [ ] `docs/sample_content/*.md` - Verify accuracy
- [ ] `docs/styling.md` - Check if still relevant
- [ ] `docs/image_processing_flow.md` - Verify accuracy

## Validation Steps

### 1. Documentation Accuracy Test
```bash
# Test all documented commands actually work
uv run python manage.py check
uv run python manage.py help

# Verify documented features exist
uv run python manage.py shell
# Test documented API endpoints
```

### 2. Link and Reference Check
- [ ] Check all internal documentation links work
- [ ] Verify code examples are syntactically correct
- [ ] Test documented workflows end-to-end

### 3. Consistency Check
- [ ] All command examples use `uv run`
- [ ] Consistent terminology throughout docs
- [ ] Portuguese translations match English versions

### 4. User Experience Test
- [ ] Can a new developer follow the documentation?
- [ ] Are setup instructions complete and accurate?
- [ ] Do deployment docs work for single-hospital setup?

## Critical Documentation Changes

### Permission System Documentation

**Before (Complex Hospital + Role):**
```markdown
## Hospital Context Management
- Hospital context middleware manages user's current hospital
- Permissions check both role AND hospital membership
- Complex fallback logic for cross-hospital access
```

**After (Simple Role-Based):**
```markdown
## Role-Based Permissions  
- Simple 2-tier system: Doctors/Residents vs Others
- All roles can access all patients
- Permission differences: discharge rights, personal data editing
```

### Patient Management Documentation

**Before (Hospital Assignment Logic):**
```markdown
## Hospital Assignment
- Inpatients require current_hospital assignment
- Automatic hospital clearing on status change
- PatientHospitalRecord tracks history
```

**After (Simple Status Management):**
```markdown
## Patient Status Management
- Simple status tracking without hospital dependencies
- Environment-configured hospital branding
- Focus on patient care rather than location management
```

## Estimated Impact

### Documentation Reduction
- **~20% fewer files** (removing hospital-specific docs)
- **~40% simpler permission docs** (removing complex hospital logic)
- **~60% simpler patient management docs** (removing hospital assignments)

### Quality Improvements
- **Accurate documentation** matching actual codebase
- **Consistent command examples** using `uv run`
- **Simplified user experience** with clearer workflows

## Success Criteria

- [ ] No documentation references removed hospital functionality
- [ ] All documented commands work with `uv run`
- [ ] Documentation accurately reflects simplified architecture
- [ ] New users can follow docs to set up single-hospital system
- [ ] All internal documentation links work
- [ ] Portuguese translations are consistent and updated

## Next Steps

After Phase 9 completion:
1. **Validate entire refactor** works end-to-end
2. **Test complete user workflows** from setup to daily use
3. **Consider creating migration guide** for users familiar with old multi-hospital docs
4. **Update any external documentation** or README files