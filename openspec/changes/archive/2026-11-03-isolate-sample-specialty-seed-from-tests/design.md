# Design: isolate-sample-specialty-seed-from-tests

## Context

Migration 0005 (`RunPython(create_sample_specialties)`, no reverse)
inserts ~30 `MedicalSpecialty` rows. Test DBs are created by running
migrations, so the rows exist in every test run. Failing tests then
insert colliding rows. Taxonomy at `main@f962e22`: 41 name-key +
33 abbreviation-key = the entire 74-error baseline; reproduced in
isolation for `test_team_membership`, `test_tag_catalogue_governance`
and `test_cache_tag_privacy`.

## Decision D1 — Settings-gated seed, default on

`create_sample_specialties` returns early unless
`getattr(settings, "EQMD_SEED_SAMPLE_SPECIALTIES", True)`. Default
`True` preserves the migration's bootstrap intent for fresh
non-test installs; databases that already applied 0005 are
untouched (recorded migrations do not re-run). No new migration is
introduced and the historical 0005 is not edited in place except
for the guard clause and the removal of its unused `uuid` import.

## Decision D2 — Test settings opt out

`config/test_settings.py` sets `EQMD_SEED_SAMPLE_SPECIALTIES =
False`. This covers the project-supported test entry points that
select that module: `scripts/test.sh` (defaults
`DJANGO_SETTINGS_MODULE=config.test_settings`), `pytest.ini`, the
CI full-suite job and the controller's throwaway-container evidence
runner. A bare `python manage.py test` without
`DJANGO_SETTINGS_MODULE` keeps base settings and therefore keeps
seeding — out of scope.

## Decision D3 — Canary against regression

A small test module asserts, at test time, that NO seeded sample
row exists in the test database — it checks **all 30 bootstrap
abbreviations** (the exact list from migration 0005), not a sample.
RED before the fix (rows exist on a freshly migrated test DB),
GREEN after; it also documents the invariant for future
contributors.

## Decision D4 — Acceptance is the full-suite delta

The only trustworthy acceptance is the whole suite: 74 → 0 errors
AND no new failures/errors anywhere (a test that silently depended
on the seed would surface as a new error and must then be fixed to
create its own row — none is expected per the audit, but the gate
proves it).

## Risks / Trade-offs

- A future consumer of sample data in tests would need to create its
  own rows (explicit is better); the canary plus D4 keep this
  visible.
- `eqmd_dev` runtime (dev DB) keeps its seeded rows — no behavior
  change outside test databases.
