## Context

Discharge reports currently use a print-only HTML view (`/print/`) with custom CSS. Other document types (prescriptions, reports, consent forms) already use the shared `apps/pdfgenerator` infrastructure with consistent branding, pagination, and signatures. We need to replace discharge report printing with a PDF flow while keeping the discharge content structure consistent with the current print layout. Additionally, discharge report deletion permissions and timeline actions are inconsistent with other event types.

## Goals / Non-Goals

**Goals:**
- Generate discharge report PDFs using the shared `HospitalLetterheadGenerator` with pagination, page numbers, date, and doctor signature.
- Preserve the current discharge report section structure (patient identification, admission/discharge dates, clinical sections) in the PDF content.
- Replace print buttons on the discharge report detail page and timeline card with PDF download buttons using the standard `pdf-download.js` behavior.
- Enforce delete permissions for finalized discharge reports consistent with other events (creator within 24h window or users with `events.delete_event`).
- Add a delete action to the discharge report timeline card with proper permission checks.

**Non-Goals:**
- Introducing new PDF document types beyond discharge reports.
- Redesigning the discharge report content or adding new data fields.
- Changing the general event permission system beyond discharge report usage.

## Decisions

1) **PDF Generation Approach**
   - Use a dedicated `DischargeReportPDFGenerator` service in `apps/dischargereports/services/pdf_generator.py` that subclasses `HospitalLetterheadGenerator` and uses `MarkdownToPDFParser` (similar to reports/consent forms).
   - Build discharge content as markdown sections in a deterministic order that mirrors the existing print template (e.g., Problems/Diagnosis, Admission History, Exams, Procedures, Inpatient History, Discharge Status, Recommendations) and feed it to the parser.
   - Rationale: This mirrors current content, leverages the shared PDF infrastructure, and keeps discharge report logic encapsulated in its app, matching existing patterns.
   - Alternatives considered: Use the generic `pdfgenerator` POST endpoint (`/pdf/discharge-report/`) directly and build JSON in the view. Rejected because the existing apps (reports/consent forms) use app-level generators, and we need precise ordering and formatting without a client-side POST step.

2) **PDF View & URL**
   - Add a discharge report PDF download view (GET) in `apps/dischargereports/views.py` and a route `/dischargereports/<uuid:pk>/pdf/`.
   - Remove the `/print/` route and template usage.
   - Rationale: Aligns with existing app patterns (reports/consent forms/outpatient prescriptions) and supports the `pdf-download.js` button behavior.

3) **Permission Alignment for Deletion**
   - For finalized discharge reports, use the same rule as other events: `can_delete_event` (creator within 24h window or users with `events.delete_event`).
   - Draft deletion remains allowed for creator or users with delete permission, but drafts are not restricted by the 24h window.
   - Rationale: This matches the requested behavior while preserving draft flexibility.
   - Alternatives considered: Apply `can_delete_event` uniformly to drafts and finals. Rejected because drafts historically allow broader deletion, and tightening would be a behavior change outside scope.

4) **Timeline Actions**
   - Replace the print button with a PDF download button (same pattern as report/prescription cards) and add a delete button with the same permission gate as the detail page.
   - Rationale: UI consistency and parity of actions between detail page and timeline.

## Risks / Trade-offs

- **[Risk]** Markdown parsing may render differently than the current print HTML layout. → **Mitigation:** Keep the same section titles and ordering; use minimal markdown formatting to avoid unexpected styling.
- **[Risk]** Removing the `/print/` route might break existing bookmarks. → **Mitigation:** Optionally add a redirect from `/print/` to `/pdf/` or remove route explicitly (decision to delete; no redirect unless requested).
- **[Risk]** Permission logic changes could surface unexpected delete options. → **Mitigation:** Use existing `can_delete_event` behavior and add tests for finalized report deletion within the edit window.

## Migration Plan

1) Add discharge report PDF generator service, view, and URL.
2) Update detail and timeline templates to use `pdf-download.js` pattern.
3) Remove print view and template; clean URLs.
4) Adjust delete permission logic and update timeline card delete action.
5) Add tests and run `./scripts/test.sh apps.dischargereports`.

## Open Questions

- None (scope and permission rules confirmed).
