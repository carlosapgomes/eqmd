# Design: Restore Green Development Quality Gates

## Context

The project documents Django 5.2.1. Before slice 001, `pyproject.toml` allowed
any Django version `>=5.2.1` and the running `eqmd_dev` container reported
Django 6.1, although the committed `uv.lock` already resolved Django 5.2.1. The
production Dockerfile ignored the lock, which caused the runtime divergence.
Development-only tools were not fully declared or installed by the image, and
`scripts/typecheck.sh` mutates the running container as root when Mypy is
missing.

Slice 001 also proved a separate, version-independent migration drift. The
latest `django-oidc-provider` migrations and the retained PostgreSQL schema use
`AutoField` for six model PKs, while its AppConfig inherits the project's
`BigAutoField` default at runtime. Reslice 001A aligns this legacy vendor app
with its migrations and schema without generating a migration.

The full suite is also red across ten apps. The earlier
`stabilize-test-suite-lifecycle-gates` change created
`NavigationReadyUserFactory` and a lifecycle AST guard rail, but its closure
report intentionally left setup, stale-contract, and functional failures for
later work. The guard rail currently audits without enforcing zero.

The patient-identity change is blocked by this baseline. This design restores
quality signals without mixing test-suite stabilization into clinical feature
slices.

## Governing Decision

See `docs/adr/ADR-0001-deterministic-development-quality-gates.md`.

The proposed policy is:

1. use the Django 5.2 LTS minor line (`>=5.2.1,<5.3`) until a separate upgrade
   change approves another minor/major line;
2. resolve application and development dependencies from `uv.lock` in Docker
   and CI;
3. provision Ruff/Mypy during image/environment construction, never from a
   quality script at runtime;
4. restore tests contract-first in app/domain cohorts;
5. require a green full suite before critical clinical feature work resumes.

The implementer must confirm all concrete dependency commands against the
installed `uv` version and existing Docker workflow before editing. The design
specifies outcomes, not an unverified Docker command sequence.

## Design Principles

### 1. Deterministic environments first

No failure classification is reliable while local Docker and CI resolve
incompatible framework versions. Runtime and dev-tool dependencies must be
locked before repairing tests.

Production images must not accidentally include the development dependency
group. Development images or targets must contain required quality tools at
build time. `scripts/typecheck.sh` and similar gates must report a missing tool
and exit nonzero rather than install it.

### 2. Contract-first repair

For every failing cohort, the implementer must identify the authority in this
order:

1. active OpenSpec delta and current canonical specs;
2. accepted ADRs and documented domain rules;
3. current migrations/model contracts and supported public interfaces;
4. established behavior covered by green tests;
5. the failing legacy test.

A failing test is not automatically correct. A production implementation is
not automatically authoritative merely because it is current.

If the test is stale, update only its setup or expectation and explain the
contract evidence. If production behavior is wrong, add or preserve a RED
regression test before the minimal production fix. If authority remains
ambiguous, stop `INCOMPLETE` and ask the planner; do not guess.

### 3. Vertical stabilization slices

A stabilization slice is vertical when it makes a named executable gate green
for one coherent domain cohort. Each slice has:

- a recorded RED baseline and failure-ID manifest;
- a bounded file cohort;
- contract inspection;
- minimal GREEN repair;
- focused static checks and tests;
- a full-suite comparison proving no new failures elsewhere;
- a temporary report reviewed before the next slice.

Known failures outside the current cohort do not make an intermediate slice
incomplete. The targeted command must, however, finish with exit code 0 and
zero failures/errors. The final slice has no baseline waiver.

### 4. No failure laundering

The following are forbidden:

- deleting or skipping failing tests without an approved reason;
- weakening assertions merely to match current output;
- increasing guard-rail thresholds;
- adding blanket Ruff/Mypy ignores;
- catching exceptions only to force green;
- substituting SQLite or mocks for required PostgreSQL behavior;
- changing clinical behavior without spec evidence;
- classifying an unexplained failure as preexisting and moving on.

### 5. Evidence without sensitive data

Reports may contain test IDs, synthetic fixture values, commands, exit codes,
aggregate counts, and small non-sensitive snippets. They must not query,
include, or reproduce identifiable restored patient data.

## Slice Sequence and Dependencies

### Foundation

1. Lock Django/runtime resolution and Docker dependency installation.
2. Complete lock closure and align the legacy OIDC primary-key contract.
3. Make development tooling and CI gates reproducible and fail closed.
4. Clear static-analysis blockers in `apps/patients/forms.py` separately from
   clinical feature changes.

