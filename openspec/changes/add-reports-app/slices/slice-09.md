# Slice 09 - Navigation/timeline integration

Goal:
Expose report creation and access in patient UI.

Scope boundaries:
- Included: add report create link in patient UI.
- Excluded: new listings.

Files to create/modify:
- templates or apps/patients/templates/... (locate via search)
- apps/patients/tests/test_patient_detail_links.py (if exists or create)

Tests to write FIRST (TDD):
- test_patient_detail_contains_report_create_link_for_authorized_user

Implementation steps:
1) Add link to report create view in patient action area.
2) Show link only to authenticated users.

Refactor steps:
- Keep template changes minimal.

Verification commands:
- ./scripts/test.sh apps.patients.tests.test_patient_detail_links
