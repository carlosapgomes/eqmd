## Context

This initiative addresses two related UX problems in patient-centered screens:

1. Users need key patient identifiers and current care context visible without
   leaving the timeline or opening the full patient profile.
2. The desktop timeline spends a permanent column on filters that are only used
   in some visits, creating visual noise and reducing room for event cards.

The project already contains duplicated compact patient information markup in
multiple detail templates. Those blocks are visually similar but not canonical,
which increases maintenance cost and makes future UI changes inconsistent.

## Goals / Non-Goals

### Goals

- Establish one canonical reusable patient context component.
- Make core patient context visible in the timeline without navigating away.
- Roll the same context pattern into selected patient event detail pages.
- Move timeline filters to an on-demand interaction pattern in phase 2.
- Keep slices small, vertical, and verifiable with focused tests.

### Non-Goals

- Breadcrumb redesign or metadata enrichment.
- Data model changes for patients, admissions, or events.
- Permission changes.
- Broad CSS refactors outside the touched screens.

## Decisions

### Decision: use a shared template component partial

Create a reusable component partial in:

- `templates/components/_patient_context_summary.html`

Rationale:

- The coding standards direct reusable template fragments to
  `templates/components/`.
- The problem is present across multiple apps, so an app-local partial would
  not be an appropriate long-term home.
- A shared partial is the lowest-risk path before considering a custom template
  tag or more abstract rendering layer.

### Decision: define canonical compact fields and conditional admission fields

The compact summary should consistently prioritize the information users called
out as hard to access:

- patient name
- record number / prontuário
- age / idade
- status

When the patient has an active admission, the compact summary should also show:

- ward / ala or setor
- bed / leito

Rationale:

- Name, record number, age, and status provide the quickest orientation in the
  clinical workflow.
- Ward and bed are highly relevant during active admissions but add noise when
  there is no active inpatient context.
- These values are already available from the existing patient model/template
  context.

### Decision: expanded details are optional and on-demand

The same component should support an optional expanded section with additional
patient context, such as:

- birth date
- gender
- admission date
- admission duration / time admitted

Admission-specific extended fields should only be shown when the patient has an
active admission.

Rationale:

- This preserves quick scanning while still exposing richer context when
  needed.
- It aligns with the old system screenshot and with the current detail-page
  pattern of using collapsible patient context.
- Admission date and duration are useful follow-up details, but not essential
  for the always-visible compact row.

### Decision: active admission drives admission-specific field visibility

The component should use active admission state, not only the displayed status
label, to decide whether ward, bed, admission date, and admission duration are
shown.

Rationale:

- Admission-specific context is semantically tied to an active admission.
- This is more robust than relying on a single status label.
- It keeps status visible for all patients while avoiding accidental display of
  stale ward or bed data.

### Decision: consumer pages keep page-specific wrappers and metadata

The shared component owns only patient context markup. Each consuming page keeps
its own page-specific wrapper, title hierarchy, event timestamp, and actions.

Rationale:

- This keeps the component narrowly scoped.
- It reduces the risk of over-generalizing page-specific layout concerns.
- It allows adoption in small slices without large template rewrites.

### Decision: phase 2 uses offcanvas for timeline filters

The patient timeline should move desktop filtering from a fixed sticky sidebar
to an on-demand offcanvas panel. The trigger should remain visible near the
header and indicate when filters are active.

Rationale:

- Offcanvas preserves full filtering functionality while removing persistent
  visual noise.
- It works naturally across desktop and mobile.
- It frees horizontal space for event cards.

## Alternatives Considered

### Enrich breadcrumb with patient details

Rejected for now:

- Breadcrumbs are spread across many templates and apps.
- Breadcrumbs mix navigation with dense clinical context poorly.
- This would create a wider, more cross-cutting change before the reusable
  component exists.

### Keep per-page compact info blocks and manually improve each one

Rejected:

- Duplicates logic and markup.
- Increases future drift.
- Does not create a canonical patient context pattern.

### Collapse the existing desktop filter sidebar in-place

Rejected:

- It still reserves page structure and visual weight around the sidebar area.
- Offcanvas better matches the "used only sometimes" nature of filtering.

## Risks / Trade-offs

### Risk: markup-based tests become brittle

Mitigation:

- Prefer assertions on stable labels/text and expected controls.
- Keep tests focused on user-visible behavior, not exact DOM nesting.

### Risk: collapse/offcanvas IDs collide across pages

Mitigation:

- Pass explicit IDs from consuming templates when the expandable section is
  enabled.

### Risk: some patient data may be absent

Mitigation:

- The component should render a safe placeholder for missing record number.
- If an active admission exists but ward or bed is unavailable, the component
  should still render safely without breaking layout.
- If no active admission exists, ward and bed should not be shown in the
  compact row.

### Risk: detail pages may need minor wrapper adjustments

Mitigation:

- Adopt the component one page at a time.
- Keep page-specific wrappers intact and only replace the duplicated patient
  field block inside each page.

## Slice Strategy

### Phase 1 - Patient context component

1. Introduce the reusable component and adopt it in the patient timeline with
   the canonical compact fields plus conditional ward/bed display when an
   active admission exists.
2. Add the optional expanded details behavior in the timeline, including
   admission-specific extended data only when an active admission exists.
3. Adopt the component in `dailynote_detail`.
4. Adopt the component in `simplenote_detail`.
5. Adopt the component in `historyandphysical_detail`.

### Phase 2 - Timeline filters on demand

1. Introduce the offcanvas trigger shell and related tests.
2. Move the existing filter form into the offcanvas.
3. Remove the fixed desktop sidebar and widen the event area.
4. Add active-filter state to the trigger and preserve reset behavior.

## Testing Strategy

- Use focused template/view tests per slice.
- Prefer narrow verification targets, for example one dedicated test module per
  adopted screen.
- Keep TDD at the slice level:
  - RED: write failing assertions for the new UI behavior
  - GREEN: minimal template/component changes
  - CLEAN: keep component API narrow and markup reusable
  - VERIFY: run only the slice verification command
