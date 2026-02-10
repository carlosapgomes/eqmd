## Context

`apps/core/management/commands/sync_firebase_data.py` currently creates and reconciles admissions with `ward=None`. This loses important location data during ongoing daily sync and creates divergence between legacy ward references and the current EQMD ward model.

We already have:
- A Firebase ward export fixture at `fixtures/sisphgrs-wards-export.json`
- Current EQMD wards exported at `fixtures/wards-current.json`
- Approved mapping policy for ambiguous/retired wards:
- `Intermediário` -> `Intermediário B`
- `Hosp. Dia` -> `None`
- `Anexo` -> `None`

## Goals / Non-Goals

**Goals:**
- Resolve Firebase ward references into EQMD `Ward` during nightly patient sync.
- Apply mapping consistently for:
- New admitted/emergency patient imports
- Reconciliation flows that create admissions
- Reconciliation flows where an active admission already exists and ward changes
- Keep behavior safe and idempotent with explicit logging for unresolved cases.

**Non-Goals:**
- Creating new `Ward` records from Firebase automatically.
- Changing ward model/schema.
- Backfilling historical ward transitions outside current sync behavior.

## Decisions

- **Use a static JSON translation map committed in the repo (`fixtures/firebase-ward-map.json`).**
  - Rationale: deterministic behavior, easy review, and no runtime dependency on extra Firebase structures.
  - Alternative: dynamic fuzzy matching by ward name at runtime. Rejected due to ambiguity and operational risk.

- **Mapping values allow `null` to represent explicitly retired legacy wards.**
  - Rationale: distinguishes "known retired" from "unknown/unmapped" and supports intentional `ward=None` outcomes.

- **Ward resolution will be isolated in helper methods inside the command.**
  - Rationale: centralizes parsing, map lookup, counters, and warnings; avoids duplicated logic across create/reconcile paths.

- **When patient is currently admitted and Firebase ward resolves to a different ward, update both active admission and patient denormalized `ward`.**
  - Rationale: keeps `PatientAdmission.ward` and `Patient.ward` coherent.

- **Outpatient/deceased reconciliation continues to clear ward as today.**
  - Rationale: preserves existing status-to-location behavior.

## Risks / Trade-offs

- **[Risk] Firebase patient payload ward field shape may vary (key vs name).**
  - Mitigation: implement resolver tolerant to known field variants and emit clear unresolved logs.

- **[Risk] Map drift when ward inventory changes in EQMD.**
  - Mitigation: keep map file versioned and update as part of release workflow when wards change.

- **[Risk] Silent data quality issues if unknown Firebase ward appears.**
  - Mitigation: increment unresolved counters and log Firebase ward reference for monitoring.

## Migration Plan

- Add `fixtures/firebase-ward-map.json` with approved mappings.
- Deploy command changes.
- Run next daily sync (dry-run first in production workflow if desired).
- Monitor summary logs for unresolved/mapped-to-none counts.

No schema migration is required.

## Open Questions

- Which exact Firebase patient field carries ward reference in production payload (`ward`, `ptWard`, etc.)?  
  Implementation should support configured/known variants and log raw value for unresolved entries.
