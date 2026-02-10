## Why

The daily Firebase sync currently imports/reconciles patients without assigning wards, which leaves admitted patients with missing location (`ward=None`) in EQMD. We need deterministic ward translation from legacy Firebase wards to current EQMD wards to keep admissions operationally accurate.

## What Changes

- Add ward auto-mapping during patient sync in `sync_firebase_data` for both new imports and reconciliation paths that create/update active admissions.
- Load a ward translation table from a JSON map derived from Firebase ward exports and current EQMD wards.
- Apply approved business mapping rules:
- `Intermediário` in Firebase maps to `Intermediário B` in EQMD.
- `Hosp. Dia` and `Anexo` map to `None` because these wards no longer exist.
- Add summary counters/logging for mapped, mapped-to-none (retired), unresolved, and updated ward assignments.
- Add tests for mapping behavior and ward reconciliation updates.

## Capabilities

### New Capabilities
- `firebase-ward-auto-map`: Translate Firebase ward references to EQMD `Ward` records during nightly sync.

### Modified Capabilities

## Impact

- Management command: `apps/core/management/commands/sync_firebase_data.py`
- Sync tests: `apps/core/tests/test_firebase_sync_reconciliation.py`
- Fixture/input mapping data: `fixtures/firebase-ward-map.json`
- Sync documentation: `docs/firebase-import.md`
