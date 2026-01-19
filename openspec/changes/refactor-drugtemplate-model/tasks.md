## 1. Model Refactoring

- [ ] 1.1 Add new model fields (`concentration`, `pharmaceutical_form`, `is_imported`, `import_source`)
- [ ] 1.2 Update model validation to make `usage_instructions` optional for imported drugs
- [ ] 1.3 Add computed `presentation` property for backward compatibility
- [ ] 1.4 Create database migration for field changes
- [ ] 1.5 Update model indexes for new fields

## 2. Admin Interface Updates

- [ ] 2.1 Update DrugTemplateAdmin to display new fields
- [ ] 2.2 Add filters for `is_imported` and `pharmaceutical_form`
- [ ] 2.3 Update search fields to include new concentration and form fields
- [ ] 2.4 Add import source display in admin list

## 3. Forms and Views

- [ ] 3.1 Update DrugTemplateForm to handle separate concentration and form fields
- [ ] 3.2 Update form validation logic for user vs imported drugs
- [ ] 3.3 Update views to handle new field structure
- [ ] 3.4 Update templates to display new fields appropriately

## 4. Data Import System

- [ ] 4.1 Create management command `import_medications_csv`
- [ ] 4.2 Implement CSV parsing logic with duplicate detection
- [ ] 4.3 Add proper error handling and logging for import process
- [ ] 4.4 Create system user for imported drug ownership
- [ ] 4.5 Add import validation and statistics reporting

## 5. Data Migration

- [ ] 5.1 Create data migration to split existing presentation fields where possible
- [ ] 5.2 Mark all existing records as user-created (not imported)
- [ ] 5.3 Test migration with existing development data

## 6. Testing

- [ ] 6.1 Write tests for new model fields and validation
- [ ] 6.2 Write tests for import management command
- [ ] 6.3 Write tests for updated forms and views
- [ ] 6.4 Test admin interface with new fields
- [ ] 6.5 Test backward compatibility with existing templates

## 7. Documentation

- [ ] 7.1 Update CLAUDE.md with import command usage
- [ ] 7.2 Document new model structure and fields
- [ ] 7.3 Add usage examples for drug import process