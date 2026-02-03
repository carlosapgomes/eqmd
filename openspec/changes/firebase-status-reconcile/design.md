## Context

The nightly Firebase sync imports new patients and dailynotes but does not reconcile status changes for existing patients. As a result, many patients remain INPATIENT with empty bed/ward even after Firebase marks them OUTPATIENT or DECEASED. Discharge report import exists, but it only creates historical DischargeReport and inactive PatientAdmission rows without closing any active admission or updating patient status.

The system already has patient admission/discharge APIs in `Patient` and an `is_active` admission constraint that should be preserved. We need to update management commands to reconcile admissions and patient status safely and idempotently.

## Goals / Non-Goals

**Goals:**
- When importing a discharge report, close any active admission for the patient and update patient status consistently.
- When syncing Firebase patient records, apply status changes for existing patients (e.g., outpatient/deceased) even without a discharge report, and close active admissions accordingly.
- Keep behavior idempotent (re-running syncs should not create duplicate closures).
- Provide clear summaries/logging for reconciliation actions.

**Non-Goals:**
- Rebuilding bed/ward history from Firebase beyond what is available.
- Creating new data models or changing database schema.
- Backfilling or editing clinical content beyond discharge status and admission closure.

## Decisions

- **Use existing `Patient.discharge_patient(...)` API to close active admissions and update denormalized fields.**
  - Rationale: Centralizes status updates, duration calculation, and audit fields.
  - Alternative: Manually update `PatientAdmission` and `Patient` fields in the command. Rejected because it risks divergence from model rules.

- **On discharge report import, close the active admission using the discharge date from the report.**
  - Rationale: Matches the report’s authoritative timeline and avoids leaving the patient active.
  - Alternative: Only create historical admissions. Rejected because it leaves incorrect inpatient status.

- **During Firebase patient sync, reconcile existing patients’ status when Firebase indicates OUTPATIENT or DECEASED.**
  - Rationale: Some discharges have no discharge report; Firebase status is the only source.
  - Alternative: Ignore status changes. Rejected because it perpetuates incorrect inpatient list.

- **If Firebase status is inpatient/emergency for an existing patient and there is no active admission, create one using the lastAdmissionDate (when provided).**
  - Rationale: Keeps active admission invariant aligned with status.
  - Alternative: Set status without admission. Rejected due to system expectations and constraints.

## Risks / Trade-offs

- **[Risk] Firebase status could be stale or incorrect.**
  → Mitigation: Only reconcile when status differs and log changes; keep behavior idempotent and auditable.

- **[Risk] Missing or invalid admission/discharge dates from Firebase.**
  → Mitigation: If dates are unavailable, fall back to `timezone.now()` for discharge and admission close operations, and log a warning.

- **[Risk] Multiple historical admissions exist; choosing which to close could be ambiguous.**
  → Mitigation: Always close the current active admission (if any). Do not edit historical admissions.

## Migration Plan

- Deploy code changes.
- Run nightly sync as usual; status reconciliation will start applying immediately.
- Optional: run discharge import to backfill reports; active admissions will be closed during import.
- Rollback: revert code changes; no schema changes required.

## Open Questions

- Should we map Firebase “deceased” to `Patient.Status.DECEASED` and `DischargeType.DEATH` when closing admissions? yes
- Should we treat Firebase “outpatient” as `DischargeType.MEDICAL` by default, or leave discharge_type blank when closing admissions via status sync? treat Firebase “outpatient” as `DischargeType.MEDICAL` by default
