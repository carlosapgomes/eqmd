# S8: Per-user specialty filter preferences

## Identity and objective

Change: `add-specialty-team-tag-governance`. Tasks: 8.1-8.3 in
[../tasks.md](../tasks.md). Depends on accepted S1 and S7. Deliver retained
user-specialty tag/mode preferences, initial defaults, manual overrides and
explicit save/reapply actions on the patient list.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D1 and D6](../design.md),
  [accounts delta](../specs/accounts/spec.md),
  [filtering spec](../specs/patient-tag-filtering/spec.md).
- Accepted S1/S7 code; reports are supplementary, not required `/tmp` inputs.
- `apps/accounts/models.py`, `forms.py`, `views.py`, `urls.py`, profile templates;
  S1 `services/team_membership.py`; S7 filter parser, lookup and components.

## Requirements and evidence

- **R1:** One retained preference per membership stores tags/mode and distinguishes
  absent from saved-empty; principal is optional. Evidence: PostgreSQL model and
  migration tests plus two-team selection cases.
- **R2:** Explicit manual state overrides saved defaults; saved defaults override
  first-use principal fallback. Evidence: precedence/clear/reapply integration tests.
- **R3:** Save is explicit, CSRF-protected and limited to the current user's valid
  active specialty; historical/inaccessible tags cannot be saved. Evidence:
  forgery, stale-context, cross-user and no-GET-save tests.
- **R4:** Invalid automatic tags are omitted with generic warnings; all-invalid
  means no tag predicate, not no results. Revocation retains settings without
  granting eligibility. Evidence: inactive/archive/revoked/rejoin cases.

## Allowed blast radius

- `apps/accounts/models.py`, `forms.py`, `views.py`, `urls.py`;
  new `services/tag_preferences.py`, `views_tag_preferences.py`,
  `forms_tag_preferences.py`.
- New sequential accounts migrations (preserve every existing migration).
- `apps/accounts/templates/accounts/profile.html`,
  new `apps/accounts/templates/accounts/tag_preferences.html`.
- `apps/patients/services/tag_filters.py`, `views.py` list context only;
  `templates/components/_tag_filter.html`, `_tag_selector.html`;
  `apps/patients/templates/patients/patient_list.html`.
- `assets/js/tag-selector.js` only as needed for explicit save/clear/reapply.
- New `apps/accounts/tests/test_tag_preferences.py`;
  `apps/patients/tests/test_tag_filters.py` and
  `apps/accounts/tests/test_team_membership.py` for integration.
- `docs/patients/tags_management.md`, `docs/admin_guide_medical_specialties.md`.

No map rewrite, catalogue policy relaxation, implicit preference mutation, team
membership management by leaders, or session-wide hardcoded tag selections.

## Failing-before plan

Write RED cases for missing preferences, empty-vs-absent behavior, unwanted
principal reinsertion, cross-team overwrites and revoked membership retaining
settings. Prove manual clear survives refresh without a database write.

## Implementation constraints

Preferences attach to retained membership identity; deactivation never cascades
settings. Use the same selection representation as S7 so S9 can consume it.
Save validates the user's still-current context, rejecting forged or stale
specialty targets rather than writing into a different active team silently.
Saved IDs remain stored when temporarily invalid; warn/omit at read time rather
than silently rewriting preferences. Invalid manual input remains an error.
User-facing default mode is ANY before an explicit preference is saved.
No live database migration/application is authorized.

## Validation

Focused:

```bash
./scripts/test.sh apps.accounts.tests.test_tag_preferences
./scripts/test.sh apps.accounts.tests.test_team_membership
./scripts/test.sh apps.patients.tests.test_tag_filters
./scripts/test.sh apps.accounts
npm run build
```

Apply full suite, scoped lint/types and Markdown gates from `AGENTS.md`.
Runtime evidence: save different defaults for two specialties, switch context,
clear without saving, explicitly save empty, reapply, and revoke/rejoin membership.
Demonstrate a generic unavailable-default warning with otherwise eligible results.

## Acceptance criteria

- [ ] R1: independent retained settings and saved-empty semantics are proven.
- [ ] R2: manual/saved/principal/none precedence and navigation persist correctly.
- [ ] R3: mutation is explicit and forged/stale-context saves are denied.
- [ ] R4: invalid defaults warn without data loss or restricted metadata exposure.
- [ ] Profile/list browser evidence, additive migration and all gates pass.

## Escalation and report

Stop `BLOCKED_NEEDS_DECISION` for changed matching semantics, cross-team settings,
new authorization rules or destructive migration requirements. Report
`/tmp/eqmd-team-tags-slice-008-report.md` using the shared schema with R1-R4
RED/GREEN, command exit statuses, runtime evidence and limitations.

## Worker handoff

Implement only approved S8 from canonical artifacts and accepted S7 code.
Follow the shared contract. Do not update `tasks.md`, commit, push, merge, deploy,
archive or start S9. Mark only this slice's checklist after verification. Return
`READY_FOR_REVIEW` with `REPORT_PATH` or `BLOCKED_NEEDS_DECISION` with evidence.
