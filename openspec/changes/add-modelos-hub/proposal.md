## Why

Users need a single, discoverable place to access and manage reusable templates (drug, prescription, and upcoming document templates) without cluttering the main navigation. Access should be limited to doctors/residents, consistent with clinical permissions.

## What Changes

- Add a "Modelos" hub page that lists available template categories and links to each feature
- Restrict all template-related pages (drug and prescription templates) to doctors/residents
- Update the main sidebar to link to the new hub instead of individual template lists

## Impact

- Affected specs: templates
- Affected code:
  - `apps/core/urls.py` / `apps/core/views.py` (new hub route/view)
  - `templates/core/` (hub template)
  - `apps/drugtemplates/views.py` (permission enforcement)
  - `apps/core/permissions/decorators.py` (doctor/resident guard)
  - `templates/base_app.html` (sidebar navigation update)
  - `apps/drugtemplates/tests/` and new hub view tests
