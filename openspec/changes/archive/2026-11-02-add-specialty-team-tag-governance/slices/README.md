# Slice execution and decomposition review

## Review scope

Reviewed with the installed `openspec-vertical-change-writer` skill (the local
vertical-slice writer). Product requirements and the four delta specs are
unchanged. Only execution boundaries, dependencies and evidence contracts change.

The previous S2 mixed catalogue identity/migration with lifecycle and ownership.
The previous S3 mixed atomic writes, event migration, all read privacy and timeline
presentation. Each required multiple independently reviewable acceptance suites.
Splitting those two slices gives nine slices, not a new product or architecture.
The unavoidable cross-reader privacy work stays together to avoid a false
"secured" checkpoint while another reader still exposes private metadata.

## Sequence and checkpoints

Execute sequentially in the accepted checkout, one approved slice per run.
No concurrent writers or automatic worker/reviewer orchestration is authorized.

<!-- markdownlint-disable MD013 -- table rows cannot be wrapped -->

| Slice                                    | Observable checkpoint                              | Technical dependencies |
| ---------------------------------------- | -------------------------------------------------- | ---------------------- |
| [S1](slice-001-team-membership.md)       | Admin grants/revokes team roles                    | None                   |
| [S2](slice-002-catalogue-governance.md)  | Admin creates namespaced tags/principal mapping    | S1                     |
| [S3](slice-003-catalogue-lifecycle.md)   | Admin archives/restores/transfers same identity    | S2                     |
| [S4](slice-004-audited-assignments.md)   | Patient/admin tag writes are authorized and atomic | S3                     |
| [S5](slice-005-patient-tag-privacy.md)   | Every reader protects current/historical metadata  | S4                     |
| [S6](slice-006-leader-tag-page.md)       | Responsible leader maintains own team tags         | S5                     |
| [S7](slice-007-multi-tag-list-filter.md) | User filters list with searchable ANY/ALL tags     | S5                     |
| [S8](slice-008-specialty-preferences.md) | User saves/reuses independent team defaults        | S1, S7                 |
| [S9](slice-009-map-parity-release.md)    | Cached map matches filters/defaults and live tags  | S5, S8                 |

<!-- markdownlint-enable MD013 -->

S2-S4 are integration checkpoints, not a restricted-tag release: existing readers
are not declared safe until S5. S5's privacy gate does not certify map assignment
freshness or multi-tag parity; those belong to S9. The design already prohibits
partial production rollout; final release review still requires all nine slices.
Do not add feature flags or new deployment behavior to compensate for sequencing.

## Previous-to-current mapping

- Old S1 -> S1: membership behavior unchanged.
- Old S2 -> S2 catalogue identity plus S3 lifecycle/responsibility.
- Old S3 -> S4 assignment/audit writes plus S5 read privacy/current timeline tags.
- Old S4 -> S6: leader page.
- Old S5 -> S7: searchable multi-tag list.
- Old S6 -> S8: preferences.
- Old S7 -> S9: map parity and final integration checks.

No implementation has started; renumbering invalidates no completed task/report.

## Shared execution contract

Read `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`, the proposal,
design, relevant delta specs, this index and the selected slice. Follow repository
engineering policy and preserve existing conventions. Prefer the smallest correct
change; avoid speculative abstraction and unrelated refactoring.

Each slice lists its allowed expected paths. Additional production paths require
a planner-approved contract amendment under `AGENTS.md`; discovery alone is not
permission to expand scope. Mechanical tests/docs needed for the slice belong
with it, not in a final catch-all testing slice.

Build RED -> GREEN -> REFACTOR evidence using deterministic tests where practical.
Browser observations supplement tests; they do not replace server authorization
or transactional assertions. Use isolated test fixtures, never production PHI.
Apply the project-required full-suite/lint/type/Markdown gates in `AGENTS.md`.
Generated migrations may run in the isolated test DB; applying them to a live
DB or deploying any slice requires separate human approval.

