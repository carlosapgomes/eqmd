# Design: serve-protected-media

## Context

Production serving chain for `/media/...` (verified on `eon`):

1. Edge (Caddy) → frontend nginx → `proxy_pass` to Django.
2. Django with `DEBUG=False` has no `/media/` route
   (`config/urls.py` guards `static()` with `settings.DEBUG`).
3. Any `{{ file.url }}` / `obj.file.url` link therefore 404s.

Unaffected patterns (already authenticated, keep as-is):

- `mediafiles` end-user surfaces use
  `mediafiles:serve_file` / `mediafiles:serve_thumbnail`
  (FilePond-native, patient-access checked).
- PDF _generation_ reads `pdf_file.path` from disk.
- `ConsentFormAttachmentsZipView` streams attachments with
  `events.view_event` + `can_access_patient`.

## Decision D1 — Per-domain views, no generic catch-all

Permission semantics differ per domain (blank hospital
templates: any authenticated user; consent scans and
thumbnails: patient access), so each domain gets (or reuses)
its own serve view next to its existing permission logic.
A generic authenticated `/media/<path>` view would need a
path→object→permission dispatcher — more code, murkier audit,
no reuse gain.

## Decision D2 — PDF template preview (slice 001)

New `PDFFormTemplatePreviewView(LoginRequiredMixin, View)` in
`apps/pdf_forms/views/base_views.py` — the `views/` package
shadows sibling `views.py` (`views/__init__.py` star-imports
`base_views`, no `__all__`, so a new public class is
auto-exported to the urlconf; `views.py` is obsolete and
stays untouched):

- Route `template/<uuid:pk>/preview/`, name `template_preview`,
  on the existing `pdf_forms` urlconf.
- Gate: `check_pdf_form_template_access(request.user)` —
  the same rule as the template list (any authenticated
  user; blank templates carry no patient data).
- Serves `FileResponse(template.pdf_file.open("rb"),
content_type="application/pdf", filename=<basename>,
as_attachment=False)` (D5 for the filename rule).
- Missing file on disk → 404 (same UX as today's dev 404,
  but explicit and test-covered).
- `PDFFormTemplateAdmin.pdf_preview` and
  `form_template_list.html` "Ver PDF" reverse this route
  instead of `template.pdf_file.url`.
- The admin change-form `pdf_file` widget link is routed
  too: a `ClearableFileInput` subclass resolving
  `value.instance.pk` to the preview route (the default
  widget would otherwise keep emitting a raw media link).
- No `is_active` filter in the view: the list already filters
  actives; staff previewing an inactive template from the
  admin must still work (test-covered).

## Decision D3 — Consent attachment serve (slice 002)

New `ConsentAttachmentServeView(LoginRequiredMixin,
PermissionRequiredMixin, View)` in
`apps/consentforms/views.py`, mirroring
`ConsentFormAttachmentsZipView`:

- Route `attachments/<uuid:pk>/serve/`, name
  `consentattachment_serve`, on the existing `consentforms`
  urlconf (sibling of `consentattachment_delete`).
- Lookup: attachments are filtered through the permitted-parent
  queryset — `ConsentAttachment.objects.filter(
consent_form__in=visible_consent_forms())` — so scans of
  soft-deleted parents and bot drafts are 404, exactly like
  their parent pages. Visibility follows detail/update
  (definitive + human drafts), NOT the zip view's stricter
  definitive-only policy: the serve links render on those
  pages, so a stricter rule would break images on human-draft
  pages.
- Gate: `permission_required = "events.view_event"` plus
  `can_access_patient(request.user,
attachment.consent_form.patient)` → `PermissionDenied`
  otherwise (same message pattern as the zip view).
  Permission checks run BEFORE opening the file.
- Serves `FileResponse(attachment.file.open("rb"),
content_type=attachment.mime_type or fallback by
extension, filename=attachment.original_filename,
as_attachment=False)` so images render in-page and PDFs
  open in the viewer.
- Missing file on disk → 404 without exposing filesystem
  paths (same contract as D2).
- `consentform_detail.html` and
  `consentform_update_form.html` use the new route for both
  the `<a href>` and the `<img src>`.
- The admin `file` widget links (attachment inline +
  `ConsentAttachmentAdmin` change form) are routed through
  the same `ClearableFileInput`-subclass pattern as D2.
- Zip download, delete flow, upload paths untouched.

## Decision D4 — mediafiles admin thumbnails (slice 003)

