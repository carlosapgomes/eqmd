# Design: extend document duplication

## Context

Five duplication flows exist today, in three shapes:

- **Text-document shape** (daily note, simple note, history and physical,
  `apps/{dailynotes,simplenotes,historyandphysicals}/views.py`):
  `CreateView` with `permission_required = "events.add_event"`; `dispatch`
  loads the source, enforces `can_access_patient` (403 otherwise);
  `get_form_kwargs` injects `initial = {content, event_datetime: now()}`;
  `form_valid` binds the source patient and redirects to the patient
  timeline. Entry points: timeline event card + detail page + list page.
- **Clone-and-edit shape** (prescriptions,
  `OutpatientPrescriptionDuplicateView`,
  `apps/outpatientprescriptions/views.py:681`): POST-only, clones header +
  items atomically into a draft, redirects to `copy.get_edit_url()`.

The third shape — PDF form duplication (opt-in per template) — is out
of scope.

## Decision A — permission model: no opt-in flags

The new flows use exactly the text-document permission model:
`events.add_event` + `can_access_patient(user, patient)`. No
`allow_duplication`-style per-template flag.

Rationale: the PDF opt-in exists because hospital PDF templates vary in
sensitivity and national forms (APAC/AIH) must be excluded structurally.
Reports and prescriptions are clinician-authored free-form documents —
the same risk profile as daily notes, which never had a flag. Adding
flags here would create configuration surface with no demonstrated need
(YAGNI) and diverge from 4 of the 5 existing flows.

Accepted divergence: `ReportCreateView` today requires only login (no
`events.add_event`, no `can_access_patient` check), so the duplicate
action is deliberately MORE restrictive than manual creation within the
same app. Hardening report creation is out of scope; the duplicate keeps
the `events.add_event` gate for consistency with the other duplication
flows and to gate the card button.

## Decision B — report duplication uses the text-document shape

`ReportDuplicateView` is a `CreateView`, not a POST-only clone:

- Reports are a single markdown body edited through a form; there is no
  formset complexity (the reason the prescription change went POST-only,
  per its archived design).
- The pre-filled form gives the clinician a chance to adjust before the
  document exists, matching how the other text apps behave.

Concrete contract:

- Route: `reports/<uuid:pk>/duplicate/`, name `report_duplicate`
  (`apps/reports/urls.py`).
- Form: subclass of `ReportCreateForm` that excludes the `template`
  field (`Meta.fields = ['title', 'document_date', 'content']`).
  Template selection is a creation aid that re-renders content from the
  template; a duplicate must edit the source's already-rendered content,
  so exposing the selector would invite accidental content replacement.
  `get_form_kwargs` passes `user` and `patient=source.patient` —
  `ReportCreateForm.__init__` pops **both** kwargs (unlike the daily-note
  pattern, which passes only `user`). Because the subclass drops the
  `template` field, it must guard the parent's template queryset block
  (`if 'template' in self.fields:`) — `apps/reports/forms.py:140-141`
  indexes `self.fields['template']` unconditionally when `user` is set,
  which would raise `KeyError` with the field removed.
- `initial`: `title` and `content` from the source;
  `document_date` defaults to today (existing form default) — a
  duplicate is a new document issued now, consistent with
  `event_datetime = now()` in the other apps.
- The source's `template` FK is **not** carried over: the copy is
  manual content, like a hand-typed report.
- `permission_required = "events.add_event"`; `dispatch` loads the
  source report (404) and raises `PermissionDenied` when
  `can_access_patient` fails.
- Success: redirect to `patients:patient_events_timeline` for the source
  patient, with a success message.
- `event_datetime` starts empty and is set by `Report.save()` → the copy
  gets a fresh 24h edit window (existing semantics, by design).

Slice granularity note: report duplication ships endpoint + form +
card button in one slice. This deliberately diverges from the
prescription change (which split endpoint and button into two slices):
without the card entry the capability is unreachable in the UI, so a
split here would produce a backend-only slice with no user-visible
capability.

## Decision C — report card button is a GET link

`event_card_report.html` gains a duplicate link (same markup pattern as
`event_card_dailynote.html`: `bi-files` icon, `btn-outline-info`,
tooltip, aria-label), gated by `{% if perms.events.add_event %}`.
Template-level gating only; the
view re-checks permissions (defense in depth). No changes to
`apps/events/views.py` — the card template context already exposes
`perms` and the card dispatch already routes `REPORT_EVENT` to this
template.

## Decision D — prescription card button is a POST form

The duplicate endpoint is POST-only, so the card renders an inline
`<form method="post">` with `{% csrf_token %}` and `class="d-inline"`
(mirroring the detail-page markup in
`outpatientprescription_detail.html:36-42`), gated by
`{% if perms.events.add_event %}`. The button uses `bi-files` +
`btn-outline-info` to match the other timeline duplicate buttons (the
detail page keeps its `bi-copy`). Submitting clones the draft and
lands on the copy's edit view (existing endpoint behavior, unchanged).
No JavaScript, no confirmation dialog (consistent with the detail page).

## Decision E — namespace standardization targets the short form

Both spellings resolve today (app namespace `apps.dailynotes` → single
instance `dailynotes`), but the bulk of references (app-internal
templates, most tests) already use the short form. Standardizing on the
short form means:

- `app_name` in the three URLconfs drops the `apps.` prefix.
- The ~30 long-form references are rewritten to short: the three
  `models.py` `get_absolute_url`/`get_edit_url` implementations, the
  three event cards, `patient_timeline.html` (4 references),
  `events/widgets/recent_events.html`, and a handful of test files.
- Validation: repository grep for
  `apps\.(dailynotes|simplenotes|historyandphysicals):` returns zero
  matches; full test suite green.

Rejected alternative: dropping the `namespace=` kwarg in
`config/urls.py` (would break every short-form reference — hundreds).
Also rejected: standardizing on the long form (same explosion, and
inconsistent with `outpatientprescriptions`/`reports`/`events`/
`mediafiles`/`consentforms`, which already use a short `app_name`.
`patients` and `dischargereports` keep long `app_name` values
(`apps.patients`, `apps.dischargereports`) — same divergence,
explicitly out of scope here alongside `apps.accounts` and
`apps.research`.)

## Testing strategy

- S1 (reports): TDD — RED: `reverse("reports:report_duplicate")`
  NoReverseMatch / GET 404; GREEN: view + route + template; card button
  asserted in the timeline test module that already covers card links
  (`apps/patients/tests/test_patient_timeline_links.py`).
- S2 (prescription card): TDD — RED: timeline response for a
  prescription event lacks the duplicate form action; GREEN: form
  present for users with `events.add_event`, absent without; POST from
  the card URL still guarded by the view (already covered by
  `apps/outpatientprescriptions/tests/test_views.py` duplicate suite —
  no re-test of clone semantics; a single permission-denial assertion
  per R2 is the only endpoint re-assertion).
- S3 (coverage): new tests document existing POST behavior (expected
  GREEN immediately; a failure indicates a real bug → escalate, do not
  fix silently).
- S4 (namespace): failing-before evidence is the grep itself (matches
  exist before, zero after); suite green proves no regression.

## Migration plan

None. No model or schema changes in this change.

## Open questions

None blocking. Discharge report duplication is deferred by proposal, not
pending a decision here.
