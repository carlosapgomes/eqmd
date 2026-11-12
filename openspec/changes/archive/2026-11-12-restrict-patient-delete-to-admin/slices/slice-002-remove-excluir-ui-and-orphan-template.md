# Slice 02 — Remove clinical Excluir affordances and dead confirmation template

- Slice ID: S2
- Change ID: `restrict-patient-delete-to-admin`
- Task: `tasks.md` item 3 (Slice 2). Requires S1 accepted.

## Objective

One sentence: non-superuser sessions see no `Excluir` control for patients
anywhere in the clinical UI, and the orphaned confirmation template is gone.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/restrict-patient-delete-to-admin/proposal.md`
- `openspec/changes/restrict-patient-delete-to-admin/design.md` (Decisions 2–4)
- `openspec/changes/restrict-patient-delete-to-admin/specs/patient-delete/spec.md`
  (Requirement: no delete affordance)
- `apps/patients/templates/patients/patient_detail.html` (Excluir anchor)
- `apps/patients/templates/patients/patient_list.html` (Excluir anchor)
- `apps/patients/templates/patients/patient_confirm_delete.html` (orphan)
- S1 evidence report (route gate already superuser-only)

Follow the repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change; avoid speculative abstraction
and unrelated refactoring.

## Requirements

- R1: Patient detail page HTML for a non-superuser session contains no link
  or form targeting the `patient_delete` route.
- R2: Patient list page HTML for a non-superuser session contains no link or
  form targeting the `patient_delete` route.
- R3: `patient_confirm_delete.html` is deleted and nothing references it.
- R4: No other control, label, or flow in the two pages regresses (Editar,
  Timeline, and list actions keep working).

## Expected blast radius

- Likely: `apps/patients/templates/patients/patient_detail.html`,
  `apps/patients/templates/patients/patient_list.html`, deletion of
  `apps/patients/templates/patients/patient_confirm_delete.html`, focused UI
  assertions (extend an existing template/view test module, no new app).
- Sensitive / out of scope without escalation: `views.py` gating (S1 owns it),
  URL routes/namespaces, admin templates, Bootstrap-to-custom-CSS changes,
  any behavior beyond removing/gating the Excluir anchors.

## Failing-before plan

Failing-before evidence (run before changing templates):

- verification scenario: render (or `GET`) the patient detail and list pages
  as a non-superuser (e.g., doctor) and assert the response HTML contains an
  `Excluir` control pointing at the delete route.
- expected observable failure: the assertion "no delete control" fails on
  current code for both pages, and `patient_confirm_delete.html` exists with
  zero view references, proving the dead UI surface.

## Implementation constraints

- Design default: remove the `Excluir` anchors entirely (even superusers use
  `/admin/` for deletion). Gating with `{% if user.is_superuser %}` is allowed
  only if the team explicitly wants a superuser shortcut; a gated shortcut
  must POST with CSRF (never a plain GET link).
- Template edits only; no Python behavior change except test files.
- Do not "fix" the `apps.patients:` vs `patients:` namespace while here.
- Do not rewire, keep, or recreate a clinical confirmation page.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.patients.tests.test_views`
- template-focused suite covering the touched pages (same command above if
  assertions live there; otherwise the suite named in the evidence report).

Project-required gates: reference `AGENTS.md`; run the repo's required checks
for touched files before handoff.

Runtime/verification evidence: rendered-HTML assertions for detail + list as a
non-superuser (and superuser per the chosen remove-vs-gate outcome), plus
`grep` evidence over runtime code and templates (excluding `openspec/`,
`docs/`, and other planning/history records) that no template references
`patient_delete` (clinical) or `patient_confirm_delete.html` anymore.

## Acceptance criteria

- [ ] R1 verified: non-superuser detail HTML has no delete-route control.
- [ ] R2 verified: non-superuser list HTML has no delete-route control.
- [ ] R3 verified: orphan template deleted; no runtime code or template
      references it (planning/history docs excluded from the check).
- [ ] R4 verified: Editar/Timeline/list actions positively asserted working
      (not just page-status green); focused suites pass.
- [ ] No file outside the blast radius changed without written justification.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if any of these appears: product wants a
kept superuser shortcut in the clinical UI (needs POST-form decision);
any request for a clinical confirmation page; S1 gate missing or contradicted;
a required route/namespace/admin change; a new security/privacy/clinical
implication.

## Evidence report

Path: `/tmp/sirhosp-slice-restrict-delete-s2-report.md`

Include: status (`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`);
requirements → evidence; files changed; failing-before evidence; passing-after
evidence; commands with exit status; rendered-HTML/`grep` evidence;
unexpected blast-radius expansion with justification; risks/limitations;
decisions needing a human, if any.

## Worker handoff

Implement only this approved slice. Treat the slice and referenced OpenSpec
artifacts as the implementation contract. Reconstruct context from the listed
files; do not rely on prior conversation. Follow the repository engineering
policy. Produce failing-before evidence, implement the smallest correct change,
run focused validation, and produce the required evidence report. Do not update
`tasks.md`, commit, push, merge, archive, or start another slice. If a new
decision is required, stop with `BLOCKED_NEEDS_DECISION` and evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/sirhosp-slice-restrict-delete-s2-report.md`.
