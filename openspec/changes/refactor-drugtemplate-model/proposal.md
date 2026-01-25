## Why

The current DrugTemplate model combines concentration and pharmaceutical form into a single "presentation" field, making it unsuitable for importing structured medication data from MERGED_medications.csv (1,071 medications with separate concentration and form fields). The model also requires usage_instructions for imported reference drugs, which don't have prescription instructions.

## What Changes

- **Split presentation field** into separate `concentration` and `pharmaceutical_form` fields for better data structure
- **Make usage_instructions optional** for imported reference medications vs user-created templates
- **Add import tracking fields** (`is_imported`, `import_source`) to distinguish imported reference data from user templates
- **Create data import management command** to import CSV medications into the refactored model
- **Update forms, admin, and views** to handle the new field structure
- **Maintain backward compatibility** with existing presentation field as computed property

## Impact

- Affected specs: drugtemplates (medication template management)
- Affected code:
  - `apps/drugtemplates/models.py` - model refactoring
  - `apps/drugtemplates/admin.py` - admin interface updates
  - `apps/drugtemplates/forms.py` - form field changes
  - `apps/drugtemplates/views.py` - view updates for new fields
  - `apps/drugtemplates/management/commands/` - new import command
  - Templates in `templates/drugtemplates/` - display updates
  - Database migration for field changes

