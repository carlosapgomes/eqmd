# Slice 08 - PDF generator + download view

Goal:
Provide PDF download with letterhead, page breaks, and signature section.

Scope boundaries:
- Included: report PDF generator, PDF view, detail template button.
- Excluded: other UI changes.

Files to create/modify:
- apps/reports/services/pdf_generator.py
- apps/reports/views/pdf_views.py
- apps/reports/urls.py
- apps/reports/templates/reports/report_detail.html
- apps/reports/tests/test_report_pdf_view.py

Tests to write FIRST (TDD):
- test_report_pdf_requires_access
- test_report_pdf_returns_pdf_content_type

Implementation steps:
1) Implement generator mirroring consentforms flow with PAGE_BREAK_TOKEN.
2) PDF view returns download with safe filename.
3) Add button in report detail template.

Refactor steps:
- Keep generator methods small and composable.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_report_pdf_view
