## Context

The system has multiple document apps (discharge reports, prescriptions, consent forms), but no generic report for low-volume use cases (referrals, reimbursement, inter-department letters). We need a single, reusable report app that follows existing Event and markdown workflows, supports strict placeholders, and generates letterheaded PDFs with signatures. The project is single-tenant and already uses EasyMDE, Event inheritance, and a PDF generator stack.

## Goals / Non-Goals

**Goals:**
- Provide a `reports` app with ReportTemplate and Report models.
- Enforce strict placeholder validation and deterministic server-side rendering.
- Allow report creation/editing in EasyMDE and 24h edit/delete by creator.
- Generate PDFs with letterhead, page breaks, and signature section.
- Use existing Event type `REPORT_EVENT` and existing permission utilities.

**Non-Goals:**
- No attachments for reports.
- No per-template custom fields or dynamic form builders.
- No multi-tenant template scoping.
- No new permissions system beyond existing role utilities.

## Decisions

1) **Modeling as Event subtype**
   - **Decision:** Report extends Event; ReportTemplate is a separate model.
   - **Rationale:** Aligns with timeline behavior and 24h edit/delete rules.
   - **Alternatives:** Standalone model without Event inheritance (rejected; would break timeline consistency).

2) **Strict placeholder validation**
   - **Decision:** Use strict allowlist with required placeholders (patient_name, patient_record_number); page_break allowed.
   - **Rationale:** Prevents invalid templates and ensures minimum clinical identifiers.
   - **Alternatives:** Best-effort replacement with unknown placeholders left intact (rejected for predictability).

3) **Template visibility and permissions**
   - **Decision:** Templates have is_public and creator fields; only admin/staff, doctors, residents can manage templates.
   - **Rationale:** Matches user requirement and existing role utilities.
   - **Alternatives:** Group-based permissions (rejected for scope).

4) **Report content storage**
   - **Decision:** Store final editable markdown in Report.content; template may be nullable (SET_NULL).
   - **Rationale:** Reports must remain editable independent of template changes/deletions.
   - **Alternatives:** Immutable rendered_markdown (rejected because reports are editable within 24h).

5) **PDF generation approach**
   - **Decision:** Create reports/services/pdf_generator.py mirroring consentforms to handle page breaks and signatures.
   - **Rationale:** Reuses proven letterhead layout and page-break token handling.
   - **Alternatives:** Use BasePDFView only (rejected because signature section is required).

## Risks / Trade-offs

- **[Strict placeholders reduce template flexibility]** → Mitigation: clear validation errors in admin and template form.
- **[Template updates don’t affect existing reports]** → Mitigation: store content snapshot and treat template as creation aid only.
- **[PDF generation failures due to malformed markdown]** → Mitigation: server-side try/except with logging and user-friendly error.
- **[Role checks mismatch future policy changes]** → Mitigation: keep permission checks centralized in a service.

## Migration Plan

1) Add `reports` app to INSTALLED_APPS.
2) Create migrations for ReportTemplate and Report.
3) Deploy and run migrations.
4) Verify template CRUD, report CRUD, PDF download.

Rollback: remove app references and reverse migrations (Report data would be lost unless preserved externally).

## Open Questions

- Should reports be searchable or tagged in the timeline beyond standard Event search? Answer: no, they shouldn't.
- Should Report have a mandatory title/subject or is template name sufficient? Answer: the template name is sufficient.
- Should PDF include optional patient identifiers beyond those in placeholders? Answer: no.
