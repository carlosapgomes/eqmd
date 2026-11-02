# S7: Searchable multi-tag filtering on the patient list

## Identity and objective

Change: `add-specialty-team-tag-governance`. Tasks: 7.1-7.3 in
[../tasks.md](../tasks.md). Depends on accepted S5; execute after S6 in this plan.
Deliver privacy-safe searchable active/historical tag selection and ANY/ALL list
queries with explicit manual-empty state and compatible legacy URLs.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D4 and D6](../design.md),
  [filtering spec](../specs/patient-tag-filtering/spec.md),
  [historical selector requirement](../specs/team-tag-governance/spec.md).
- `apps/patients/views.py:PatientListView`, `urls.py`, `tag_policy.py`,
  `templates/patients/patient_list.html`; `webpack.config.js` asset conventions.
- Accepted S5/S6 code; reports are supplementary, not required `/tmp` inputs.

## Requirements and evidence

- **R1:** Shared parser represents repeated tags, ANY/ALL and explicit cleared
  state; legacy `tag=<id>` means explicit ANY. Evidence: parser compatibility tests.
- **R2:** List results apply distinct ANY/ALL alongside existing status/name
  predicates without changing patient access. Evidence: two-team query matrix.
- **R3:** Searchable lookup is paginated, namespace-labelled and visibility-checked;
  old tags appear only on explicit request. Evidence: outsider/revoked/historical
  lookup and forged selection tests.
- **R4:** Form, active badges, clear, refresh and pagination preserve effective
  repeated parameters/mode. Evidence: HTML URL assertions and mobile browser flow.

## Allowed blast radius

- New `apps/patients/services/tag_filters.py`, `tag_lookup.py`;
  existing `tag_policy.py`, `tag_projection.py` as required by selection.
- `apps/patients/views.py` list orchestration, `urls.py`;
  new `views_tag_filters.py` for lookup and `forms_tag_filters.py`.
- `apps/patients/templates/patients/patient_list.html`;
  new `templates/components/_tag_filter.html`, `_tag_selector.html`.
- New `assets/js/tag-selector.js`; `webpack.config.js` for its source asset only.
- New `apps/patients/tests/test_tag_filters.py`, `test_tag_lookup.py`;
  existing `test_views.py`, `test_tag_navigation.py`, `test_tag_visualization.py`.
- `docs/patients/tags_management.md`, `docs/patients/api.md` query documentation.

No preference persistence or map integration yet; no schema/dependency changes,
clinical authorization changes or direct edits to generated `static/` assets.

## Failing-before plan

Write RED cases showing repeated parameters collapse to one tag, ALL is absent,
archived lookup cannot be selected, and explicit clear loses its meaning across
navigation. Include invalid tag-mode and malformed IDs. Inaccessible single-tag
inputs must already be denied by S5: retain those as regression tests, not RED
claims that would invalidate the accepted privacy checkpoint.

## Implementation constraints

Return generic validation errors for invalid explicit IDs; do not silently widen
the search. Deduplicate selections and patient results. Historical selection
never grants assignment rights. Avoid embedding restricted labels/IDs in DOM
options or response totals. Lookup endpoint has no create operation. Preserve
non-tag parameters with proper URL encoding, not concatenated unescaped values.
Use reusable components and source assets, with no third-party selector package.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_tag_filters
./scripts/test.sh apps.patients.tests.test_tag_lookup
./scripts/test.sh apps.patients.tests.test_tag_navigation
npm run build
```

Apply `AGENTS.md` full suite, scoped lint/types and changed Markdown lint.
Runtime evidence: mobile search/select two tags, toggle ANY/ALL, find an archived
visible tag, clear, paginate and refresh. A legacy bookmark must override any
future default without migration.

## Acceptance criteria

- [ ] R1: parser preserves repeated/empty/legacy distinctions.
- [ ] R2: ANY/ALL and conjunctive query matrix pass without duplicate patients.
- [ ] R3: lookup/history/input validation cannot disclose inaccessible tags.
- [ ] R4: URLs and mobile controls preserve effective state.
- [ ] Documentation, frontend build and all gates are evidenced.

## Escalation and report

Stop `BLOCKED_NEEDS_DECISION` for preference/schema work, new dependency needs,
unapproved query compatibility changes or unexpected private readers. Report
`/tmp/eqmd-team-tags-slice-007-report.md` using the shared schema with R1-R4
RED/GREEN evidence, command statuses and desktop/mobile observations.

## Worker handoff

Implement only approved S7 from canonical artifacts and accepted predecessor
code. Follow the shared contract. Do not update `tasks.md`, commit, push, merge,
deploy, archive or begin S8. Complete this slice's checklist only after
verification; return `READY_FOR_REVIEW` with `REPORT_PATH` or
`BLOCKED_NEEDS_DECISION` with evidence.
