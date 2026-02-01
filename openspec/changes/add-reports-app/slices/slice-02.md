# Slice 02 - ReportTemplate model + admin + validation

Goal:
Persist report templates with validation and audit/history.

Scope boundaries:
- Included: ReportTemplate model, migration, admin registration, model tests.
- Excluded: template UI views, report model.

Files to create/modify:
- apps/reports/models.py
- apps/reports/admin.py
- apps/reports/migrations/0001_initial.py
- apps/reports/tests/test_models_template.py

Tests to write FIRST (TDD):
- test_reporttemplate_valid_placeholders_saves
- test_reporttemplate_rejects_unknown_placeholder
- test_reporttemplate_requires_patient_placeholders
- test_reporttemplate_defaults_is_active_true
- test_reporttemplate_str_returns_name

Implementation steps:
1) Create ReportTemplate with UUID PK, name, markdown_body, is_active, is_public, created_by, updated_by, timestamps, history.
2) Validate placeholders in clean().
3) Call full_clean() in save().
4) Register in admin with search fields and list filters.

Refactor steps:
- Keep validation logic minimal and reuse renderer helpers.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_models_template
