# Design: Patient-map actions and truthful result context

## Context

The list change is archived under
`2026-11-17-simplify-patient-list-filter-actions`. Map behavior was explicitly
preserved there. The map now needs equivalent action clarity plus two map-only
presentation fixes accepted by the operator.

Existing seams are WardPatientMapView, the shared preference/parser services,
ward_tag_overlay, the full map template and its tree-only AJAX template.
The live dev cache may be expired because its generator was not run. This is
an accepted operational prerequisite, not a defect to repair in this change.

## D1. One map action bar, with explicit scopes

The map offers:

- `Aplicar filtros`: apply the visible draft by GET.
- `Limpar todos os filtros`: immediately clear map filter predicates.
- `Usar padrão de tags da especialidade`: immediately restore only tags/mode.

Restore appears only for manual tag state, a valid active specialty and a
configured saved preference or principal tag. Saved-empty is configured.
No specialty/default means no restore action. Initial automatic entry does
not show a redundant restore action.

Remove the old applied-clear link from the map selector, all applied badge
removal links and repeated recovery links. Search, ward, tag and origin badges
are informational. Filtered-empty recovery refers to the single action bar.

Keep the independent preference-save POST and its authorization unchanged.
Keep chip × and native deselection as draft editing; do not add a bulk-clear
control or change the shared JavaScript.

## D2. Applied URLs, native empty Apply and preserved eligibility

Clear-all starts from a fresh QueryDict with only `tag_filter=manual` and
`tag_mode=any`. It drops q, ward, tag aliases, show_empty_wards and other
old parameters. Thus search/ward/tags are empty, mode is ANY, empty wards are
hidden by the existing default, and defaults do not return on reload.
This does not mean all patients in the hospital: existing map eligibility
and requester-visible projection remain authoritative.

Restore uses the canonical effective-query helper with automatic selection:
drop tag parameters/page, preserve applied q/ward/show_empty_wards and discard
pending DOM edits. Revalidate the existing defaults on the next GET.
A later parameter-free entry still applies defaults normally.

The native Apply button submits `tag_filter=manual`, after the selector's
initial hidden origin. Empty native selection must not fall back to defaults.
Enhanced clean Apply remains the existing no-request operation.
GET actions never save/delete preferences or memberships.
Legacy scoped clear/removal URLs continue working even though UI duplicates
disappear.

Tree expansion/session state is not a filter predicate. Do not add tree-state
reset behavior to clear-all. Expand, collapse and refresh behavior is unchanged.

## D3. Distinguish origin, effective filters and patient narrowing

Use separate applied-state facts:

- Origin/context can be manual, saved, principal, initial or invalid.
- Effective map filters exist iff trimmed search, ward selection or effective
  selected tags actually constrain results.
- Patient-narrowing filters within a retained ward exist iff trimmed search
  or effective selected tags are present. Ward selection alone only chooses
  wards; it does not hide patients inside a displayed ward.

Manual-empty, matching mode without tags, preference-record existence,
option-search/historical lookup controls and show_empty_wards alone do not
make totals "resultado filtrado". Automatic effective tags do.
Keep manual-empty context visible without classifying it as a predicate.

Do not change numeric totals or matching. Only change the filtered-result
label in both full and AJAX totals. Pending edits never relabel applied results.

Preference wording follows the already resolved source/effective tags:
manual is personalized; saved, saved-empty and principal are distinct;
no default, invalid explicit input and unavailable subset/all remain truthful.
Keep existing generic errors and warnings. The existing typed
`preference_status` function may be reused read-only without moving/refactoring
the accepted list service.

## D4. Empty-state wording without extra patient counts

Keep the checkbox label `Mostrar alas vazias` and add its helper:

"Inclui alas sem pacientes correspondentes aos filtros atuais."

For a displayed ward with zero matching patients:

- With a patient-narrowing search/tag predicate:
  "Nenhum paciente corresponde aos filtros atuais nesta ala."
- Without that predicate:
  "Nenhum paciente internado nesta ala."

The first message is intentionally neutral: it is true for both a genuinely
empty ward and a ward emptied by filtering. Do not add unfiltered patient
counts, a cache-schema field or a second eligibility model merely to distinguish
those physical states.

For a valid available map result with effective filters, zero total patients,
show_empty_wards enabled and at least one ward still rendered, show one visible
notice before the tree:

"Nenhum paciente corresponde aos filtros atuais. As alas continuam visíveis
porque 'Mostrar alas vazias' está ativado."

This notice must remain visible without expanding each ward. It does not add
clear/restore controls. When no wards are rendered, retain one filtered-empty
explanation referring to the action bar instead of duplicating the notice.
An unfiltered empty map must not claim filters hid its patients.

Per-ward/global messages and total labels agree in both rendering variants.
The checkbox/helper remain in the full-page form; the AJAX fragment does not
duplicate filter controls. Invalid input remains an error,
not a successful empty search. Existing no-ward and unavailable/updating-cache
handling is left intact: do not use zero fallback totals as evidence of a
successful filtered-empty result.

## D5. Narrow orchestration and unchanged shared surfaces

Do not grow the 1,948-line legacy views.py. Add a small adapter subclassing
WardPatientMapView and wire only the existing named map route to it.
Inherit authentication, permission checks, cache/eligibility and AJAX routing.

The inherited context already contains resolved selection, specialty,
saved-preference presence and error/warning values. Adapt those values into a
typed service input; do not resolve preferences a second time or reconstruct
tag identities from raw parameters. Views perform transport/context shaping;
action visibility, URLs, state labels and presentation facts belong in the
map-owned service.

Add an explicit map-only selector opt-in, e.g. `map_filter_actions=True`.
Preserve `patient_list_actions=True` and the false/default branch for other
callers. Do not rename shared JS hooks or reuse list-owned template key names
for the map. No list service or report changes are planned. The operator's visual
homologation amendment additionally permits list-template layout alignment,
without altering list filtering or persistence.

Keep new test modules bounded. The 812-line ward-map test module and 419-line
selector test module need only obsolete-assertion updates; no new feature
matrix or broad refactor belongs there.

## D6. Verification and rollback

Use RED → GREEN → REFACTOR, then the focused command and browser matrix in
verification.md. A fresh, genuinely populated TestCase cache is required for
empty-state evidence. Do not repair or regenerate the shared dev cache.
Isolated test-database preview is acceptable and must be labelled accurately.

No source assets are planned; no build is needed for template/service changes.
If source assets become necessary, stop for scope approval and add the build.

Rollback redeploys the previous map route/adapter/templates and selector opt-in.
No clinical/preference data rollback is needed; no schema changes occur.
