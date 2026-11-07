# Slice 002 — Consent attachment serving (authenticated)

## Identity

- Slice: `slice-002-consent-attachment-serve`
- Change: `serve-protected-media`
- Tasks: `tasks.md` items 2.1–2.4 (Contract: this file)

## Objective

Serve consent-form scan attachments through an
authenticated view enforcing patient access, and point the
detail/update templates at it instead of raw `/media/...`
URLs (design D3).

## Read first

- `AGENTS.md`
- `openspec/changes/serve-protected-media/proposal.md`
- `openspec/changes/serve-protected-media/design.md` (D1, D3, D5)
- `openspec/changes/serve-protected-media/specs/consent-forms/spec.md`
  (scenarios are the behavioral contract)
- `apps/consentforms/views.py` (`visible_consent_forms()`
  permitted-parent queryset, `ConsentFormAttachmentsZipView`
  permission pattern, `ConsentAttachmentDeleteView` lookup
  pattern)
- `apps/consentforms/urls.py` (sibling `consentattachment_*`
  routes + `app_name`)
- `apps/consentforms/models.py` (`ConsentAttachment` fields:
  `file`, `original_filename`, `mime_type`)
- `apps/consentforms/templates/consentforms/consentform_detail.html`
  and `consentform_update_form.html` (attachment links/imgs)
- `apps/consentforms/admin.py` (attachment inline +
  `ConsentAttachmentAdmin` file widgets)

## Requirements

- **R1 — View**: add `ConsentAttachmentServeView`
  (`LoginRequiredMixin`, `PermissionRequiredMixin`, `View`)
  with `permission_required = "events.view_event"`: resolve
  the attachment via `get_object_or_404` constrained to
  `consent_form__in=visible_consent_forms()` (bot-draft
  and soft-deleted parents → 404, D3); raise
  `PermissionDenied` when `can_access_patient(request.user,
attachment.consent_form.patient)` fails (same message
  pattern as the zip view); return
  `FileResponse(attachment.file.open("rb"),
content_type=attachment.mime_type or fallback,
filename=attachment.original_filename,
as_attachment=False)` (fallback: guess from extension,
  then `application/octet-stream`); missing file on disk →
  404 without filesystem paths. Permission checks run
  BEFORE opening the file. Evidence: focused tests.
- **R2 — Route**: add to `apps/consentforms/urls.py`
  `path('attachments/<uuid:pk>/serve/',
views.ConsentAttachmentServeView.as_view(),
name='consentattachment_serve')`. Evidence: reverse
  resolves.
- **R3 — Templates**: in `consentform_detail.html` and
  `consentform_update_form.html`, attachment `<a href>`
  and `<img src>` use
  `{% url 'consentforms:consentattachment_serve'
attachment.pk %}` instead of `attachment.file.url`.
  Evidence: template link-target tests.
- **R4 — Admin widgets**: `ClearableFileInput` subclasses
  (or one shared with the slice-001 pattern) routing the
  attachment-inline and `ConsentAttachmentAdmin`
  existing-file links to the serve route via
  `value.instance.pk` (D3). Evidence: rendered-admin test.
- **R5 — Tests**: new or extended
  `apps/consentforms/tests/test_attachment_serve_view.py`
  covering at least: 200 + inline headers + streamed bytes
  equal to the stored file for an authorized user; one test
  under `override_settings(DEBUG=False)` asserting 200
  (prod-mode proof); `Cache-Control: private` asserted;
  403 with `can_access_patient` mocked to `False`
  (it grants every authenticated user unmocked);
  quote/Unicode filenames served safely;
  anonymous redirect; denial without `events.view_event`;
  BOTH MIME-fallback branches (extension guess +
  octet-stream); human-draft attachment 200 vs bot-draft
  and soft-deleted-parent 404; 404 unknown pk; 404 missing
  file on disk; detail/update pages render the serve links
  (and no raw media URL); admin inline renders the serve
  link. Storage writes must use the test media root
  (`override_settings` per existing consentforms test
  patterns).
- **R6 — No regressions**: zip download, delete flow,
  create/update/detail/PDF views, model immutability
  untouched. Evidence: focused + full suite.
- **R7 — Post-conditions**: `rg -n "consentattachment_serve"
apps/consentforms` shows route + view + templates + admin +
  tests; `rg -n "attachment\.file\.url"
apps/consentforms/templates` returns nothing; the rendered
  admin inline contains no raw `/media/` link.

## Expected blast radius

Expected surfaces: `apps/consentforms/{views.py,urls.py,admin.py}`
(+ a small widget module if not inlined in admin),
the two templates, the new test module. Sensitive
surfaces that must not change (escalate first): models,
migrations, `render_template`/renderer, zip/delete flows,
any other app. Extra files need justification.

## Failing-before plan

Reproduce BEFORE implementing (record outputs):

- from a Django shell, reverse
  `consentforms:consentattachment_serve` with a uuid kwarg
  → expected `NoReverseMatch`;
- `GET /consentforms/attachments/<uuid>/serve/` as staff
  → expected 404 (no route).

## Implementation constraints

- Mirror the zip view's permission contract exactly
  (`events.view_event` + `can_access_patient`); do not
  weaken or strengthen it.
- Inline disposition (preview), private cache; served
  filename from `original_filename` only.
- No commits/pushes; no dependency installs; no new deps;
  no migrations; do not update `tasks.md`.

## Validation

- Focused: `./scripts/test.sh apps.consentforms` — green.
- Project gates: full suite (`./scripts/test.sh`) shows no
  NEW failures vs the pre-change baseline (record both);
  `ruff check` on changed `.py` files — zero new findings.

## Acceptance criteria

- [ ] AC1: serve route resolves (R2).
- [ ] AC2: authorized GET returns bytes inline with stored
      MIME + original filename, incl. `DEBUG=False`
      (test-asserted).
- [ ] AC3: 403 with mocked patient denial; anonymous
      redirect; denial without `events.view_event`
      (test-asserted).
- [ ] AC4: both MIME fallbacks + unknown pk + missing file
      404s + parent-visibility matrix (test-asserted).
- [ ] AC5: detail/update pages + admin widgets link the
      serve route, no raw media URL remains
      (test-asserted).
- [ ] AC6: focused suite green; full suite no-new-failures;
      ruff zero new findings.
- [ ] AC7: diff limited to expected blast radius (extras
      justified).

## Escalation conditions

Stop and return `BLOCKED_NEEDS_DECISION` with evidence if:
the zip-view permission pattern cannot be reused as
specified; stored MIME/filenames prove untrustworthy for
headers beyond the documented fallback; blast radius must
expand materially.

## Evidence report

Report: status, R1–R7 → evidence, failing-before +
passing-after, commands + exit codes, `git diff --stat`,
deviations, risks. End with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
