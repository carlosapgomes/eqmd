# Tasks: duplicate-consent-form

## 1. Consent form duplication flow

Contract: `slices/slice-001-consent-form-duplication.md`

- [x] 1.1 Add `ConsentFormDuplicateForm` and
      `ConsentFormDuplicateView` (editable pre-filled markdown,
      today's document date, fixed template provenance,
      `events.add_event` + `can_access_patient` gate) with the
      `consentform_duplicate` route and
      `consentform_duplicate_form.html` template.
- [x] 1.2 Add the gated duplicate action to
      `event_card_consentform.html` (parity with report and
      prescription cards).
- [x] 1.3 Add regression tests: GET prefill (editable markdown,
      description, today's date, read-only template), POST creates
      independent corrected term (edited markdown frozen, fresh
      `rendered_at`, submitting author), source integrity, zero
      attachments copied, inactive-template source allowed, 403
      without patient access, 404 unknown source, card gating.
- [x] 1.4 Full suite green (no new failures vs the recorded
      pre-existing baseline).
