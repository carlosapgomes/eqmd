# Proposal: Simplify patient-map filter actions

## Why

The patient list now distinguishes applying a draft, clearing all filters and
restoring specialty tags. The ward map still repeats clear/restore links,
labels automatic-default reentry as "Limpar filtros" and claims saved
preferences are in use during manual filtering.

The map also confuses an empty ward with a ward without matching patients.
Its "resultado filtrado" label treats manual origin as an effective predicate.

## What Changes

- Give the map one action bar matching the accepted patient-list vocabulary.
- Make applied summaries informational and keep draft-chip removal local.
- Preserve applied search, ward and empty-ward visibility when restoring tags.
- Ensure native empty Apply explicitly suppresses automatic defaults.
- Derive preference descriptions and filtered-total labels from applied state.
- Explain empty-ward visibility and distinguish no matches from no inpatients,
  consistently in the full page and AJAX tree fragment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `patient-tag-filtering`: map action semantics, truthful context/totals and
  filter-aware empty-state wording; preserve existing patient-list behavior.

## Impact

Map presentation, a narrow inherited view adapter, a typed map-owned service
and targeted tests. The shared tag selector gains a map-only opt-in. No new
endpoint, permission, dependency, schema or preference-persistence change.

## Non-Goals

Cache generation, refresh scheduling, TTL/fallback repair, cache population in
the shared dev stack, synchronous cache rebuilding, numeric filtering changes,
ward/patient eligibility changes and redesign of tree controls. Reports and the
accepted patient-list UX remain unchanged. No bulk "Limpar seleção" is added.

## Accepted Visual Homologation Amendment

The operator additionally approved matching left-aligned list/map action bars,
a separate bordered map-display section and an independent preference card.
This is a layout-only exception to the original patient-list UX exclusion;
filter semantics, preference persistence and tree-control behavior stay intact.
The amendment is recorded in the design, slice and delta specification.

## Delivery

Planning only: one vertical slice, PMFA-S1. Implementation requires subsequent
operator approval. This proposal does not authorize shared fixtures, generator
execution, deployment, Git commits, merge or archive.
