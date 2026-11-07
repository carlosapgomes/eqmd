# Proposal: serve-protected-media

## Why

In production (`DEBUG=False` behind the `eon` nginx frontend),
every raw `/media/...` link returns 404 even though the files
exist on the `eqmd_media` volume. Root cause, verified read-only
on `eon` (Nov 2026):

- `config/urls.py` only registers Django's media route under
  `if settings.DEBUG`, so production has no `/media/` route.
- The frontend nginx explicitly proxies `/media/` to Django
  (`deploy/eon/frontend/nginx.conf`: "Media is
  authorization-protected in Django: never serve from disk").
- Result: `/media/...` → proxy → Django 404.

This breaks three user-facing surfaces that link `FileField.url`
directly:

1. `pdf_forms` — "View PDF" in `PDFFormTemplateAdmin` and the
   "Ver PDF" button in `form_template_list.html` (the reported
   issue; PDF _generation_ keeps working because it reads from
   disk).
2. `consentforms` — signed-scan attachments in
   `consentform_detail.html` / `consentform_update_form.html`.
3. `mediafiles` — admin thumbnail previews (`MediaFileAdmin`,
   `PhotoAdmin`, photo-series inline).

## What Changes

- Add an authenticated `PDFFormTemplate` preview view
  (`pdf-forms/template/<uuid:pk>/preview/`, inline PDF) gated by
  the existing template-access rule, and point the admin +
  list links at it (slice 001).
- Add an authenticated `ConsentAttachment` serve view
  (`attachments/<uuid:pk>/serve/`, inline with stored MIME) gated
  by `events.view_event` + `can_access_patient` over the
  permitted-parent queryset, and point the detail/update
  templates at it (slice 002).
- Repair the `mediafiles` admin previews around the current
  FilePond models (`get_thumbnail_url()` → tested
  `serve_thumbnail` route) with minimal stale-ref repair so
  the pages render (slice 003, no new views).
- Route the admin change-form file-widget links for PDF
  templates and consent attachments through the same
  endpoints (slices 001–002; the default widget would
  otherwise keep emitting raw media URLs).

## Non-goals

- Nginx changes (no `/media/` alias — that would expose patient
  photos/videos unauthenticated).
- Touching `DEBUG`-dependent `static()` wiring, upload paths,
  storage backends, or existing permission helpers.
- A generic authenticated `/media/` catch-all (permission
  semantics differ per domain; see design D1).
- Prod → dev media import (explicitly deferred by the requester;
  separate future task).
- `MediaFileAdmin` legacy previews and the `MediaFile.file`
  widget: surviving rows are event-orphans unresolvable by
  any patient-checked view; re-linking is a data-model
  repair needing its own change (design D4).
- New dependencies, migrations, or admin visual redesign.
