# Single Hospital Refactor - Phase Execution Prompts

This file contains the standardized prompts for executing each phase of the single-hospital refactor. Use these prompts with a fresh context window for each phase.

## 📋 Phase-by-Phase Execution Prompts

### Phase 1: Analysis and Preparation _(Starting Prompt)_

```
REFACTOR CONTEXT: I'm starting a single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/README.md for overview, then read @refactor-single-hospital/refactor-progress.md for current status, then execute Phase 1 according to @refactor-single-hospital/phase-1-analysis.md.

OBJECTIVE: Complete Phase 1 analysis, update progress file with findings, create hospital-inventory.md as specified.

CRITICAL: Use search tools extensively to find all hospital references. This sets the foundation for all subsequent phases.
```

### Phase 2: Database Models Refactor

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 2 according to @refactor-single-hospital/phase-2-models.md.

OBJECTIVE: Remove hospital models/fields, create fresh migrations, update progress file with all changes made.

CRITICAL: This is greenfield - delete existing migrations and create fresh ones. Use `uv run` for all Django commands.
```

### Phase 3: Permission System Simplification

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 3 according to @refactor-single-hospital/phase-3-permissions.md.

OBJECTIVE: Drastically simplify permission system from ~756 lines to ~200 lines, implement 2-tier model, update progress file.

CRITICAL: New permission rules - Doctors/Residents: full access + discharge + personal data. Others: full access but no discharge/personal data.
```

### Phase 4: Views and Forms Cleanup

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 4 according to @refactor-single-hospital/phase-4-views-forms.md.

OBJECTIVE: Remove hospital logic from views/forms, simplify patient forms, update URLs, update progress file.

CRITICAL: Remove all PatientHospitalRecord references and hospital field requirements from forms.
```

### Phase 5: Templates and Frontend

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 5 according to @refactor-single-hospital/phase-5-templates.md.

OBJECTIVE: Remove hospital selection UI, add hospital config template tags, update templates for env-based hospital info, update progress file.

CRITICAL: Implement hospital configuration template tags for environment-based hospital branding.
```

### Phase 6: Settings and Configuration

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 6 according to @refactor-single-hospital/phase-6-settings.md.

OBJECTIVE: Remove hospital app from settings, update management commands, add hospital env config, update progress file.

CRITICAL: Update setup_groups.py and populate_sample_data.py. Delete assign_users_to_hospitals.py. Add HOSPITAL_CONFIG settings.
```

### Phase 7: Testing Refactor

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 7 according to @refactor-single-hospital/phase-7-testing.md.

OBJECTIVE: Remove hospital-related tests, update permission tests for simplified model, update factories, update progress file.

CRITICAL: Update tests to reflect all roles can access all patients, with different editing/discharge permissions.
```

### Phase 8: Documentation Update

```
REFACTOR CONTEXT: I'm continuing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute Phase 8 according to @refactor-single-hospital/phase-8-documentation.md.

OBJECTIVE: Major rewrite of CLAUDE.md, update README/setup docs, document simplified architecture, update progress file.

CRITICAL: Use `uv run` for all command examples. Focus on simplified architecture benefits and env-based hospital config.
```

### Phase 9: Documentation Audit & Update _(Final Phase)_

```
REFACTOR CONTEXT: I'm completing the single-hospital refactor for EquipeMed Django project. Please read @refactor-single-hospital/refactor-progress.md to understand what has been completed so far, then execute final Phase 9 according to @refactor-single-hospital/phase-9-documentation-audit.md.

OBJECTIVE: Comprehensive docs/ folder audit, remove obsolete hospital docs, verify accuracy, final progress file update.

CRITICAL: Delete hospital_records.md files, major rewrite of permission docs, ensure all commands use `uv run`. This is the final phase.
```

## 🔑 Execution Instructions

### Before Each Phase

1. **Clear your context window completely**
2. **Copy the exact prompt** for the current phase
3. **Paste and execute** - Claude will read the necessary files for context
4. **Verify completion** before moving to the next phase

### Key Pattern Elements

- **Context primer** - explains refactor continuation/start
- **Progress file reference** - provides current state awareness
- **Phase-specific plan** - detailed instructions for current phase
- **Clear objective** - what to accomplish + update progress file
- **Critical reminders** - key implementation details for the phase

### Success Criteria

- Each phase updates the progress file with what was accomplished
- All validation steps are completed before proceeding
- Any issues encountered are documented in the progress file
- The refactor maintains momentum through clear context handoffs

## 📝 Notes

- These prompts are designed to work with the progress tracking system
- Each phase builds on the previous phase's documented changes
- The progress file serves as the "memory" between context windows
- Always verify phase completion before proceeding to the next phase
