# Slice 004 — URL namespace consistency (runs last)

## Identity

- Slice: S4 of change `extend-document-duplication`.
- Task: `tasks.md` section 4.

## Objective

The `dailynotes`, `simplenotes`, and `historyandphysicals` URL namespaces
are consistent everywhere: `app_name` matches the mounted instance
namespace, and no reference uses the long `apps.*` spelling.

## Read first

- `AGENTS.md`
- `openspec/changes/extend-document-duplication/proposal.md`
- `openspec/changes/extend-document-duplication/design.md` — Decision E
- Mount points: `config/urls.py` (lines ~55–64)
- URLconfs: `apps/dailynotes/urls.py`, `apps/simplenotes/urls.py`,
  `apps/historyandphysicals/urls.py` (`app_name = "apps.*"` today)

## Requirements

- R1: `app_name` in the three URLconfs is the short form
  (`dailynotes`, `simplenotes`, `historyandphysicals`).
- R2: Every long-form reference
  `apps.(dailynotes|simplenotes|historyandphysicals):` in the
  repository (templates, Python, tests) is rewritten to the short form.
  Known locations (verify with grep, list may drift):
  - `apps/{dailynotes,simplenotes,historyandphysicals}/models.py`
    (`get_absolute_url`/`get_edit_url`)
  - `apps/events/templates/events/partials/event_card_{dailynote,simplenote,historyandphysical}.html`
  - `apps/events/templates/events/patient_timeline.html`
  - `apps/events/templates/events/widgets/recent_events.html`
  - `apps/simplenotes/tests/test_detail_context_ui.py`
  - `apps/historyandphysicals/tests/{test_permissions,test_detail_context_ui,test_integration}.py`
  - `apps/{dailynotes,simplenotes,historyandphysicals}/tests/test_duplication.py`
    (created by slice-003)
  - `docs/styling.md:358` (documentation example using the long form)
- R3: Post-condition: `rg -n "apps\.(dailynotes|simplenotes|historyandphysicals):"`
  over the repository (`apps config templates docs`) returns ZERO
  matches; full test suite green.
- R4: No routing change: route paths, URL names, and the mounted
  `namespace=` values in `config/urls.py` are unchanged; the only
  URLconf edits are the three `app_name` values. Evidence: the diffs of
  the three `urls.py` files touch only the `app_name` line, and the
  full suite stays green.

## Expected blast radius

- Modified: the three `urls.py`, the files listed in R2 (plus any file
  grep reveals; justify each in the report).
- Sensitive: `apps/events/templates/events/patient_timeline.html` is
  ALSO modified by the in-flight
  `harden-discharge-report-collaborative-draft` change (different
  regions). Before starting, confirm the current state of this file on
  the working base; keep the edit strictly to the namespace references
  (quick-add dropdown links), far from the card-dispatch region.
- Must not change: `config/urls.py` include namespaces (already short),
  other apps' namespaces (`apps.accounts`, `apps.research` are
  explicitly out of scope), route paths or names.

## Failing-before evidence

- Deterministic verification: run
  `rg -n "apps\.(dailynotes|simplenotes|historyandphysicals):"
apps config templates docs`
  and record the matches (expected: ~34 in code plus the
  `docs/styling.md` example). After the slice the same command must
  return no matches.

## Implementation constraints

- Mechanical rewrite only — no renames of URL names, no route changes,
  no template restructuring.
- Do not touch `apps.accounts`/`apps.research` prefixes (out of scope).
- Do not implement other slices.

## Validation

- Focused: `./scripts/test.sh apps.dailynotes`,
  `./scripts/test.sh apps.simplenotes`,
  `./scripts/test.sh apps.historyandphysicals`,
  `./scripts/test.sh apps.events`, `./scripts/test.sh apps.patients`.
- Project gates: `AGENTS.md` (full `./scripts/test.sh`).
- Grep evidence per R3 and the `urls.py` diff evidence per R4 in the
  report.

## Acceptance criteria

- [ ] R1–R4 verified (grep zero + suites green).
- [ ] Failing-before grep output captured.
- [ ] `patient_timeline.html` diff limited to namespace references.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: any short-form reference fails to
resolve after the change (indicates a second mount or a real
namespace collision); the `patient_timeline.html` region needed for the
rewrite conflicts with unmerged work from the in-flight discharge-report
change; a non-mechanical edit appears necessary.

## Evidence report

Write `/tmp/eqmd-slice-S4-report.md` (same structure as S1; include
before/after grep output).

## Worker handoff

Implement only this approved slice. Treat the slice and referenced
OpenSpec artifacts as the implementation contract. Reconstruct context
from the listed files; do not rely on prior conversation. Follow the
repository engineering policy in `AGENTS.md` and preserve existing
conventions. Produce failing-before (grep) evidence, implement the
smallest correct change, run focused validation, and produce the
required evidence report. Do not update `tasks.md`, commit, push,
merge, archive, or start another slice. If a new decision is required,
stop with `BLOCKED_NEEDS_DECISION` and evidence. Otherwise finish with
`READY_FOR_REVIEW` and `REPORT_PATH=/tmp/eqmd-slice-S4-report.md`.
