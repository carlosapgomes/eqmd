# Proposal: isolate-sample-specialty-seed-from-tests

## Why

The full test suite carries 74 pre-existing errors — all one family:
`IntegrityError` on `accounts_medicalspecialty_name_key` (41) or
`accounts_medicalspecialty_abbreviation_key` (33) across
accounts/patients/events/core tests. Root cause (verified
empirically): the data migration
`apps/accounts/migrations/0005_populate_sample_specialties.py`
seeds ~30 sample specialties into EVERY new database — including
test databases — and a generation of tests creates
`MedicalSpecialty` rows with the same names/abbreviations verbatim
("Cardiologia", "CARDIO", …). The collisions are order-independent
(each failing module fails in isolation). The CI "Full test suite
(blocking)" job is red because of this, and every slice loop must
diff against a 74-error baseline.

## What Changes

- Gate the 0005 seed behind a settings flag
  `EQMD_SEED_SAMPLE_SPECIALTIES` (default `True` — fresh dev/demo
  installs keep their bootstrap data; already-migrated databases are
  untouched by definition).
- `config/test_settings.py` sets the flag to `False`, so test
  databases are built without sample data.
- Add a canary test that fails if the seed ever leaks back into test
  databases.
- Expected result: full suite goes from 74 errors to 0 with no new
  failures; the CI full-suite job turns green.

## Non-goals

- Fixing the ~10 failing test modules by editing them (no churn:
  no test depends on the seed — audit verified `get/filter` usages
  reference self-created rows and the passing modules use
  `get_or_create`).
- Removing the seed from real environments or writing a new
  migration (0005 stays applied wherever it ran).
- The remaining 302-lifecycle debt tracked by
  `stabilize-test-suite-lifecycle-gates` (separate concern; the
  current suite shows 0 failures — only these 74 errors).
