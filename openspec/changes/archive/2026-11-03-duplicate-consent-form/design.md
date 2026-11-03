# Design: duplicate-consent-form

## Context

`ConsentForm(Event)` freezes `rendered_markdown` at creation
(rendered from `ConsentTemplate.markdown_body` with patient/date/
procedure substitutions) and forbids later changes at the model
level (`ValidationError: "Rendered markdown is immutable"`).
`ConsentFormUpdateView` only uploads scanned attachments. The create
flow (`ConsentFormCreateView` + `ConsentFormCreateForm`) gates on
`events.add_event` + `can_access_patient` and validates
`document_date <= today`, active template and a minimum procedure
description.

## Decision D1 — A′: editable snapshot at (re)creation

A literal "pre-filled create form" cannot deliver the clinical
intent — a small text correction — because no existing surface edits
a term's markdown. The duplicate form therefore exposes the source's
`rendered_markdown` (already patient-substituted) as an editable
field: the user tweaks it, saves, and the NEW document freezes the
corrected text with a fresh `rendered_at`. Per-document immutability
is preserved: the duplicate is a creation, not an edit of the
source.

## Decision D2 — Field copy matrix

Copied from the source: `procedure_description` (editable),
`template` (fixed FK reference for provenance — allowed even if the
template is now inactive, since `PROTECT` already forbids template
deletion; the create form's `clean_template` active-check does not
apply to this fixed reference).

Fresh on the copy: `document_date` (defaults to today, editable,
still `<= today` validated), `rendered_markdown` (edited field
value), `rendered_at` = now, `event_datetime` = now,
`created_by`/`updated_by` = submitting user, `description` =
"Termo de Consentimento - {template.name}", `event_type` =
`CONSENT_FORM_EVENT`.

Never copied: attachments (new signature cycle needs new scans),
any link back to the source, `document_date` of the source.

## Decision D3 — Permissions

Same contract as the create flow: view requires
`events.add_event` (PermissionRequiredMixin) plus
`can_access_patient(user, source.patient)` in `dispatch`; card
action gated by `perms.events.add_event`. No edit-window logic —
duplicating is creating, and the signed original is never mutated.

## Decision D4 — Implementation

`ConsentFormDuplicateForm(forms.ModelForm)` — NOT a subclass of
`ConsentFormCreateForm` (different field set and save pipeline: it
must skip `render_template` and use the edited markdown) — holding
`document_date`, `procedure_description` (ModelForm fields) plus an
extra `markdown` CharField (Textarea) prefilled from the source in
`__init__` (popping a `source` kwarg alongside `user`/`patient`),
reusing the create form's `clean_document_date` and
`clean_procedure_description` rules verbatim. `save()` stamps the
D2 matrix.

`ConsentFormDuplicateView(LoginRequiredMixin, PermissionRequiredMixin,
CreateView)` resolves the source via `get_object_or_404` in
`dispatch`, renders `consentforms/consentform_duplicate_form.html`
(same layout/preview JS as the create form, title "Duplicar Termo
de Consentimento", template name shown read-only), redirects to the
patient timeline with a pt-BR success message.

## Decision D5 — Card parity

Button between the PDF and attachment-edit actions in
`event_card_consentform.html`: `bi-files`, `btn-outline-info`,
tooltip/aria "Duplicar termo de consentimento", gated by
`{% if perms.events.add_event %}` — identical to the report,
prescription and (upcoming) discharge-report cards.

## Decision D6 — Auto date replacement at prefill (one-shot)

The render pipeline bakes the source's `document_date` into the
text as `%d/%m/%Y` (`render_template` context). The duplicate
form's markdown initial therefore applies a single best-effort
replacement at prefill time: every occurrence of
`source.document_date.strftime("%d/%m/%Y")` becomes today's date
in the same format. One-shot and best-effort by design: if the
source date does not appear verbatim in the text (hand-written
variants, long-form dates), nothing is replaced and the user
adjusts manually; if the user later changes the `document_date`
field in the form, the markdown keeps the prefilled text (no
dynamic binding).

## Risks / Trade-offs

- Divergence between the edited duplicate and the current template
  content is INTENDED (that is the correction) — the fixed template
  reference keeps provenance without implying content equality.
- Inactive template on the source: accepted by design (D2); test
  covers it.
