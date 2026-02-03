## Why

Nightly Firebase sync imports new patients and notes but leaves many patients stuck as inpatients because status changes and discharges are not reconciled. This causes inaccurate inpatient lists (often with empty bed/ward) and operational confusion, and will continue until status sync is handled.

## What Changes

- Update discharge report import to close any active admission and update patient status when a discharge report is imported.
- Sync Firebase patient status for existing patients (e.g., outpatient/deceased) and reconcile active admissions even when no discharge report exists.
- Add clear logging/summary for how many patients/admissions were reconciled in each run.

## Capabilities

### New Capabilities
- `firebase-patient-status-sync`: Reconcile patient status and active admissions from Firebase status changes and discharge report imports.

### Modified Capabilities

## Impact

- Management commands: `apps/dischargereports/management/commands/import_firebase_discharge_reports.py`, `apps/core/management/commands/sync_firebase_data.py`.
- Patient/admission reconciliation logic in `apps/patients/models.py` (usage of existing APIs).
- Tests for Firebase sync and discharge import behaviors.
