# Slice 07 - Report detail/update/delete with 24h rules

Goal:
View, edit, and delete reports within the 24h window.

Scope boundaries:
- Included: detail, update, delete views and templates.
- Excluded: PDF.

Files to create/modify:
- apps/reports/views/report_views.py
- apps/reports/urls.py
- apps/reports/templates/reports/report_detail.html
- apps/reports/templates/reports/report_update_form.html
- apps/reports/templates/reports/report_confirm_delete.html
- apps/reports/tests/test_report_edit_delete_views.py

Tests to write FIRST (TDD):
- test_report_detail_shows_markdown
- test_report_update_allowed_within_24h_by_creator
- test_report_update_denied_after_24h
- test_report_delete_allowed_within_24h_by_creator
- test_report_delete_denied_for_non_creator

Implementation steps:
1) Implement detail/update/delete views with can_edit_event and can_delete_event.
2) Update form allows editing content/title/document_date only.
3) Templates show edit/delete buttons only when allowed.

Refactor steps:
- Extract permission checks if duplicated.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_report_edit_delete_views
