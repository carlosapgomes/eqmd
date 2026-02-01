# Reports app plan

## Context
- App name: reports
- Event type: Event.REPORT_EVENT (8)
- Templates: strict placeholders, required patient_name and patient_record_number, page_break allowed
- PDF: letterhead + page breaks + signature section (consentforms pattern)
- Edit/delete: 24h window by creator (standard event rules)
- Templates: only admin/staff, doctors, residents can manage; public templates visible system-wide
- No attachments

## Architecture overview
- Models: ReportTemplate, Report (extends Event)
- Services: renderer, context_builder, report_service, permissions, pdf_generator
- Views: template CRUD, report CRUD, PDF download
- Templates: Bootstrap 5 user-facing views with EasyMDE
- Rules: business logic in services; views only orchestrate

## Slice list
1. App scaffold + placeholder renderer
2. ReportTemplate model + admin + validation
3. Template permission service
4. Template CRUD UI (list/create/update)
5. Report model + context builder + report service
6. Report create UI (EasyMDE + template selection)
7. Report detail/update/delete with 24h rules
8. PDF generator + download view
9. Navigation/timeline integration
10. Move report link to timeline dropdown

## Notes on verification
- Use `./scripts/test.sh <test_target>` for each slice.
- Lint/typecheck tools are not configured in this repo; do not invent commands.

