# Slice 001 — Consent form duplication flow

## Identity

- Slice: `slice-001-consent-form-duplication`
- Change: `duplicate-consent-form`
- Tasks: `tasks.md` items 1.1–1.4 (Contract: this file)

## Objective

Deliver the full consent-form duplication flow end to end: form,
view, route, template, timeline-card action and regression tests,
adapted to the frozen-snapshot semantics (editable markdown at
re-creation, design D1).

## Read first

- `AGENTS.md`
- `openspec/changes/duplicate-consent-form/proposal.md`
- `openspec/changes/duplicate-consent-form/design.md` (D1–D6)
- `openspec/changes/duplicate-consent-form/specs/consent-forms/spec.md`
  (scenarios are the behavioral contract)
- `apps/consentforms/models.py` (immutability in `save`)
- `apps/consentforms/forms.py` (`ConsentFormCreateForm`)
- `apps/consentforms/views.py` (create view)
- `apps/consentforms/templates/consentforms/consentform_create_form.html`
- Mirrors: `apps/reports/views/report_views.py` (`ReportDuplicateView`),
  `apps/reports/forms.py` (`ReportDuplicateForm`),
  `apps/reports/urls.py`,
  `apps/reports/templates/reports/report_duplicate_form.html`,
  `apps/events/templates/events/partials/event_card_report.html`
- Test patterns: `apps/reports/tests/test_report_duplicate_view.py`,
  existing `apps/consentforms/tests/` fixtures

## Requirements

- **R1 — Route**: add to `apps/consentforms/urls.py`
  `path('<uuid:pk>/duplicate/', views.ConsentFormDuplicateView.as_view(), name='consentform_duplicate')`.
  Evidence: reverse resolves; focused tests green.
