# Single Hospital Refactor Plan

This folder contains the detailed step-by-step plan for refactoring EquipeMed from a multi-hospital architecture to a single-hospital architecture.

## Overview

The refactor will completely remove the multi-hospital functionality to simplify the codebase by approximately 40-60%. This is a greenfield project decision to avoid unnecessary complexity.

## Execution Order

Execute the phases in this exact order, with each phase being a separate coding session:

1. **Phase 1: Analysis and Preparation** (`phase-1-analysis.md`)
   - Scope analysis and impact assessment
   - Backup creation and safety measures

2. **Phase 2: Database Models Refactor** (`phase-2-models.md`)
   - Remove hospital-related models and fields
   - Create database migrations

3. **Phase 3: Permission System Simplification** (`phase-3-permissions.md`)
   - Drastically simplify permission logic
   - Remove hospital context dependencies

4. **Phase 4: Views and Forms Cleanup** (`phase-4-views-forms.md`)
   - Remove hospital-related logic from views and forms
   - Simplify form validation

5. **Phase 5: Templates and Frontend** (`phase-5-templates.md`)
   - Remove hospital selection UI
   - Clean up templates

6. **Phase 6: Settings and Configuration** (`phase-6-settings.md`)
   - Remove hospital-related settings
   - Clean up middleware and URL patterns

7. **Phase 7: Testing Refactor** (`phase-7-testing.md`)
   - Remove hospital-related tests
   - Update remaining tests

8. **Phase 8: Documentation Update** (`phase-8-documentation.md`)
   - Update CLAUDE.md
   - Update project documentation
   - Update README and setup instructions

## Success Criteria

After completion:
- All tests pass
- No hospital-related code remains
- Permission system is simplified
- Documentation reflects single-hospital architecture
- Development server starts without errors

## Rollback Plan

The original multi-hospital implementation remains in the `prescriptions` branch. If multi-hospital functionality is needed later, switch back to that branch.