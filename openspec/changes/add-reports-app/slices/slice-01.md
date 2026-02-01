# Slice 01 - App scaffold + placeholder renderer

Goal:
Provide placeholder validation/rendering service and register the reports app.

Scope boundaries:
- Included: app config, renderer service, unit tests, settings registration.
- Excluded: models, migrations, views, templates.

Files to create/modify:
- apps/reports/__init__.py
- apps/reports/apps.py
- apps/reports/services/renderer.py
- apps/reports/tests/test_renderer.py
- config/settings.py

Tests to write FIRST (TDD):
- test_validate_rejects_unknown_placeholder
- test_validate_requires_patient_name_and_record
- test_render_substitutes_values
- test_render_page_break_token
- test_render_missing_context_value_raises

Implementation steps:
1) Add reports app config and register in INSTALLED_APPS.
2) Implement placeholder regex, allowed set, required set, PAGE_BREAK_TOKEN.
3) Implement extract_placeholders, validate_template_placeholders, render_template.

Refactor steps:
- Extract helper for unknown/missing placeholder checks to keep functions small.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_renderer