### Patients

1. Repair legacy patient user fixtures: history and record tracking cohort.
2. Repair record-number create validation exposed by that cohort.
3. Repair the signal fixture and soft-deleted timeline-event recovery exposed
   by validation of the correction.
4. Repair patient API, development, and performance setup cohort.
5. Complete aggregate dry-run and verbosity safety for the patient refresh
   command exposed by that cohort.
6. Restore tag HTTP/error-handling contracts.
7. Repair the tag-add view's swallowed `Http404` and malformed tag-id body
   handling exposed by that cohort.
8. Restore tag architecture/integration contracts.
9. Restore admission, status, and soft-delete contracts.
10. Require the entire `apps.patients` suite to be green.

### Remaining apps

1. Restore the drug-template cohort.
2. Restore the outpatient-prescription cohort.
3. Restore mediafiles model/security/form foundations.
4. Restore mediafiles HTTP/integration/performance cohorts.
5. Restore PDF forms model/service/mapping foundations.
6. Restore PDF forms admin/HTTP/security cohorts.
7. Restore events and history-and-physicals cohorts.
8. Restore Matrix, PDF generator, and sample-content cohorts.

### Closure

1. Enforce lifecycle guard rail zero, run the full repository gate, and
   re-verify the blocked patient-identity slice.

Only one slice may be implemented at a time. A slice must be verified by a
third LLM before the next begins.

## Failure Cohort Map

The initial aggregate inventory is authoritative only for planning; every
slice must regenerate its own exact failure-ID baseline.

| Cohort            | Initial problems | Dominant signals                                  |
| ----------------- | ---------------: | ------------------------------------------------- |
| Patients          |              145 | lifecycle 302, obsolete user fields, tags, status |
| Drug/prescription |              107 | missing fixtures, obsolete fields/contracts       |
| Mediafiles        |              200 | missing `Hospital`, old Patient/Photo APIs        |
| PDF forms         |               85 | validation, mapping, permissions, mocks, URLs     |
| Remaining apps    |               36 | soft delete, lifecycle, constructor/API drift     |

## File-Scope Policy

Each slice lists expected test and production candidate files. A file outside
that list requires planner approval before editing. Discovery of a real defect
in an unlisted production module is a reason to stop and propose a focused
follow-up slice, not permission to expand scope.

Generated assets, migrations, restored backups, and production data are always
out of scope. `uv.lock` may change only in the dependency-lock slice.

## Verification Strategy

### Intermediate slices

Every intermediate slice runs:

1. its focused target command, which must become fully green;
2. Ruff/format/Mypy for changed Python files where configured;
3. `manage.py check`;
4. `makemigrations --check --dry-run` after the runtime foundation is green;
5. `./scripts/test.sh` to compare failure IDs and prove no new failures;
6. OpenSpec and Markdown validation.

The full suite may remain red only for explicitly untouched downstream
cohorts. Any new failure ID or increased failure/error count requires
`INCOMPLETE` unless the report proves that an old loader/setup error was
replaced by the same cohort's now-visible tests and the target slice still
meets its acceptance contract.

### Final slice

The final slice requires all commands to return exit code 0, including the
full suite. No known-failure allowance remains.

## Rollback Plan

### Foundation rollback

Revert the dependency declaration, lockfile, Docker targets, quality scripts,
and CI changes together. Rebuild the previous image only with user approval.
Do not mix partial old/new lock semantics.

### Test-cohort rollback

Each cohort is independently revertible because slices do not share broad
refactors. Revert its test and minimal production corrections together so
regression tests never become detached from behavior.

### Production-fix rollback

The slice report must identify the exact production hunk, affected contract,
and rerun command. A rollback restores the previous production behavior and
its matching test expectation; no database rollback is expected because
migrations are forbidden.

## Risks and Mitigations

- **Framework pin exposes incompatibilities:** resolve before app repairs and
  verify container/CI parity.
- **Legacy tests encode obsolete assumptions:** use the authority order and
  stop on ambiguity.
- **Large formatting diff hides behavior:** isolate `forms.py` static cleanup
  in its own slice and require behavior tests before/after.
- **One root fix reveals many tests:** report failure-ID transitions rather
  than comparing counts alone.
- **Cross-app scope grows:** stop and create a new bounded slice when listed
  files are insufficient.
- **Critical feature pressure encourages waivers:** keep the identity change
  tasks unchecked until the final full gate is green.
