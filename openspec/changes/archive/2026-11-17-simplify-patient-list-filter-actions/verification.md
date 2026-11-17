# Verification: Patient-list filter actions

## Required Fixture and Runtime Gates

Before implementation, establish available browser tooling, the target checkout
and an operator-supplied or explicitly approved disposable fixture manifest.
Do not create shared users, memberships, tags or profile defaults just to unblock
verification. Isolated Django test fixtures follow the existing test command.

The main live/preview actor MUST have a valid active specialty and a saved
non-empty default tag X with known mode. Supply another readable active tag Y
and eligible disposable patients covering X, Y, both and no tags. Include cases
for saved-empty, principal-only, no valid specialty and unavailable defaults;
these secondary cases may be isolated Django integration tests when live
transitions are not explicitly approved.

Record exact owned IDs, initial profile/default state, expected patient IDs,
credential environment-variable names and operator cleanup responsibility.
Never store credentials or authenticated browser state in evidence. Profile
changes and fixture lifecycle transitions are operator-controlled.

Confirm the container actually serves the changed checkout and matching files.
Do not restart, remount, migrate or overwrite /projects/dev/eqmd from a worker.
If only a workspace preview is available, label it explicitly and record which
HTML/assets are routed versus served. Missing meaningful profile fixtures means
BLOCKED_NEEDS_DECISION, not passing proof from an empty profile.

## Mechanism and Evidence

Use installed Playwright/system Chrome following
`.pi/skills/verify-eqmd/SKILL.md` safety rules. A standalone evidence script may
resolve the existing package under that skill's harness/node_modules; do not
install a browser/dependency or modify its unrelated supervision journeys.

Keep reproducible evidence under:

```text
/tmp/eqmd-patient-list-filter-actions/<run-id>/
  manifest.json
  verify-S1.mjs
  run-instructions.txt
  assertions.json
  requests.jsonl
  screenshots/
  probes/
```

Record actions, assertions, URLs, role, viewport, source identity, exact commands
and exit statuses. Python probes are read-only and run via docker exec eqmd_dev.
GET filtering and draft edits must create no clinical or preference POSTs.

## Mandatory Browser Journey

1. Open the list without parameters: confirm saved default X/mode is applied
   and identified truthfully, with no redundant restore action.
2. Apply name/status/manual tags Y. Confirm the single action bar, read-only
   summary, no repeated applied-clear links and a truthful personalized label.
3. Enter different pending name/status/tags. Clear-all: prove the rendered
   predicates and controls are empty, eligible untagged patients can match,
   default X is suppressed, and preference data is unchanged.
4. Refresh and paginate the explicit cleared URL: X stays suppressed. A separate
   parameter-free entry still uses X. Do not confuse these two URLs.
5. Apply name Ana/status Internado/manual tags Y. Type pending name Bruno.
   Restore the specialty tags: Ana/Internado remain, default X/mode returns,
   Bruno is discarded and the page resets. Stored preference remains unchanged.
6. Remove draft chips using ×: other pending controls remain and results/URL
   do not change until Apply. Verify normalized dirty tracking and clean Apply.
7. Reach a filtered-empty result: show its explanation and refer to the action
   bar, without duplicate recovery controls. Genuine unfiltered-empty keeps its
   existing authorized creation explanation (an isolated view test can prove it).
8. Repeat the relevant native GET journey with JavaScript disabled: deselect
   all tags and Apply must produce explicit manual-empty rather than fallback.
9. Check 1440px and 390/320px, keyboard labels/focus and absence of extra overflow.
   Smoke-check map and both report surfaces: their old clear/default actions and
   JS transport/lookup behavior must remain unchanged.

The existing independent preference-save POST remains available; do not click it
during these no-write journeys. No bulk `Limpar seleção` control is added.
Use exact-ID operator cleanup after successful or failed runtime runs and
record the handoff/outcome. No general deletion or restoration is authorized.
