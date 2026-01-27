## Context

Hospital PDF forms are dynamically generated from configurable field mappings. The APAC form already provides a procedure search experience that queries the MedicalProcedure API by code or description. We want the same search UX for hospital-specific PDF forms without adding a new field type to the configurator.

## Goals / Non-Goals

- Goals:
  - Enable procedure lookup by code or description for hospital PDF forms.
  - Keep admin configuration simple via naming convention.
  - Enforce selection from valid procedures and prevent manual edits of code/description fields.
  - Store only code and description (no procedure UUID).
- Non-Goals:
  - Adding a new configurator field type UI.
  - Supporting multiple procedure search groups per form (out of scope for now).

## Decisions

- Decision: Use naming convention detection.
  - If `procedure_code` and `procedure_description` exist in the template config, render a single combined search input and bind it to those fields.
  - Rationale: avoids new field types and keeps admin workflow unchanged.

- Decision: Generate a synthetic display field in the form and hide or disable the raw fields.
  - The display field shows "CODE - Description" and drives the search dropdown.
  - The raw fields remain in the form for submission and PDF overlay mapping.

- Decision: Enforce selection server-side.
  - Validate that `procedure_code` exists in MedicalProcedure and (optionally) matches the selected description.
  - Reject free-text values not matched to a known procedure.

## Alternatives Considered

- Add a new field type (e.g., `procedure_search`) to the configurator.
  - Rejected: more UI and validation work; administrators prefer naming convention.

- Use existing linked data_sources system.
  - Rejected: requires loading procedure data into form config or building a remote data source type.

## Risks / Trade-offs

- Validation depends on MedicalProcedure content; missing or incomplete data can block submissions.
- Hiding fields may confuse admins who expect to see code/description inputs; requires clear documentation.

## Migration Plan

- No data migration required; only affects form rendering and validation when the naming convention is used.

## Open Questions

- Should server validation require code-only match or code+description exact match?
