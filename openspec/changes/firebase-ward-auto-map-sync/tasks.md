## 1. Prepare Ward Mapping Input

- [ ] 1.1 Add `fixtures/firebase-ward-map.json` with Firebase ward key -> EQMD ward id mappings.
- [ ] 1.2 Encode approved policy in mapping data:
- [ ] `Intermediário` -> `Intermediário B`
- [ ] `Hosp. Dia` -> `null`
- [ ] `Anexo` -> `null`
- [ ] 1.3 Verify all known Firebase ward keys from `fixtures/sisphgrs-wards-export.json` are represented in the map.

## 2. Implement Ward Resolver in Sync Command

- [ ] 2.1 Update `apps/core/management/commands/sync_firebase_data.py` to load and validate the ward map.
- [ ] 2.2 Add helper methods to extract Firebase ward reference, resolve mapped ward, and classify outcomes (`mapped`, `mapped_to_none`, `unresolved`).
- [ ] 2.3 Add counters/logging for ward mapping outcomes in command summary.

## 3. Apply Mapping in Patient Sync Flows

- [ ] 3.1 Use resolved ward for new patient admission creation paths (imported inpatient/emergency).
- [ ] 3.2 Use resolved ward for reconciliation paths that create a new active admission.
- [ ] 3.3 Update existing active admission and patient denormalized ward when mapped ward differs.
- [ ] 3.4 Preserve existing ward-clearing behavior for outpatient/deceased reconciliation.

## 4. Tests and Verification

- [ ] 4.1 Extend `apps/core/tests/test_firebase_sync_reconciliation.py` with mapping tests:
- [ ] mapped ward assignment on new import
- [ ] `Intermediário` -> `Intermediário B`
- [ ] `Hosp. Dia` / `Anexo` -> `None` (mapped-to-none)
- [ ] unresolved ward handling without sync failure
- [ ] active admission ward update when mapped ward changes
- [ ] 4.2 Run verification with `./scripts/test.sh apps.core.tests.test_firebase_sync_reconciliation`.

## 5. Documentation

- [ ] 5.1 Update `docs/firebase-import.md` to document ward mapping behavior, retired ward handling, and operational monitoring counters.
