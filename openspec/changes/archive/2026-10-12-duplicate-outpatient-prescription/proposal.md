# Proposal: Duplicate Outpatient Prescription

## Problem

Recurring outpatient prescriptions must be retyped item by item.
`PrescriptionTemplate` covers only standardized regimens saved as
templates; an actual previous prescription — with its adjusted doses
and free-text instructions — cannot be reused as a starting point.

## Goal

Allow an authorized user to duplicate a previous outpatient
prescription of the same patient into a new draft and land directly
on the edit view of the copy for adjustments ("duplicate and edit").

## Scope

- New `POST <uuid:pk>/duplicate/` action on `OutpatientPrescription`.
- Clone contract: same patient, copied `instructions`, today's
  `prescription_date`, status `draft`, items copied as new independent
  rows.
- "Duplicar" button on the prescription detail page.
- Source may be a draft or a finalized prescription; the copy is
  always a new draft.

## Non-goals

- No duplication across different patients.
- No "save as template" flow (templates already exist).
- No change to create/update/delete/print/PDF behavior.
- No new permission; no migration.

## Risks

- `PrescriptionItem.save()` increments `DrugTemplate.usage_count`
  when a new item carries `source_template`. Cloned items must not
  carry it, or duplication would inflate template statistics.
- The item formset makes pre-rendering N item forms fragile; the
  design avoids it with a POST-only clone plus redirect to edit.
