## 1. Prepare Ward Mapping Input

- [x] 1.1 Add `fixtures/firebase-ward-map.json` with Firebase ward key -> EQMD ward id mappings.
- [x] 1.2 Encode approved policy in mapping data:
- [x] `Intermediário` -> `Intermediário B`
- [x] `Hosp. Dia` -> `null`
- [x] `Anexo` -> `null`
- [x] 1.3 Verify all known Firebase ward keys from `fixtures/sisphgrs-wards-export.json` are represented in the map.

## 2. Implement Ward Resolver in Sync Command

- [x] 2.1 Update `apps/core/management/commands/sync_firebase_data.py` to load and validate the ward map.
- [x] 2.2 Add helper methods to extract Firebase ward reference, resolve mapped ward, and classify outcomes (`mapped`, `mapped_to_none`, `unresolved`).
- [x] 2.3 Add counters/logging for ward mapping outcomes in command summary.

## 3. Apply Mapping in Patient Sync Flows

- [x] 3.1 Use resolved ward for new patient admission creation paths (imported inpatient/emergency).
- [x] 3.2 Use resolved ward for reconciliation paths that create a new active admission.
- [x] 3.3 Update existing active admission and patient denormalized ward when mapped ward differs.
- [x] 3.4 Preserve existing ward-clearing behavior for outpatient/deceased reconciliation.

## 4. Tests and Verification

- [x] 4.1 Extend `apps/core/tests/test_firebase_sync_reconciliation.py` with mapping tests:
- [x] mapped ward assignment on new import
- [x] `Intermediário` -> `Intermediário B`
- [x] `Hosp. Dia` / `Anexo` -> `None` (mapped-to-none)
- [x] unresolved ward handling without sync failure
- [x] active admission ward update when mapped ward changes
- [x] 4.2 Run verification with `./scripts/test.sh apps.core.tests.test_firebase_sync_reconciliation`.

## 5. Documentation

- [x] 5.1 Update `docs/firebase-import.md` to document ward mapping behavior, retired ward handling, and operational monitoring counters.
