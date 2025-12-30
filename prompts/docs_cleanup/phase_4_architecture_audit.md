# Phase 4: Architecture Documentation Audit

## Objective

Review and update architecture documentation that may contain outdated references or information post-migration.

## Files Requiring Audit

### High Priority Review

#### 1. `docs/MIGRATION.md` (252 lines)

**Concerns:**

- Documents "Single-Hospital Architecture Migration"
- References migration from multi-hospital to single-hospital
- May contain outdated migration steps
- Could confuse new developers about current architecture

**Review Questions:**

- Is this historical documentation or still-relevant guide?
- Are the migration steps current?
- Should this be moved to historical documentation?

#### 2. `docs/database-reset.md` (243 lines)

**Concerns:**

- References old management commands that may not exist
- Contains database reset procedures that might be outdated
- May reference multi-hospital concepts that are no longer relevant

**Review Questions:**

- Are all management commands still valid?
- Do database reset procedures work with current schema?
- Are there references to removed models/concepts?

#### 3. `docs/README_reset_script.md`

**Concerns:**

- Unknown content, needs investigation
- Could be outdated reset/setup script documentation

### Medium Priority Review

#### 4. `docs/image_processing_flow.md`

**Concerns:**

- May reference old image processing approaches
- Could conflict with current MediaFiles implementation
- Might document superseded workflows

## Audit Process

### Phase 4A: MIGRATION.md Audit

#### Investigation Steps

1. **Check Migration Relevance**

   ```bash
   # Review first 50 lines to understand scope
   head -50 docs/MIGRATION.md
   
   # Check for references to removed concepts
   grep -i "hospital" docs/MIGRATION.md
   grep -i "ward" docs/MIGRATION.md
   grep -i "PatientHospitalRecord" docs/MIGRATION.md
   ```

2. **Verify Command Validity**

   ```bash
   # Check if mentioned management commands exist
   grep "manage.py" docs/MIGRATION.md | grep -o "manage.py [^\"]*" | sort | uniq
   
   # Test key commands mentioned in the guide
   uv run python manage.py help | grep -f <(grep -o "manage.py [a-z_]*" docs/MIGRATION.md)
   ```

3. **Decision Matrix:**
   - **If Current**: Update any outdated references, keep as guide
   - **If Historical**: Move to historical documentation section
   - **If Partially Relevant**: Split into current guidance + historical context

#### Potential Actions

- **KEEP & UPDATE**: If migration guide is still relevant
- **ARCHIVE**: If purely historical post-migration
- **SPLIT**: If contains both current and historical information

### Phase 4B: database-reset.md Audit

#### Investigation Steps

1. **Validate Management Commands**

   ```bash
   # Extract all management commands mentioned
   grep -o "manage.py [a-z_]*" docs/database-reset.md
   
   # Check each command exists
   uv run python manage.py help | grep setup_groups
   uv run python manage.py help | grep create_sample_wards
   uv run python manage.py help | grep populate_sample_data
   ```

2. **Check Model References**

   ```bash
   # Look for references to removed models
   grep -i "hospital" docs/database-reset.md
   grep -i "ward" docs/database-reset.md
   grep -i "PatientHospitalRecord" docs/database-reset.md
   ```

3. **Test Reset Procedures**
   - Verify database reset steps work with current schema
   - Check that sample data commands are current
   - Ensure no references to removed concepts

#### Potential Actions

- **UPDATE**: Fix outdated commands and references
- **REWRITE**: If significantly outdated
- **DELETE**: If procedures are no longer recommended

### Phase 4C: Other Files Audit

#### README_reset_script.md

1. **Content Investigation**

   ```bash
   # Examine file content and purpose
   cat docs/README_reset_script.md
   
   # Check file size and last modified
   ls -la docs/README_reset_script.md
   ```

#### image_processing_flow.md

1. **Relevance Check**

   ```bash
   # Compare with current MediaFiles implementation
   grep -i "filepond" docs/image_processing_flow.md
   grep -i "video" docs/image_processing_flow.md
   
   # Check if conflicts with docs/apps/mediafiles.md
   ```

## Execution Steps

### 1. Create Audit Branch

```bash
git checkout -b docs-audit-phase4
```

### 2. Systematic File Review

#### For Each File

1. **Read Complete Content**
2. **Check Command Validity**
3. **Verify Model/Concept References**
4. **Test Procedures if Applicable**
5. **Document Findings**

### 3. Update Files Based on Findings

#### Example Update Actions

```bash
# For outdated management commands:
sed -i 's/manage.py create_sample_wards/manage.py create_sample_tags/g' docs/database-reset.md

# For removed model references:
sed -i '/PatientHospitalRecord/d' docs/MIGRATION.md
```

### 4. Document Audit Results

Create `docs/ARCHITECTURE_AUDIT_RESULTS.md`:

```markdown
# Architecture Documentation Audit Results

## Files Reviewed
- MIGRATION.md: [Status] - [Actions taken]
- database-reset.md: [Status] - [Actions taken]  
- README_reset_script.md: [Status] - [Actions taken]
- image_processing_flow.md: [Status] - [Actions taken]

## Issues Found
- [List of outdated references]
- [Invalid commands]
- [Conflicting information]

## Actions Taken
- [Updates made]
- [Files archived/deleted]
- [New documentation created]
```

### 5. Commit Changes

```bash
git add .
git commit -m "docs: Phase 4 audit - Update architecture documentation

Audit Results:
- MIGRATION.md: [describe action taken]
- database-reset.md: [describe action taken]
- README_reset_script.md: [describe action taken]
- image_processing_flow.md: [describe action taken]

Changes:
- Updated outdated management command references
- Removed references to deprecated models/concepts  
- Fixed conflicting information
- Added audit results documentation

Ensures all architecture docs reflect current system state."
```

## Decision Framework

### For Each Audited File

#### KEEP & UPDATE if

- Core information is still relevant
- Procedures/commands are mostly current
- File serves ongoing purpose
- Minor updates can fix issues

#### ARCHIVE/MOVE if

- Primarily historical value
- Documents completed migrations
- No longer relevant to current users
- Better placed in historical section

#### DELETE if

- Completely outdated
- Conflicts with current implementation
- No historical value
- Information available elsewhere

#### REWRITE if

- Core purpose is valid
- Content is significantly outdated
- Major restructuring needed
- Current approach is different

## Validation Steps

### Before Updates

- [ ] Complete content review of each file
- [ ] Test all referenced commands and procedures
- [ ] Identify conflicts with current documentation
- [ ] Document audit findings

### After Updates

- [ ] All management commands are valid
- [ ] No references to removed models/concepts
- [ ] Procedures work with current system
- [ ] No conflicting information with other docs
- [ ] Clear indication of what's current vs. historical

## Expected Impact

- **Accurate documentation** - All procedures and references current
- **Reduced confusion** - No outdated information misleading users
- **Better onboarding** - New developers get correct guidance
- **Maintenance clarity** - Clear distinction between current and historical docs

## Next Phase

Proceed to **Phase 5: Translation Files Cleanup** after successful completion and validation.
