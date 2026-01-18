## Why

ICD-10 (CID) codes are needed for searching and selecting diagnoses similarly to medical procedures.

## What Changes

- Add ICD-10 code model mirroring MedicalProcedure (code, description, active flag, search vector)
- Add API endpoints for ICD-10 search, detail, and list under /api/icd10/...
- Add import command for fixtures/cid.csv with update/deactivate options
- Add admin UI and comprehensive tests

## Impact

- Affected specs: icd10-codes (new capability)
- Affected code: apps/core/models, apps/core/api, apps/core/management/commands, apps/core/admin.py, apps/core/urls.py, tests
