# Design: Patient-list filter action contract

## Context

See `proposal.md` and `specs/patient-tag-filtering/spec.md`.
Current list links share `clear_tags_querystring` in selector, summary and
empty recovery. "Limpar filtros" uses the parameter-free list URL, which invokes
`tag_preferences.resolve_request_state()` and reapplies defaults.
`reapply_tags_querystring` instead preserves applied non-tag parameters.

The selector and `patient-filter-form.js` are shared with the map. Reports
have their own selector template but consume shared selector events. Scope must
be opt-in, not a global reinterpretation of clear or default semantics.

## Decisions

### D1. One action bar and explicit scopes

| Action                               | Effect                | Timing        |
| ------------------------------------ | --------------------- | ------------- |
| Aplicar filtros                      | Apply visible draft   | Explicit GET  |
| Limpar todos os filtros              | Remove all predicates | Immediate GET |
| Usar padrão de tags da especialidade | Restore tags/mode     | Immediate GET |

Show specialty restore only for manual tag state with a valid active specialty
and a saved preference or configured principal tag. Saved-empty is a valid
default; no specialty or configured default means no restore action. The
clear-all action is not a preference deletion. Both immediate navigation actions
discard pending edits, as existing full-page patient navigation does.

Keep one action bar in the filter card. Remove list-only old applied-clear and
restore links from selector/summary/empty recovery; make all applied badges
read-only, including name/status badges. An empty result explains the mismatch
and refers to the action bar rather than duplicating controls. Preserve the
unfiltered-empty first-patient explanation and existing create authorization.

Do not add the optional bulk `Limpar seleção` control in this first delivery:
existing draft-chip × controls and native deselection already edit tags without
adding a fourth competing action. Individual removals still require Apply.

Keep the independent preference-save POST action and its current authorization.
Do not add an implicit save to any filtering or clearing interaction.

### D2. Encode genuine clear-all without changing default resolution

Build the list clear-all URL from a fresh QueryDict containing only
`tag_filter=manual` and `tag_mode=any`. Do not use the parameter-free list URL
or reuse `manual_empty_query()`, which intentionally preserves other predicates.
Drop q/status/admission, all tag forms, page and other old filter/option params.
Explicit manual-empty prevents immediate, refresh and pagination fallback.

Specialty restore continues using the existing canonical reapply helper: remove
manual tag state/page from the applied request while keeping applied q/status
and admission. Never construct either immediate link from unsaved DOM values.

Do not change `tag_filters` or `tag_preferences` parser/persistence semantics,
legacy bookmarked URLs or parameter-free initial entry. "All patients" always
means otherwise eligible patients under existing permission gates.

Apply remains the existing full-page GET for visible draft fields. A named
Apply submitter `tag_filter=manual` must support no-JS empty deselection even
when the initial hidden origin is automatic. Preserve clean enhanced Apply's
existing no-request behavior.

### D3. List-owned orchestration, shared behavior unchanged

Add `apps/patients/services/patient_list_filter_actions.py` for typed,
stateless list action URLs/visibility and preference-status presentation.
A small `views_patient_list_filters.py` adapter subclasses the existing
PatientListView and adds only this context after super().get_context_data().
Point the existing named list route to the adapter; inherit query, permission,
login and pagination behavior unchanged. No new public URL is introduced.
This leaves the 1,948-line legacy views.py untouched and avoids growing it or
inventing a global context processor. Business rules remain in the service.

Patient list explicitly passes `patient_list_actions=True` through
`components/_tag_filter.html` to the shared selector. The default false branch
must render map controls exactly as before. Under the flag, suppress the old
`data-tag-clear` link; add no replacement local-clear button. Reports templates
and lookup responses are not modified.

No new JS module, Webpack wiring or shared-JS edit is needed. Keep the existing
`tag-selector.js` and `patient-filter-form.js` behavior: × removes only a
selected draft identity and updates the dirty state; it does not apply patient
predicates or save preferences. Native fallback remains usable. Do not call a
silent programmatic selection setter as a substitute for existing user removal.

### D4. Label what is actually applied

The preference panel must distinguish saved settings from effective use.
Use the resolved applied selection source and effective tags:

- Manual: identify personalized filters; a stored preference is not "in use".
- Saved: identify the applied saved default; saved-empty means no tag predicate.
- Principal: identify the specialty's initial default.
- Initial/no default: indicate no automatic tag predicate.
- Invalid explicit input: retain the existing generic validation error, never
  claim a successful unfiltered search.
- Unavailable automatic defaults: retain generic warnings and state that only
  the valid subset, or no tag predicate, is effective.

Draft edits do not relabel the currently displayed results. The normal dirty
indicator communicates pending differences. No changes to the account preference
save endpoint or repair of unrelated preference-save behavior are in scope.

### D5. Validation and compatibility

`verification.md` defines required profile fixtures and runtime proof. Saved
default tags must be present in the principal browser case; a blank-profile
preview alone cannot catch the reset/default confusion.

Keep new feature tests in a bounded module. Existing oversized test modules may
need only minimal obsolete-assertion updates, not new feature logic; record their
baseline and defer a comprehensive split to a separately approved change.

Regression-check the map's existing links, labels, draft handling and JS loading,
plus both report surfaces. Keep catalogue identity, lifecycle/visibility,
lookup timing, result eligibility and matching untouched. No schema change.

## Rollback

Redeploy prior list templates/helper/asset wiring and corresponding built assets.
No data rollback is needed because these interactions must not change stored
preferences or patient data. Do not edit old archived changes.

## Planning Status

One vertical slice is sufficient: list action semantics, UI and their proof land
together. Implementation requires operator approval. Live fixture provisioning
and checkout/schema identity remain separate operational prerequisites.