Accepted predecessor code plus canonical artifacts are authoritative. A fresh
worker must not depend on the previous conversation or a surviving `/tmp` file.
Prior reports are supplementary: if absent, reconstruct from accepted code and
rerun the stated focused predecessor regression rather than inventing context.

Every handoff stops after its slice. Do not update `tasks.md`, commit, push,
merge, archive, deploy or start another slice. The planner/operator updates task
progress after review; only the slice acceptance checklist is marked by its worker.

## Evidence report and escalation

Use the report path given in each slice. Include:

- status: `READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`;
- each R-number -> test/inspection/runtime evidence;
- changed files and any requested scope amendment;
- failing-before and passing-after evidence;
- commands and exit statuses, including project gates;
- runtime evidence where required, limitations and remaining risks;
- any decision needed from a human.

Stop `BLOCKED_NEEDS_DECISION` on a spec/design conflict, new product or privacy
choice, material blast-radius growth, unapproved persistence/FSM/compatibility
change, inability to prove the slice, or an unexplained regression. Never broaden
clinical access, weaken assertions or assume deployment approval to finish.

## Requirement coverage

Each entry names the exact requirement in the corresponding delta spec. Final
cross-surface release regression belongs to S9 even when first delivered earlier.

### Accounts delta

- User Specialties Property; Primary Specialty Property; User Current Specialty;
  Specialty Change API -> S1.
- Administrator-managed team membership and leadership -> S1.
- Revocation retains preferences and immediately removes authority -> S1 for
  membership identity, S5 for metadata, S8 for persisted preference revalidation.

### Team tag governance

- Independent tag origin and visibility -> S2.
- Reserved names within namespaces -> S2, retained through lifecycle in S3.
- Public principal tag for each team -> S2 configuration, S4 mutation restrictions,
  S8 automatic-default fallback/warnings.
- Administrator catalogue control -> S2 classification, S3 lifecycle/transfer.
- Responsible leader self-service -> S6.
- Transfer responsibility without changing creator -> S3, exercised by S6.
- Active inactive and archived lifecycle -> S3; assignment behavior in S4.
- Administrator restoration preserves tag identity -> S3.
- Request-time restricted visibility -> S5; selector regressions S7; map S9.
- Policy-checked patient tag assignments -> S4.
- Patient tags survive clinical transitions -> S4 regression.
- Searchable historical catalogue -> S7.

### Patient tag audit

- Atomic patient assignment audit -> S4.
- Stable catalogue identity in timeline events -> S4 migration/writes, S5 reader.
- Restricted timeline actions are generically visible -> S5.
- Current visibility governs historical events -> S5.
- Mixed bulk events redact each hidden classification -> S5.
- Current tags are visible on the patient timeline -> S5.
- Catalogue lifecycle and ownership audit -> S2 creation/edit, S3 transitions.
- Tag audit is immutable in ordinary patient workflows -> S4.

### Patient tag filtering

- Searchable multi-tag ANY and ALL filtering -> S7 list, S9 map.
- Per-user specialty preference identity -> S8.
- Initial entry applies explicit specialty defaults -> S8 list, S9 map.
- Manual override clear and reapply are distinct -> S7 manual state, S8 defaults,
  S9 map navigation.
- Explicit preference save -> S8.
- Invalid automatic defaults warn without hiding patients -> S8, S9 parity.
- Historical manual filters preserve identity -> S7, S9 parity.
- Legacy single-tag filter compatibility -> S7, S9 parity.
- Map privacy and totals reflect filtered results -> S5 privacy, S9 freshness/totals.
- Visible effective filter context -> S7 list, S8 defaults, S9 map.

## Review checklist

- [x] No product/spec requirement changed during decomposition review.
- [x] Old S2/S3 split by observable workflows, not arbitrary model/view layers.
- [x] Every requirement has a first delivery and verification owner.
- [x] Every slice links tasks, dependencies, fresh-context inputs and evidence.
- [x] Write atomicity and read redaction have separate acceptance boundaries.
- [x] Partial integration is not mislabeled as deployable or privacy-complete.
- [x] Predecessor reports are not required persistent dependencies.
- [x] Implementation remains unstarted and all implementation tasks unchecked.
