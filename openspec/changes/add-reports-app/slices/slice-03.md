# Slice 03 - Template permission service

Goal:
Centralize who can manage report templates.

Scope boundaries:
- Included: permission service + tests.
- Excluded: views and forms.

Files to create/modify:
- apps/reports/services/permissions.py
- apps/reports/tests/test_template_permissions.py

Tests to write FIRST (TDD):
- test_admin_can_manage_templates
- test_doctor_can_manage_templates
- test_resident_can_manage_templates
- test_nurse_cannot_manage_templates
- test_unauthenticated_cannot_manage_templates

Implementation steps:
1) Implement can_manage_report_templates(user) using is_staff/is_superuser or is_doctor_or_resident.

Refactor steps:
- Keep function <= 25 lines; avoid extra branches.

Verification commands:
- ./scripts/test.sh apps.reports.tests.test_template_permissions
