# Slice 10 - Move report link to timeline dropdown

Goal:
Remove the "Relatório" button from patient detail and enable it in the "Criar evento" dropdown on the patient timeline.

Scope boundaries:
- Included: remove detail-page report button; enable timeline dropdown link.
- Excluded: new views, models, or permissions changes.

Files to create/modify:
- apps/patients/templates/... (patient detail template)
- apps/patients/templates/... (patient timeline template with "Criar evento" dropdown)
- apps/patients/tests/test_patient_detail_links.py (update or add)
- apps/patients/tests/test_patient_timeline_links.py (create if needed)

Tests to write FIRST (TDD):
- test_patient_detail_does_not_show_report_button
- test_patient_timeline_dropdown_includes_report_link

Implementation steps:
1) Locate patient detail template and remove the report button/link.
2) Locate patient timeline template and replace the "Em breve" report item with the actual report create URL.
3) Ensure the link is shown for authenticated users and matches existing event links pattern.

Refactor steps:
- Keep template changes minimal and consistent with surrounding markup.

Verification commands:
- ./scripts/test.sh apps.patients.tests.test_patient_detail_links
- ./scripts/test.sh apps.patients.tests.test_patient_timeline_links
