# Design: Duplicate Outpatient Prescription

## Context

`OutpatientPrescription` (header) + `PrescriptionItem` rows
(`apps/outpatientprescriptions/models.py`). Creation uses a main form
plus an item formset with AJAX template support
(`OutpatientPrescriptionCreateView`). The project already duplicates
`DailyNote`, `HistoryAndPhysical` and `SimpleNote` via
`*DuplicateView(CreateView)` that renders a pre-filled form.

## Decisions

### D1 — POST-only clone, no duplicate form template

Render-and-prefill (the DailyNote pattern) does not transfer to a
formset: injecting N item initial forms is fragile. The duplicate view
accepts only POST, clones server-side, and redirects (302) to the
copy's update view for adjustments. No `*_duplicate_form.html`.

### D2 — Clone contract

New `OutpatientPrescription`: same `patient`, copied `instructions`,
`prescription_date` = configured-local date (`timezone.localdate()`,
`America/Bahia` per `TIME_ZONE`; a UTC date near midnight can differ),
`status` = `"draft"`,
`event_datetime` = now, `created_by`/`updated_by` = acting user.
Only the listed header fields are copied; `event_type` and any derived
values are recomputed by the model, never copied.
Items: new rows copying `drug_name`, `presentation`,
`usage_instructions`, `quantity`, `order`, with
`source_template = None`. New PKs everywhere; source untouched.

### D3 — Permissions

`events.add_event` (a duplication creates a new event) plus
`can_access_patient` on the source prescription's patient. Same
predicate as creation. Non-GET methods other than POST are rejected.

### D4 — Redirect target is the copy's edit view

"Duplicate and edit": after cloning, 302 to
`outpatientprescription_update` of the copy, with a success message
naming the patient. Timeline redirect (the create-view behavior) is
not used here because the user must review the copy first.

### D5 — Button visibility

The detail view already requires patient access, so the "Duplicar"
button is additionally gated only on `perms.events.add_event`. It is
a small inline POST form with CSRF (same technique as the existing
delete form), never a GET link.

### D6 — No `usage_count` inflation

Consequence of D2 (`source_template = None` on clones):
duplication never touches `DrugTemplate.usage_count`. Covered by an
explicit test.

## Alternatives considered

- Pre-filled formset via `initial`: rejected (fragile with dynamic
  item rows and the `PrescriptionItemFormSetHelper` user-scoped
  formset).
- Cross-patient duplication: rejected (a prescription belongs to its
  patient; templates cover the cross-patient reuse case).
