# Verification: Ward-map XLSX export

## Runtime and fixture boundary

Cache generation is excluded from this delivery. The dev cache is currently
expired; that is not authorization to run the shared generator, schedule
jobs or rewrite `WardMappingCache` rows outside tests.

Automated fixtures use the standard isolated PostgreSQL test database and
seed a healthy ward-mapping cache exactly as the background command writes
it, following the existing `seed_warm_cache` pattern in
`apps/patients/tests/test_ward_map_tag_filters.py`. Do not run the shared
generator to make verification possible.

Browser evidence (optional here, mandatory only if the operator requests
homologation) runs under the `.pi/skills/verify-eqmd` safety rules with a
TestCase-backed preview or an operator-approved live stack. A stale
live-dev cache is not valid evidence: the empty-result refusal is the
expected behavior there and must be labeled as such.

## Required primary fixture

A normal non-superuser clinical account with `patients.view_patient`:

- Two wards with published inpatients; one ward retained empty via
  `show_empty_wards`.
- One patient with two published notes (newest wins), one patient with only
  drafts, one patient with no notes at all, and one patient missing record
  number and admission date.
- Filters exercised: `q`, `ward`, `tag_filter` and `show_empty_wards`, plus
  an empty-result combination.
- A fresh valid cache referencing those wards/patients, reprojected by the
  real requester-aware service.

Record exact owned IDs, expected patient/ward IDs and cleanup owner. Never
save passwords, cookies, storage state or real clinical records in
evidence.

## Evidence location

```text
/tmp/eqmd-ward-map-xlsx-export/<run-id>/
  manifest.json
  assertions.json
  requests.jsonl
  screenshots/
```

Each slice report (see its contract) states `READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`, maps requirements to evidence, lists changed
paths, RED/GREEN proof, commands with exit statuses and any unresolved
limitations.
