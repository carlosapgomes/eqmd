# J5 — photo draft: upload, inline view, download denial, hard delete

Photos are the media half of the draft flow. A student uploads through FilePond,
the draft is viewable on screen, downloading is refused while it is a draft, and
deleting a never-finalized draft removes the row and the stored file.

## Sub-features

- Student upload path: `/mediafiles/photos/create/<patient-uuid>/` with a
  FilePond drop area (`input[name="filepond"]`), `description`, `caption`, and
  the hidden `upload_id` that FilePond fills after the server accepts the file.
- The file is posted to `/mediafiles/fp/process/` (django-drf-filepond) and
  stored under `MEDIA_ROOT/photos/<YYYY>/<MM>/originals/<file_id>.<ext>`.
- The timeline card is a draft card (badge + tint) and offers `Revisar`.
- The detail page renders the image inline (`img` with `naturalWidth > 0`) even
  though the download endpoint refuses drafts.
- Download of a draft returns `404`: `PhotoDownloadView` resolves through
  `downloadable_photos()` (`is_draft=False`).
- Hard delete: a never-finalized draft is removed (`delete_event_record`), the
  detail URL becomes `404`, and the stored file is gone from disk.

## How to get to it (user POV)

1. As a student open the timeline and choose
   **Criar Evento → Imagem** (or go to the create URL directly).
2. Drop or pick a JPEG/PNG/WebP up to 5 MB in the FilePond area, wait for the
   preview, add a description and caption, then press **Criar Foto**.
3. The timeline shows the draft photo card; open it to see the image inline and
   the record metadata.
4. The download button is present but the request is refused (`404`) — drafts
   are reviewed on screen only.
5. Delete the photo: the card's delete action opens the confirmation page, tick
   the confirmation checkbox, press **Excluir**.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run journey:j5
```

What the script does (`journey-j5-photo-draft.mjs`):

1. Generates a 10×10 PNG into the run's evidence dir
   (`fixtures/verify-photo.png`) — no binary fixture in the repository.
2. Uploads it with `setInputFiles` on `input[name="filepond"]` and waits until
   `input[name="upload_id"]` is non-empty (FilePond finished the server round
   trip).
3. Submits, asserts the timeline draft badge, then opens the detail page and
   asserts the inline image is complete with `naturalWidth > 0`.
4. Requests the download URL with the student session
   (`page.request.get`) and asserts `404`.
5. Probes storage while the draft exists: one `Photo` row, `is_draft=true`, one
   stored file path under `media/photos/...`.
6. Deletes through the UI, then asserts the timeline is empty, the detail URL is
   `404`, the row is gone, and the previously recorded file path no longer
   exists.

Evidence: `j5-photo-draft/` (`timeline-photo-draft.png`,
`photo-detail-inline.png`, `report.json`) and `db/before-j5-delete.json` /
`db/after-j5-delete.json` with the file-existence flags.

## Gotchas

- FilePond is loaded from `https://unpkg.com/...` by the template. Without
  outbound internet the drop area never initializes and `input[name="filepond"]`
  never appears — that is a hard failure of the journey, not a reason to skip
  it.
- FilePond rewrites the input: the original `class="filepond"` becomes
  `filepond--browser`, so select by `name`, not by class.
- Uploading is asynchronous. Submitting before `input[name="upload_id"]` is
  filled produces a form validation error (`Upload not found or expired`).
- Deleting needs the confirmation checkbox `#confirmDelete` (it enables
  `#deleteBtn`); clicking the disabled button times out.
- The download `404` comes from the queryset, not from a hidden link: the button
  is rendered, the response is `Http404`. Assert the status, not the button.
- The stored path uses the container's `MEDIA_ROOT` (`/app/media`), which is a
  different mount from the worktree's `media/` directory — always resolve it
  inside the container (`probe.py`), never on the host.
- Photo rows live behind `PhotoManager`, which does not exclude drafts or
  soft-deleted rows; the supervision filter is the explicit
  `visible_photos()`/`downloadable_photos()` helpers.
