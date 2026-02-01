# Slice 04 - Template CRUD UI (list/create/update)

Goal:
Authorized users can list, create, and update templates with correct visibility.

Scope boundaries:
- Included: list, create, update views; forms; templates; URL routing.
- Excluded: delete action; report model.

Files to create/modify:
- apps/reports/forms.py
- apps/reports/views/template_views.py
- apps/reports/urls.py
- apps/reports/templates/reports/reporttemplate_list.html
- apps/reports/templates/reports/reporttemplate_form.html
- config/urls.py
- apps/reports/tests/test_template_views.py

Tests to write FIRST (TDD):
- test_template_list_requires_permission
- test_template_list_shows_public_and_own
- test_template_create_sets_creator_fields
- test_template_update_allowed_for_creator_or_admin
- test_template_update_forbidden_for_non_creator

Implementation steps:
1) Create ReportTemplateForm with markdown_body field.
2) Implement list/create/update views with permission checks using can_manage_report_templates.
3) Filter list queryset to is_public or creator.
4) Add urls and include in config.

Refactor steps:
- Move decision logic to a service (TemplateService) if view grows.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_template_views