The plan first assumed `Photo`/`PhotoSeriesFile` link to
`MediaFile`; they do not — both are FilePond-native
(`file_id` + `thumbnail_path`) and expose
`get_thumbnail_url()` reversing the tested
`mediafiles:serve_thumbnail` route. The `PhotoAdmin`
`media_file` references (previews, `search_fields`,
`fieldsets`, `select_related`) are stale post-migration
leftovers. Slice 003 therefore repairs around CURRENT
models, with no new views:

- `PhotoAdmin.thumbnail_preview` and
  `thumbnail_preview_large` render
  `obj.get_thumbnail_url()` (None → existing placeholder).
- The photo-series file inline renders
  `obj.get_thumbnail_url()` (None → placeholder), but the
  caller MUST validate both `file_id` and `thumbnail_path`
  BEFORE calling the getter: the series model's getter
  checks only `thumbnail_path` and would raise
  `NoReverseMatch` on a missing id (models stay untouched).
- Minimal stale-ref repair so these admin pages render at
  all: drop/replace `media_file` lookups in `PhotoAdmin`
  (`search_fields`, `fieldsets`, queryset
  `select_related`), the series inline `fields` list, and
  `PhotoSeriesAdmin.get_queryset()`'s invalid
  `photoseriesfile_set__media_file` prefetch, plus any
  file-info display helpers that dereference it (worker
  verifies each site; keep the repair to what rendering
  needs).
- `MediaFileAdmin` previews are explicitly DEFERRED, not
  fixed here: surviving `MediaFile` rows are orphans
  (nothing links them to an event anymore), so
  `secure_thumbnail`'s patient lookup cannot resolve them
  and any reversed URL 404s. Re-linking or a dedicated
  legacy serve is a data-model repair, not a serving fix
  — recorded as follow-up, out of this change.

Placeholder semantics: existing guards cover EMPTY
references only (no `file_id`/`thumbnail_path`); a
physically missing file still yields a broken image —
accepted, same as the end-user surfaces.

## Decision D5 — Response conventions

All served responses: `FileResponse`, `Content-Disposition:
inline` (preview semantics — the zip/download flows keep
`attachment`), `Cache-Control: private` (never public;
patient-adjacent bytes must not sit in shared caches),
`X-Content-Type-Options: nosniff` where the pattern
already sets it. Filenames are passed via
`FileResponse(..., filename=..., as_attachment=False)`
(Django encodes quotes/Unicode safely) — never by manual
`Content-Disposition` string interpolation. Name source per
domain: consent attachments use stored `original_filename`;
`PDFFormTemplate` keeps no original name, so the preview
uses `basename(template.pdf_file.name)` (acknowledged: the
pre-upload name is not retained; no migration just for
this).

## Decision D6 — What stays raw

After this change no IN-SCOPE surface links raw
`/media/...`: explicit template/admin links AND the admin
change-form file widgets for PDF templates and consent
attachments are routed (slices 001–002, rendered-admin
regression tests). Out of scope and unchanged: the
`DEBUG`-only `static()` wiring (dev convenience), the
`MediaFileAdmin` legacy previews + `MediaFile.file` widget
(D4 deferral), and unused `mediafiles_tags` raw-URL helpers
(no production template invokes them). Any future
`FileField` MUST ship with an authenticated serve view
or reuse an existing one — enforced by review, not code.

## Risks / Trade-offs

- Staff viewing the `mediafiles` admin without patient
  access to a given event will see a broken thumbnail
  image (403/404 from the secure view) instead of the
  image. Same behavior as the secure end-user surfaces;
  accepted — leaking thumbnails would be worse.
- Preview views stream from disk per request (no
  `X-Accel-Redirect` yet). Traffic is staff-only and low;
  nginx offload is a future optimization, not this change.
- `mime_type` on old attachments may be empty (it was
  captured from `content_type` at upload); the view falls
  back to extension-based guessing, then
  `application/octet-stream` (both branches test-covered).
- `can_access_patient` currently grants every authenticated
  user, so patient-denial tests MUST mock it to `False`
  (anonymous-redirect tests need no mock).
- Slice HARNESS note: at least one test per new view runs
  under `override_settings(DEBUG=False)` asserting 200 —
  proving the fix does not depend on the dev-only media
  route (the production-mode regression this change exists
  for).
- Follow-up (out of this change): legacy `MediaFile` rows
  are event-orphans; re-link or dedicated legacy serving
  needs its own change once the data story is decided.
