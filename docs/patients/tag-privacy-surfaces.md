# Tag privacy surfaces

Every tag surface reads through the requester-aware projections in
`apps/patients/services/tag_projection.py` (catalogue/associations) and
`apps/events/services/tag_audit_presentation.py` (historical actions); writes
and legacy classification stay in `apps/events/services/tag_audit.py`. Hiding
metadata in CSS or client-side code is not a privacy control: the server
payload is the contract.

## Visibility rule

Read visibility is decided per request from:

- the **current** catalogue row (`visibility`, `specialty`, `is_active`,
  `is_deleted`), and
- the **union of the actor's active team memberships** in active specialties
  (not only the selected current specialty).

Who may read what:

- anyone authenticated: public tags in any namespace;
- active team member: public tags plus the restricted tags of every own team;
- authorized catalogue administrator: every tag and every history detail.

Administrators are active Django-admin operators: superusers, or staff holding
the relevant `patients.*_allowedtag` permission. Staff status, leadership and
authorship alone grant no extra read visibility.

Nothing is cached across requests, so revocation and reclassification apply to
the very next response, including responses built from a shared cache payload.

## Patient readers

- `PatientListView` — list rows, tag selector, active-filter chip and the
  `?tag=` result set. Tests: `test_tag_visibility.PatientList*`.
- `PatientDetailView` — `tag_management.html` badges, counters and modals.
  Tests: `test_tag_visibility.PatientDetailAndApiReaderTests`.
- `PatientTagsAPIView` — JSON `current_tags` and `available_tags`. Tests:
  `test_tag_visibility...test_tag_api_*`.
- `PatientTagAddView` — JSON `tags` payload and message. Tests:
  `...TagMutationPayloadTests`.
- `PatientTagRemoveView` — JSON `tags` payload and message. Tests:
  `...test_remove_response_payload_is_projected_for_the_caller`.
- `PatientTagRemoveAllView` — JSON `tags` and `preserved`. Tests:
  `...test_bulk_remove_response_payload_*`.
- `WardDetailView` — ward patient table rows. Tests:
  `test_tag_visibility.WardReaderTests`.
- `WardPatientMapView` — full map HTML, AJAX tree partial,
  `data-patient-tags`, tag selector and `?tag=` filtering. Tests:
  `apps/core/tests/test_cache_tag_privacy.py`.
- `patient_tags` inclusion tag — `patients/tags/patient_tags.html`. Tests:
  `test_tag_audit_projection.PatientTagsInclusionTagTests`.
- `patient_tag_badge` partial — one badge with its remove control; exercised by
  the widget and detail readers.
- `tag_management_widget` — widget partial rendering `current_tags`; exercised
  by the detail reader.
- `get_available_tags_for_patient` — active, unassigned, readable catalogue;
  exercised by the tag API reader.
- `available_for_patient` — set subtraction over a caller-supplied queryset; it
  performs no catalogue query of its own.
- `apps/core/utils/cache.py` — shared ward-mapping payload reprojection. Tests:
  `apps/core/tests/test_cache_tag_privacy.py`.

Patient badges carry the association id, catalogue id, name, colour and
lifecycle label of **visible** associations only. A hidden association
contributes no row, no counter increment and no identifier.

## Historical event readers

- `PatientEventsTimelineView` — timeline cards, header badges, print DOM.
  Tests: `test_tag_audit_projection.TimelineReaderTests` and
  `TimelineHeaderTests`.
- `partials/event_card_base.html` — includes `event_card_tag_action.html` for
  tag audit events. Same tests.
- `patient_events_list` — table description column. Tests:
  `...test_patient_events_list_hides_restricted_metadata`.
- `user_events_list` — table description column. Tests:
  `...test_user_events_list_hides_restricted_metadata`.
- `event_api_detail` — JSON `description` and `tag_audit` payload. Tests:
  `...test_event_api_payload_is_projected`.
- `recent_events_widget` — widget excerpt. Tests:
  `...test_recent_events_widget_*`.
- `Event.get_excerpt` / `Event.get_display_description` — model seams used by
  every reader; they fail closed when no projection is attached. Tests:
  `EventDescriptionFallbackTests`.

Authorized viewers see the action-time snapshot name and colour of a **currently
visible** tag plus its current lifecycle label. Outsiders see a generic
restricted action with the team abbreviation and the action verb, never a name,
colour, note, description or identifier. Bulk events are rendered per tag and
never from the stored concatenated `tag_names`.

Current visibility governs history: reclassifying a public tag as restricted
protects its older descriptions and snapshots on the next request. Removing an
association only appends the opposing event; stored events, references and
descriptions are never rewritten.

Legacy events without catalogue references are resolved against the retained
catalogue history at read time using the same rules as the backfill. A resolved
event is presented through current visibility; an ambiguous or unresolved event
is shown as `Ação de tag não identificada` for non-administrators and keeps its
stored content untouched. Administrators may see the stored snapshot, which
never invents an identity.

## Legacy single-tag filters

The legacy `?tag=<id>` parameter remains supported on the patient list and
the ward map: it resolves as a manual ANY selection in the shared multi-tag
filter (S7/S9). Both surfaces resolve the value against the readable
catalogue first:

- unreadable, unknown or malformed values render the generic message
  `Filtro de tag inválido.` with an empty result set;
- no distinguishing status code, name, id or patient count is returned, so the
  filter cannot be used as an existence oracle or to infer patient results;
- a readable value (including a visible inactive/archived tag) filters as
  before.

## Shared cache

`WardMappingCache` stays a structural base only. Before filtering or
serialization the reader rehydrates associations and catalogue metadata for the
bounded patient set of that payload, projects them for the requester and builds
new ward/patient dictionaries. Requirements:

- stale cached names, colours and visibility decisions are never trusted;
- the cached payload is never mutated for one requester;
- the tag selector is rebuilt from the current catalogue, not from the cached
  filter payload.

Map assignment freshness, result totals and filter/map parity are delivered
by S9: the live overlay rehydrates the bounded patient set per request,
totals are recomputed from rendered rows and the list and map share one
selection/default contract.

## Administrator-only surfaces

Django Admin (`AllowedTagAdmin`, `TagAdmin`, `EventAdmin`), the catalogue forms
and the management commands (`update_ward_mapping_cache`, `security_report`,
`detect_suspicious_activity`, `security_alert_monitor`) are operator-only and
show full catalogue metadata by design. They expose aggregate counts only and
are not patient readers.

## Delivered slices and known gaps

Delivered: S6 leader tag page; S7 multi-tag list filter; S8 specialty
preferences; S9 cache-assignment freshness, result totals and map parity
(list/map share the contract; live overlay covers cache freshness).

- `OptimizedPatientEventsTimelineView` in `apps/events/views.py` caches whole
  HTML per URL and is not routed. Do not route it without per-user variation.