- **R2 — Form**: `ConsentFormDuplicateForm` in
  `apps/consentforms/forms.py` — a `ModelForm` (NOT a subclass of
  `ConsentFormCreateForm`), Meta fields
  `['document_date', 'procedure_description']` plus an extra
  `markdown = forms.CharField(widget=forms.Textarea)`; `__init__`
  pops `source`/`user`/`patient` kwargs and sets field-level
  initials (`markdown` = the source's `rendered_markdown` AFTER
  applying D6's one-shot date replacement;
  `procedure_description` = source's; `document_date` = today);
  validation reuses the create rules verbatim (date not in the
  future; description minimum 5 chars); the `template` reference is
  fixed to the source's (no active-template check); `save()` stamps
  the D2 matrix (`patient`, `template`, edited
  `rendered_markdown`, `rendered_at=now`, `event_datetime=now`,
  stripped `procedure_description`,
  `event_type=Event.CONSENT_FORM_EVENT`,
  `description = "Termo de Consentimento - {template.name}"`,
  `created_by`/`updated_by` = user). Evidence: GET prefill tests +
  POST save tests.
- **R3 — View**: `ConsentFormDuplicateView(LoginRequiredMixin,
PermissionRequiredMixin, CreateView)` with
  `permission_required = 'events.add_event'`; `dispatch` resolves
  the source via `get_object_or_404` and raises `PermissionDenied`
  when `can_access_patient` fails; `get_form_kwargs` passes
  `source`, `user`, `patient` (source's patient); context exposes
  `patient`, `source`, `patient_record_number`; success redirects
  to the patient timeline with the create view's pt-BR message
  pattern. Evidence: GET/POST tests incl. 403/404.
- **R4 — Template**: `consentform_duplicate_form.html` reusing the
  create layout (including the create form's preview block), title
  "Duplicar Termo de Consentimento", template name displayed
  read-only (no selector), markdown editor field, same
  submit/cancel affordances. Evidence: GET renders (assert template
  used + key content).
- **R5 — Card**: in `event_card_consentform.html`, between the PDF
  and attachment-edit buttons: link to the `consentform_duplicate`
  route for `event.pk`, `bi-files` icon, `btn-outline-info btn-sm`,
  tooltip/aria "Duplicar termo de consentimento", gated by
  `{% if perms.events.add_event %}`. Evidence: card render tests
  for both permission states.
- **R6 — Tests**: new
  `apps/consentforms/tests/test_duplicate_view.py` covering at
  least: GET prefills editable markdown with the source's
  `rendered_markdown` (today's date auto-replaced per D6 —
  including a case where the source date is absent from the text
  and it stays unmodified without error), procedure description,
  today as document date, template name read-only — asserting the
  replacement is one-shot at prefill (no dynamic binding: changing
  the `document_date` field afterwards must not alter the
  pre-filled text); POST with edited markdown creates
  an independent consent form (frozen edited text, fresh
  `rendered_at`, author = submitter, source's template FK,
  `event_type` correct); POST keeps source unchanged (markdown,
  dates, description, template, attachments count); duplicate of a
  source WITH attachments starts with zero attachments; source
  with deactivated template duplicates successfully; 403 without
  patient access; 404 unknown pk; card gating.
- **R7 — No regressions**: create/update/delete flows, the
  immutability invariant, `ConsentFormCreateForm` and the model are
  byte-identical except for the additions above. Evidence:
  `git diff --stat` limited to expected surfaces.
- **R8 — Post-conditions**: `rg -n "consentform_duplicate" apps`
  shows route + view + template + card + tests.

## Expected blast radius

Expected surfaces: `apps/consentforms/{forms.py,views.py,urls.py}`,
the new template, `event_card_consentform.html`, the new test
module. Sensitive surfaces that must not change (escalate first):
the model and its immutability, `render_template`,
`ConsentFormCreateForm/Views`, admin, migrations, any other app.
Extra files need justification in the report.

## Failing-before plan

Reproduce BEFORE implementing (record outputs):

- from a Django shell, reverse the
  `consentforms:consentform_duplicate` route with a uuid kwarg →
  expected `NoReverseMatch`;
- `manage.py test apps.consentforms.tests.test_duplicate_view` →
  expected module-not-found (tests are the RED step; write them
  first against the contract, then implement to GREEN).

## Implementation constraints

- The duplicate is a NEW document: never mutate the source, never
  create any cross-reference, never copy attachments (D2).
- The edited markdown freezes at submission (`rendered_at` = now);
  per-document immutability afterwards is preserved by existing
  model logic.
- Do NOT modify `ConsentFormCreateForm`, existing views, the
  model, `render_template`, admin, or migrations.
- No commits/pushes; no dependency installs; no new deps; do not
  update `tasks.md`.

## Validation

- Focused (worker): `apps.consentforms apps.events` via the
  established container runner (controller-provided; test DB
  `test_eqmd_dev_dupconsent1`).
- Project gates: full suite error set must equal the recorded
  74-error fully-qualified pre-existing baseline
  (`/tmp/eqmd-slice-loop/eqmd/extend-document-duplication/exec-4-prep/post-merge-err-ids.txt`);
  extract with `grep -E "^ERROR:" <log>` piped to
  `sed -E 's/^ERROR: (\w+) \(([^)]+)\).*/\2.\1/' | sort`.
- `ruff check` on changed `.py` files — zero NEW findings vs
  `SLICE_BASE_REF`.

## Acceptance criteria

- [ ] AC1: duplicate route resolves (R1).
- [ ] AC2: GET form prefilled per R2 — editable markdown from
      source with today's date auto-replaced (and best-effort no-op
      case), description copied, date = today, template
      read-only (test-asserted).
- [ ] AC3: POST creates independent corrected term per R2/R3 —
      frozen edited text, fresh `rendered_at`, submitting author
      (test-asserted).
- [ ] AC4: source unchanged and zero attachments copied
      (test-asserted).
- [ ] AC5: inactive-template source duplicates successfully
      (test-asserted).
- [ ] AC6: 403/404 handling test-asserted.
- [ ] AC7: card action present/absent per permission
      (test-asserted).
- [ ] AC8: full suite = baseline identity; ruff zero new findings.
- [ ] AC9: diff limited to expected blast radius (extras justified).

## Escalation conditions

Stop and return `BLOCKED_NEEDS_DECISION` with evidence if: the
immutability invariant rejects the new document; the create-form
validation cannot be reused per R2; a new product/clinical decision
emerges (e.g. date-in-text handling beyond manual editing); blast
radius must expand materially.

## Evidence report

Report to the controller-bound output path (slice-loop evidence
root): status, R1–R8 → evidence, failing-before + passing-after,
commands + exit codes, error-identity proof, `git diff --stat`,
deviations, risks. End with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
