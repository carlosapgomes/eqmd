# Slice 001 — PDF template preview (authenticated)

## Identity

- Slice: `slice-001-pdf-template-preview`
- Change: `serve-protected-media`
- Tasks: `tasks.md` items 1.1–1.4 (Contract: this file)

## Objective

Serve blank PDF form templates through an authenticated
preview view that works in production (`DEBUG=False`), and
point the admin + template-list links at it instead of raw
`/media/...` URLs (design D2).

## Read first

- `AGENTS.md`
- `openspec/changes/serve-protected-media/proposal.md`
- `openspec/changes/serve-protected-media/design.md` (D1, D2, D5)
- `openspec/changes/serve-protected-media/specs/pdf-forms/spec.md`
  (scenarios are the behavioral contract)
- `apps/pdf_forms/views/base_views.py` (authoritative module —
  sibling `views.py` is shadowed by the `views/` package and
  stays untouched) + `apps/pdf_forms/views/__init__.py`
  (star-export)
- `apps/pdf_forms/permissions.py`
  (`check_pdf_form_template_access`)
- `apps/pdf_forms/urls.py` (urlconf + `app_name`)
- `apps/pdf_forms/admin.py` (`pdf_preview` + `pdf_file`
  widget in fieldsets)
- `apps/pdf_forms/templates/pdf_forms/form_template_list.html`
  ("Ver PDF" button)
- Serve-response mirror:
  `apps/consentforms/views.py::ConsentFormAttachmentsZipView`
  (permission + streaming pattern)

## Requirements

- **R1 — View**: add `PDFFormTemplatePreviewView`
  (`LoginRequiredMixin`, `View`) in
  `apps/pdf_forms/views/base_views.py`: resolve the template
  via `get_object_or_404`, gate with
  `check_pdf_form_template_access(request.user)`, return
  `FileResponse(template.pdf_file.open("rb"),
content_type="application/pdf",
filename=basename(template.pdf_file.name),
as_attachment=False)`; missing file on disk → 404. No
  `is_active` filter (D2). Evidence: focused tests green.
- **R2 — Route**: add to `apps/pdf_forms/urls.py`
  `path('template/<uuid:pk>/preview/',
views.PDFFormTemplatePreviewView.as_view(),
name='template_preview')`. Evidence: reverse resolves.
- **R3 — Links**: `PDFFormTemplateAdmin.pdf_preview` and the
  list "Ver PDF" button reverse `pdf_forms:template_preview`
  instead of `template.pdf_file.url`. Evidence: link-target
  tests.
- **R4 — Admin widget**: `ClearableFileInput` subclass
  routing the change-form existing-file link to the preview
  route via `value.instance.pk` (D2); wired through the
  template admin. Evidence: rendered-admin test.
- **R5 — Tests**: new or extended
  `apps/pdf_forms/tests/test_template_preview_view.py`
  covering at least: 200 + inline headers + streamed bytes
  equal to the stored file for an authenticated user;
  inactive template previews 200; one test under
  `override_settings(DEBUG=False)` asserting 200 (prod-mode
  proof); `Cache-Control: private` asserted; login redirect
  for anonymous; 404 unknown pk; 404 missing file on disk;
  quote/Unicode filenames served safely; admin
  `pdf_preview` output contains the reversed route; list
  page renders the preview link; change form renders the
  widget link. Storage writes in tests must use the test
  media root (`override_settings` per existing pdf_forms
  test patterns).
- **R6 — No regressions**: list view, admin behavior,
  generation (`PDFFormOverlay`), download view, and
  `views.py` untouched except the link targets in R3–R4.
  Evidence: focused + full suite.
- **R7 — Post-conditions**: `rg -n "template_preview"
apps/pdf_forms` shows route + view + admin + template +
  widget + tests; `rg -n "pdf_file\.url" apps/pdf_forms`
  returns no user-facing link (storage-level `.url` in
  non-served contexts must be justified); the rendered
  change form contains no raw `/media/` link.

## Expected blast radius

Expected surfaces: `apps/pdf_forms/{views/base_views.py,urls.py,admin.py}`
(+ a small widget module if not inlined in admin),
`form_template_list.html`, the new test module. Sensitive
surfaces that must not change (escalate first): models,
migrations, `permissions.py` helpers, `PDFFormOverlay`,
submission/download flows, the obsolete sibling `views.py`,
any other app. Extra files need justification in the report.

## Failing-before plan

Reproduce BEFORE implementing (record outputs):

- from a Django shell, reverse
  `pdf_forms:template_preview` with a uuid kwarg →
  expected `NoReverseMatch`;
- `GET /pdf-forms/template/<uuid>/preview/` as staff →
  expected 404 (no route).

## Implementation constraints

- Gate with the EXISTING `check_pdf_form_template_access`
  helper — do not invent a new permission rule.
- Inline disposition (preview), private cache; filenames
  from the stored file, never from user input.
- No commits/pushes; no dependency installs; no new deps;
  no migrations; do not update `tasks.md`.

## Validation

- Focused: `./scripts/test.sh apps.pdf_forms` — green.
- Project gates: full suite (`./scripts/test.sh`) shows no
  NEW failures vs the pre-change baseline (record both);
  `ruff check` on changed `.py` files — zero new findings.

## Acceptance criteria

- [ ] AC1: preview route resolves (R2).
- [ ] AC2: authenticated GET returns the PDF inline with
      correct headers + identical bytes, incl. inactive
      templates and `DEBUG=False` (test-asserted).
- [ ] AC3: anonymous GET redirects to login (test-asserted).
- [ ] AC4: unknown pk and missing file both 404
      (test-asserted).
- [ ] AC5: admin + list + widget link to the preview route,
      no raw media URL remains in these surfaces
      (test-asserted).
- [ ] AC6: focused suite green; full suite no-new-failures;
      ruff zero new findings.
- [ ] AC7: diff limited to expected blast radius (extras
      justified).

## Escalation conditions

Stop and return `BLOCKED_NEEDS_DECISION` with evidence if:
the existing template-access helper cannot gate the view;
`FileResponse` streaming conflicts with an existing
middleware/security rule; blast radius must expand
materially.

## Evidence report

Report: status, R1–R7 → evidence, failing-before +
passing-after, commands + exit codes, `git diff --stat`,
deviations, risks. End with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
