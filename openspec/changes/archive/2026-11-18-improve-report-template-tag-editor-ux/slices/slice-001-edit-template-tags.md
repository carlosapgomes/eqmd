# RTTE-S1 — Searchable removable template classification

## Identity and Objective

Change: improve-report-template-tag-editor-ux.
Task: [tasks.md 1.1](../tasks.md#1-usable-classification-on-create-and-update).
Deliver ordinary enhanced multiple selection and last-chip removal on template
create/update, persisting only through existing explicit form submission.
Dependency: separate implementation approval; none is implied by planning.

## Read First

Read AGENTS.md, PROJECT_CONTEXT.md, openspec/config.yaml and canonical coding
standards, then:

- ../proposal.md, ../design.md, ../specs/reports/spec.md, ../verification.md.
- openspec/specs/reports/spec.md classification/authority/retention/audit.
- apps/reports/forms.py: ReportTemplateForm and tag_ids validation.
- apps/reports/templates/reports/reporttemplate_form.html.
- apps/reports/services/template_tag_projection.py: editor_tag_choices.
- apps/reports/services/template_tags.py: marker, delta, locking and persistence.
- apps/reports/views/template_views.py and existing classification tests.
- assets/scss/main.scss chip/removal classes; webpack.config.js copy entries.
- apps/core/templatetags/static_assets.py for delivery behavior.
- .pi/skills/verify-eqmd/SKILL.md for runtime safety.
- Prior RTFA reports/manifests if available; their accepted working-tree state
  is protected, not part of this feature.

## Requirements and Planned Evidence

- **R1:** Search and ordinary click/tap add multiple offered choices without
  replacement/duplicates or network. Evidence: host harness and real create POST.
- **R2:** Named × removes any chip, including the final one, with no default
  insertion. Evidence: browser update-to-empty and actual persisted editable set.
- **R3:** Draft selection mirrors one native tag_ids field plus the existing
  marker; no parent submit/history/storage/unrelated-field write until Save.
  Evidence: serialized requests, sentinels, Enter/reset and database snapshots.
- **R4:** Offered/historical/protected and current POST authority boundaries
  remain intact. Evidence: per-role projection, historical retention/removal,
  forged/revoked rejection, M2M/history rollback and generic errors.
- **R5:** Bound errors preserve submitted authorized choices or empty rather
  than stale initial tags. Evidence: invalid-field re-render and successful retry.
- **R6:** Keyboard, touch, long labels, generic empty states and native fallback
  work. Evidence: 1440/390/320px, 24/44px targets,
  JS-disabled and blocked-asset saves.
- **R7:** Only template create/update load the built versioned editor module;
  accepted filters and clinical flows stay unchanged.
  Evidence: source/assets/hashes plus discovery/patient/clinical regression smoke.

## Expected Blast Radius

Approved existing source edits:

- apps/reports/templates/reports/reporttemplate_form.html:
  only Tags-block include, required tag-library load and editor asset reference.
- webpack.config.js: only one source-to-static copy pattern for the editor.

Approved new paths:

- apps/reports/templates/components/\_report_template_tag_editor.html.
- assets/js/report-template-tag-editor.js.
- apps/reports/tests/test_template_tag_editor.py.
- apps/reports/tests/test_template_tag_editor_submission.py.
- apps/reports/tests/template_tag_editor_fixtures.py, if needed.
- apps/reports/tests/template_tag_editor_harness.cjs.

Generated js/report-template-tag-editor.js and build outputs are produced only
by npm run build, never manually edited. Report generated tracked changes.

Keep forms.py, views, URLs, models, projection/association/policy services,
shared selector/discovery/patient JS, preference flows and global/base loading
read-only. No CSS, new endpoint, dependency or migration is planned.
Any unlisted/material expansion requires evidence and operator approval.

## Failing-Before Plan

Follow RED -> GREEN -> REFACTOR. Automated component/harness tests must pin
the new interaction and single-field submission contract. Before browser proof:
ordinary X then Y replaces X, no explicit last-chip × exists, and the field has
no search. Preserve backend zero/multiple saves as existing positive controls;
do not invent a backend failure to justify the UI work.

An absent test symbol, missing asset or unhealthy fixture is not semantic RED.
Use the real form and user actions to reproduce R1/R2 on both current surfaces.

## Implementation Constraints

Follow repository engineering policy and preserve existing conventions.
Implement design D2-D6, not a reusable-selector framework.

The enabled native select stays the sole named tag_ids source. No second hidden
identity list, default/manual markers, lookup transport or auto-save is allowed.
Read rendered selected options, not saved field.initial, and use text-only DOM
construction. Initialize idempotently without stranding the native fallback.

Reuse neutral chip styles and Bootstrap utilities. Search results are contained
in-flow and generic empty messaging describes only this field. No bulk clear,
inline catalogue creation, specialty-default action or filter Apply is added.
Every generated interaction button is type=button; preserve outer form/CSRF.
New modules remain below 300 lines and functions <=40 lines. If the local design
cannot meet these bounds, stop with evidence rather than expanding silently.

## Validation

Focused command, after adding the planned new tests:

```bash
./scripts/test.sh apps.reports.tests.test_template_tag_editor \
  apps.reports.tests.test_template_tag_editor_submission \
  apps.reports.tests.test_template_tags \
  apps.reports.tests.test_template_tag_history \
  apps.reports.tests.test_template_views \
  apps.reports.tests.test_template_catalogue_s3 \
  apps.reports.tests.test_template_creation_s4 \
  apps.reports.tests.test_template_selection \
  apps.core.tests.test_static_assets \
  apps.patients.tests.test_patient_list_filter_actions \
  apps.patients.tests.test_ward_map_filter_actions
node apps/reports/tests/template_tag_editor_harness.cjs
npm run build
```

Project-required gates: AGENTS.md and canonical coding standards; run scoped
lint/type/format, Markdown/OpenSpec checks and affected legacy host scenarios.
Existing Node absence in the container does not waive host execution.

Runtime evidence: verification.md matrix against actual built scripts and
real Django/PostgreSQL fixtures. Declare live versus routed transport honestly.
No operator profile, clinical save, shared cache generation or service lifecycle
operation is authorized. Prove intended template/M2M writes and exact rollback.

## Acceptance Criteria

- [ ] R1: Ordinary enhanced multi-selection/search preserve unique choices.
- [ ] R2: Final editable chip is removable and empty saves correctly.
- [ ] R3: Single native submission contract and local-only draft behavior pass.
- [ ] R4: Mutation authority, historical/protected links and audit remain safe.
- [ ] R5: Invalid forms keep authorized submitted state and support retry.
- [ ] R6: Responsive accessibility and native/failed-asset fallback pass.
- [ ] R7: Versioned build and protected-surface regression evidence are complete.

## Escalation and Evidence Report

Return BLOCKED_NEEDS_DECISION for contradictions, new product/architecture
choices, unlisted/material scope, compatibility/schema/persistence changes,
security/privacy/clinical implications or inability to deliver this contract.

Write /tmp/sirhosp-slice-RTTE-S1-report.md with status, R-to-evidence mapping,
changed paths, RED/GREEN/refactor, actual commands/exit codes, runtime/source/
asset identity, baseline comparison, intended/forbidden writes, exact-owner
cleanup, expansion decisions and limitations.

Implement only this approved slice and reconstruct context from these artifacts.
Do not update tasks.md, sync specs, commit, push, merge, archive or start more work.
Stop with READY_FOR_REVIEW and REPORT_PATH, or BLOCKED_NEEDS_DECISION.
