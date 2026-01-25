## Context

The prescription template create/update forms currently use manual text input fields for drug selection. Users must type drug names and all medication details manually. The outpatient prescription form, however, has a sophisticated drug selection UX with:
- Autocomplete search that queries DrugTemplate objects
- Dropdown suggestions with drug name, presentation, and creator info
- Auto-population of fields when a drug is selected
- Consistent styling and error handling

This creates UX inconsistency - users have different experiences when creating prescription templates vs creating actual prescriptions. Both forms look very similar but work differently.

## Goals / Non-Goals

- Goals:
  - Provide consistent drug selection UX across prescription templates and outpatient prescriptions
  - Enable autocomplete search for drug names in prescription templates
  - Auto-populate fields from DrugTemplate selections
  - Maintain existing functionality (manual entry, multi-drug forms)
- Non-Goals:
  - Track DrugTemplate references in PrescriptionTemplateItem (data is copied, not referenced)
  - Modify outpatient prescription behavior or templates
  - Create new static assets (reuse existing ones)

## Decisions

- Decision: Reuse existing `AutoCompleteWidget` and `DrugTemplateField` from `apps.outpatientprescriptions.widgets`
  - Rationale: These components are already tested and work correctly. Duplication would create maintenance burden.
- Decision: Reuse existing CSS/JS files from outpatientprescriptions app
  - Rationale: Styles and functionality are identical. Shared assets ensure consistency and reduce maintenance.
- Decision: Reuse existing AJAX endpoints from outpatientprescriptions app
  - Rationale: The search endpoints already work correctly and provide the same data needed. No need to duplicate.
- Decision: Keep data copying (not referencing) from DrugTemplate
  - Rationale: Prescription templates store independent data. Source templates are for reference during creation, not ongoing relationships.

## Alternatives Considered

- Create separate widgets and static files for prescription templates:
  - Rejected: Creates duplication and maintenance burden. UX is identical.
- Create new AJAX endpoints in drugtemplates app:
  - Rejected: Existing endpoints work perfectly. Duplication adds complexity.
- Track DrugTemplate references in PrescriptionTemplateItem:
  - Rejected: Out of scope for this change. Data independence is the current design.

## Risks / Trade-offs

- Container ID mismatch: `drug_template_integration.js` expects `#prescription-items-container` but prescription templates use `#formset-container`
  - Mitigation: Update container ID in prescription template files to `#prescription-items-container` to match shared JS expectations
- Formset prefix differences: Need to ensure `items` prefix works correctly with shared JS
  - Mitigation: Review and test formset prefix handling
- Static file loading: Need to ensure prescription templates can access outpatientprescriptions static files
  - Mitigation: Django's static file system handles this automatically

## Migration Plan

1. Update form class to use AutoCompleteWidget and DrugTemplateField
2. Update views to pass drug_templates to context
3. Update templates with new structure and static file references
4. Remove custom formset JavaScript
5. Test autocomplete, formset management, and validation
6. Run test suite to ensure no regressions

## Open Questions

- None
