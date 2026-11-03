# Tasks: isolate-sample-specialty-seed-from-tests

## 1. Seed isolation

Contract: `slices/slice-001-seed-isolation.md`

- [x] 1.1 Gate `0005_populate_sample_specialties` behind
      `EQMD_SEED_SAMPLE_SPECIALTIES` (default `True`) and set it to
      `False` in `config/test_settings.py`.
- [x] 1.2 Add the seed-isolation canary test (RED before, GREEN
      after).
- [x] 1.3 Full suite: 74 pre-existing errors → 0, with zero new
      failures/errors; focused accounts/patients/events/core green.
