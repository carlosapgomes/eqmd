# Slice 06 - Report create UI (EasyMDE + template selection)

Goal:
User can create a report from a template, edit markdown, and save.

Scope boundaries:
- Included: create form/view/template; template selection and initial render.
- Excluded: update/delete/detail.

Files to create/modify:
- apps/reports/forms.py
- apps/reports/views/report_views.py
- apps/reports/urls.py
- apps/reports/templates/reports/report_create_form.html
- apps/reports/tests/test_report_create_view.py

Tests to write FIRST (TDD):
- test_report_create_requires_login
- test_report_create_filters_templates_public_or_own
- test_report_create_from_template_saves_report
- test_report_create_manual_content_without_template
- test_report_create_rejects_private_template_from_other_user

Implementation steps:
1) Implement ReportCreateForm with template, title, document_date, content.
2) Use report service to render initial content.
3) Add EasyMDE assets and initialization consistent with simplenotes/dailynotes.

Refactor steps:
- Ensure view only orchestrates; move logic to report service.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_report_create_view
