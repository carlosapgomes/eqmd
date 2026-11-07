# Tasks: serve-protected-media

## 1. PDF template preview (authenticated)

Contract: `slices/slice-001-pdf-template-preview.md`

- [x] 1.1 Add `PDFFormTemplatePreviewView` in
      `views/base_views.py`, with the `template_preview`
      route (D2 gate, inline `FileResponse`, 404 when the
      file is missing).
- [x] 1.2 Point `PDFFormTemplateAdmin.pdf_preview`, the
      template-list "Ver PDF" button, and the admin
      change-form file widget at the preview route.
- [x] 1.3 Add regression tests: 200 + headers + streamed
      bytes for an authenticated user (incl. inactive
      template and `DEBUG=False`), private cache headers,
      login redirect for anonymous, 404 unknown id, 404
      missing file, quote/Unicode filenames, admin/list/
      widget link targets.
- [x] 1.4 Focused suite green (`apps.pdf_forms`); no new
      failures in the full suite; `ruff check` zero new
      findings on changed files.

## 2. Consent attachment serving (authenticated)

Contract: `slices/slice-002-consent-attachment-serve.md`

- [x] 2.1 Add `ConsentAttachmentServeView` (permitted-parent
      lookup + zip-view permission pattern + inline
      `FileResponse` with stored MIME/filename + 404 on
      missing file) with the `consentattachment_serve`
      route.
- [x] 2.2 Point the consent detail/update attachment links,
      inline images, and admin file widgets at the serve
      route.
- [x] 2.3 Add regression tests: 200 + headers + streamed
      bytes (incl. `DEBUG=False`), private cache headers,
      403 with mocked patient denial, quote/Unicode
      filenames, anonymous redirect,
      both MIME-fallback branches, human-draft 200 vs
      bot-draft/deleted 404, 404 unknown id, 404 missing
      file, template/widget link targets.
- [x] 2.4 Focused suite green (`apps.consentforms`); no new
      failures in the full suite; `ruff check` zero new
      findings on changed files.

## 3. mediafiles admin thumbnails via secure view

Contract: `slices/slice-003-mediafiles-admin-thumbnails.md`

- [x] 3.1 Render `PhotoAdmin` (both sizes) and photo-series
      inline previews via `get_thumbnail_url()`, with
      minimal stale `media_file`-ref repair so the pages
      render; `MediaFileAdmin` explicitly untouched (D4
      deferral).
- [x] 3.2 Add/extend admin preview tests asserting the
      model URLs (fetch the emitted `<img src>`), the
      empty-reference placeholders, and that the admin
      pages render.
- [x] 3.3 Focused suite green (`apps.mediafiles`); no new
      failures in the full suite; `ruff check` zero new
      findings on changed files.
