# Proposal: Improve tag filter discovery UX

## Why

Patient list, patient map and report-template discovery share tag-filtering
concepts but do not present a consistent interaction model. In particular,
users cannot reliably distinguish pending controls from the filter that
produced the current results. Long option lists displace the Apply action,
report models use a native multi-select, filtered-empty states suggest creating
records, and several labels/actions are ambiguous on desktop and mobile.

The operator approved a consistent explicit policy: ordinary filter edits stay
pending until the user chooses **Aplicar filtros**, with a visible indication
of unapplied changes.

## What Changes

- Separate the last-applied predicate, the current draft controls and the
  persisted specialty preference. Show when the first two differ.
- Apply the complete visible predicate only through an explicit, text-labelled
  **Aplicar filtros** action. Typing in patient/model name fields, changing
  tag selections or matching mode, and toggling empty wards no longer updates
  result predicates implicitly.
- Keep clear/reapply, badge removal and pagination as deliberate shortcut or
  navigation actions. They use their named scope and the last-applied state;
  they must not silently commit unrelated pending edits.
- Clarify tag matching, historical choices and filter-origin wording, provide
  accessible names for removal controls and distinguish genuinely empty
  collections from collections emptied by active predicates.
- Keep the patient/map tag option list within a bounded, dismissible panel;
  preserve keyboard navigation, polite status announcements and selected-row
  state without moving the surrounding Apply action.
- Replace the report discovery native multi-select, with JavaScript
  enhancement, by the established searchable lookup and selected-chip model.
  Retain the native form as the no-JavaScript contract.
- Version result-state history deliberately in enhanced report discovery:
  explicit applications may push history entries, option-only changes replace
  the current entry, and browser Back/Forward restores matching results.
- Carry the same discovery behavior to report creation only after catalogue
  discovery is accepted, preserving all in-progress clinical fields and the
  selected model throughout filter interactions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `patient-tag-filtering`: explicit draft-versus-applied behavior, bounded
  selector interaction, accessible controls and filtered-empty recovery on
  patient list and ward map.
- `reports`: explicit name/tag application on both discovery surfaces,
  searchable tag selection, restorable browser history and filtered-empty
  catalogue recovery while retaining existing report-creation guarantees.

## Impact

- UI: patient list/map templates, report-template catalogue and report-create
  discovery templates; scoped filter presentation styles.
- Frontend: reusable tag-selector behavior, patient/map filter-form state and
  report discovery transport/history. Source assets are built by existing
  Webpack configuration; generated assets are not edited directly.
- Backend: minimal context/URL support and a reports-owned read-only tag lookup
  that reuses existing visibility-checked catalogue query services. Existing
  patient lookup authorization remains unchanged.
- Compatibility: existing GET parameter names, repeated tags, ANY/ALL values,
  manual-empty marker, preference precedence and result eligibility remain.
- Persistence: no schema, migration, data backfill or new preference behavior.
- Dependencies: no new frontend package, Python package or browser harness.
- Verification: focused Django tests, frontend build, desktop/mobile browser
  evidence and report-creation content-preservation proof are required.

## Non-Goals

No changes to tag matching results, patient/template access, catalogue
authority, restricted metadata projection, report rendering, PDF output,
clinical submission rules or template application semantics. No redesign of
preference precedence, preference-storage UI, global clear-all behavior,
responsive result tables or unrelated badges outside filter surfaces.

## Review Clarifications

- Searching within the tag-option lookup does **not** apply a patient/model
  filter and does not by itself make that host filter dirty.
- Historical-option presentation can refresh immediately because it is not a
  result predicate; it must not commit pending tag or name edits.
- Enhanced Apply may be available while unchanged, but a no-op application
  must not create a misleading dirty state or an unnecessary history entry.
- In asynchronous report discovery, a failed refresh leaves the last-applied
  results visible, preserves the draft and keeps the dirty/error indication; it
  never claims successful empty or unfiltered results.
- Existing manual > saved > principal > none precedence and explicit saved
  empty behavior remain canonical. Structural preference simplification is a
  separate future product decision.

## Delivery Boundary

Planning only at change creation. Four sequential vertical slices deliver
language/recovery, stable patient/map selection, report-catalogue parity and
report-creation parity respectively. Every slice has independent RED, GREEN
and runtime evidence obligations; no slice authorizes implementation of the
next one, a migration, a commit or an archive.
