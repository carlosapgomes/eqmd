# Phase 3: App Documentation Deduplication

## Objective

Eliminate redundant app documentation and establish clear hierarchy between comprehensive guides and legacy docs.

## Current State Analysis

### Duplicate Documentation Issue

We now have **two sets** of app documentation:

1. **Legacy Detailed Docs** - In original locations (e.g., `docs/mediafiles/index.md`)
2. **New Comprehensive Guides** - In `docs/apps/` (e.g., `docs/apps/mediafiles.md`)

### Specific Conflicts

#### MediaFiles Documentation

- **`docs/mediafiles/index.md`** (553 lines) - **REPLACE/REDIRECT**
  - Detailed app documentation with architecture details
  - Pre-FilePond migration content (partially outdated)
  - Overlaps significantly with `docs/apps/mediafiles.md`

- **`docs/apps/mediafiles.md`** - **KEEP** - Primary comprehensive guide
  - Current post-FilePond migration state
  - Complete implementation details
  - Up-to-date architecture

#### Patients Documentation  

- **`docs/patients/`** directory - **REVIEW** - Multiple files
  - `patient_management.md` (130 lines)
  - `api.md`, `deployment.md`, etc.
  - Some content may overlap with `docs/apps/patients.md`

## Files to REPLACE/REDIRECT

### 1. `docs/mediafiles/index.md` → Redirect to `docs/apps/mediafiles.md`

**Current Status:**

- 553 lines of detailed documentation
- Contains outdated pre-FilePond migration information
- Overlaps 80% with `docs/apps/mediafiles.md`
- Still contains valuable specific technical details

**Action Plan:**

- Replace with redirect/summary pointing to `docs/apps/mediafiles.md`
- Extract any unique technical details not in new guide
- Keep as lightweight index for `docs/mediafiles/` directory

## Files to REVIEW for Overlap

### 1. `docs/patients/` Directory

Compare with `docs/apps/patients.md`:

#### Potentially Redundant Files

- **`patient_management.md`** (130 lines) - User guide format
- **`patient_management.pt-BR.md`** - Portuguese translation
- **`index.md`** (17 lines) - Simple index

#### Potentially Unique Files

- **`api.md`** / **`api.pt-BR.md`** - API documentation
- **`deployment.md`** / **`deployment.pt-BR.md`** - Deployment guides
- **`tags_management.md`** / **`tags_management.pt-BR.md`** - Specific tag workflows

## Execution Steps

### 1. Create Archive Branch

```bash
git checkout -b docs-cleanup-archive-phase3
git add docs/mediafiles/index.md docs/patients/
git commit -m "Archive: App documentation before deduplication"
git push origin docs-cleanup-archive-phase3
```

### 2. Analyze MediaFiles Index Content

```bash
# Compare docs/mediafiles/index.md with docs/apps/mediafiles.md
# Identify unique technical details to preserve
```

#### Content Analysis

- **Architecture sections** - Check if covered in new guide
- **Code examples** - Preserve unique examples
- **Configuration details** - Ensure not lost
- **Troubleshooting** - Important to preserve

### 3. Replace MediaFiles Index

Create lightweight redirect version:

```markdown
# MediaFiles App Documentation

**📖 For comprehensive MediaFiles documentation, see: [docs/apps/mediafiles.md](../apps/mediafiles.md)**

## Quick Links

- **[Complete Implementation Guide](../apps/mediafiles.md)** - Full MediaFiles documentation
- **[Database Schema](database_schema.md)** - Technical database details  
- **[File Storage Structure](file_storage_structure.md)** - File organization
- **[Security Implementation](security_implementation.md)** - Security measures

## Technical Reference Files

This directory contains technical reference documentation:
- Database schemas and storage structures
- Security implementation details  
- Migration documentation (historical)

For usage guides, API reference, and comprehensive implementation details, see the main MediaFiles guide at `docs/apps/mediafiles.md`.
```

### 4. Analyze Patients Directory

```bash
# Compare each file in docs/patients/ with docs/apps/patients.md
# Determine redundancy vs. unique value

# Check file sizes and content focus:
diff docs/patients/patient_management.md docs/apps/patients.md | head -20
```

### 5. Handle Patients Documentation

#### If Significant Overlap

- Replace `docs/patients/patient_management.md` with redirect
- Keep `docs/patients/index.md` as directory index
- Preserve unique content (API, deployment guides)

#### If Unique Content

- Keep as complementary documentation
- Update cross-references between files
- Ensure no conflicting information

### 6. Update Navigation

```bash
# Update docs/README.md to reflect new structure
# Update CLAUDE.md references if needed
# Fix any broken cross-references
```

### 7. Commit Changes

```bash
git add .
git commit -m "docs: Phase 3 cleanup - Deduplicate app documentation

MediaFiles:
- Replace docs/mediafiles/index.md with redirect to apps/mediafiles.md
- Preserve unique technical content
- Maintain technical reference files

Patients: 
- [Describe specific changes made]
- [Preserve/redirect decisions]

Updated navigation and cross-references.
Original files archived in docs-cleanup-archive-phase3 branch."
```

## Decision Matrix for File Actions

### REPLACE with Redirect

- **High overlap** (>80%) with new comprehensive guide
- **Outdated information** that could confuse users
- **User guide format** better handled in apps/ directory

### KEEP as Complementary

- **Unique technical details** not in comprehensive guide
- **Specialized workflows** (API, deployment)
- **Reference materials** (schemas, configurations)

### REVIEW Further

- **Medium overlap** (40-80%) - need detailed comparison
- **Translation files** - check maintenance status
- **Uncertain value** - compare with user needs

## Validation Steps

### Before Changes

- [ ] Map all unique content in files to be replaced
- [ ] Verify comprehensive guides cover essential use cases
- [ ] Check external references to files being changed

### After Changes

- [ ] All essential information accessible through new structure
- [ ] No broken links in documentation
- [ ] Clear navigation hierarchy
- [ ] Users can find information efficiently

## Expected Impact

- **Clear documentation hierarchy** - Primary guides vs. technical reference
- **Reduced redundancy** - Single source of truth for each topic
- **Better user experience** - Less confusion about which doc to use
- **Easier maintenance** - Fewer files to keep synchronized

## Next Phase

Proceed to **Phase 4: Architecture Documentation Audit** after successful completion and validation.
