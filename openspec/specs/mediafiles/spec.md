# mediafiles Specification

## Purpose

Secure upload, storage, and role-gated serving of patient
photos, photo series, and video clips (FilePond-based),
including admin previews.

## Requirements

### Requirement: Admin previews use FilePond thumbnail URLs

The system SHALL render `Photo` and photo-series admin
thumbnail previews through the models' `get_thumbnail_url()`
(the tested `mediafiles:serve_thumbnail` route) instead of
stale `media_file` dereferences, so the pages render and
previews work in production (`DEBUG=False`).

(`MediaFileAdmin` legacy previews are explicitly deferred,
design D4: surviving rows are event-orphans.)

#### Scenario: Photo changelist preview uses the model URL

- **WHEN** staff opens the Photo changelist for a photo
  with a thumbnail
- **THEN** the preview `<img>` points to the photo's
  `get_thumbnail_url()`

#### Scenario: Photo change page preview uses the model URL

- **WHEN** staff opens a Photo change page for a photo
  with a thumbnail
- **THEN** the large preview `<img>` points to the photo's
  `get_thumbnail_url()`

#### Scenario: Photo-series inline preview uses the model URL

- **WHEN** staff opens a PhotoSeries change page with
  files that have thumbnails
- **THEN** each inline preview `<img>` points to its
  file's `get_thumbnail_url()`

#### Scenario: Missing thumbnail reference renders a placeholder

- **WHEN** the photo or series file has no `file_id` or
  `thumbnail_path`
- **THEN** the admin renders the existing "No thumbnail"
  placeholder instead of an image URL
