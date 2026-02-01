# Slice 05 - Report model + context builder + report service

Goal:
Introduce report persistence and deterministic placeholder context building.

Scope boundaries:
- Included: Report model, context builder service, report creation service, tests.
- Excluded: UI views.

Files to create/modify:
- apps/reports/models.py
- apps/reports/services/context_builder.py
- apps/reports/services/report_service.py
- apps/reports/migrations/0002_report_model.py
- apps/reports/tests/test_context_builder.py
- apps/reports/tests/test_report_service.py
- apps/reports/tests/test_models_report.py

Tests to write FIRST (TDD):
- test_context_builder_includes_patient_doctor_document_hospital_fields
- test_report_save_sets_event_type
- test_report_service_renders_template_with_context
- test_report_service_raises_on_missing_required_placeholder
- test_report_template_delete_does_not_delete_report

Implementation steps:
1) Add Report model extending Event with content, document_date, optional title, optional template (SET_NULL).
2) Build context builder for patient/doctor/hospital/document fields.
3) Implement report service to render initial content and create report instance.

Refactor steps:
- Split context builder into small helpers (patient/doctor/hospital).

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_context_builder
- ./scripts/test.sh apps.reports.tests.test_report_service
- ./scripts/test.sh apps.reports.tests.test_models_report
