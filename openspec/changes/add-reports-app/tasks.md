## 1. App scaffolding and renderer

- [x] 1.1 Create reports app package, services folder, and tests folder
- [x] 1.2 Implement placeholder renderer with allowlist, required placeholders, and page_break token
- [x] 1.3 Add renderer unit tests and register reports app in settings

## 2. ReportTemplate model

- [x] 2.1 Add ReportTemplate model with history, visibility flags, and validation
- [x] 2.2 Create admin registration for ReportTemplate
- [x] 2.3 Add model tests for placeholder validation and defaults

## 3. Template permissions and CRUD UI

- [x] 3.1 Implement template permission service (admin/staff, doctor, resident)
- [x] 3.2 Add template list/create/update views with visibility filtering
- [x] 3.3 Add template form and user-facing templates
- [x] 3.4 Add view tests for template permissions and visibility

## 4. Report model and services

- [x] 4.1 Add Report model extending Event with content, document_date, title, and template FK
- [x] 4.2 Implement context builder for placeholders (patient/doctor/hospital/document)
- [x] 4.3 Implement report service for rendering and creation
- [x] 4.4 Add model/service tests for report behavior

## 5. Report CRUD UI

- [x] 5.1 Add report create form/view with EasyMDE and template selection
- [x] 5.2 Add report detail/update/delete views with 24h rules
- [x] 5.3 Add user-facing templates for report create/detail/update/delete
- [x] 5.4 Add view tests for report CRUD and permissions

## 6. PDF generation

- [x] 6.1 Implement report PDF generator with letterhead, page breaks, signature section
- [x] 6.2 Add PDF download view and URL
- [x] 6.3 Add PDF button to report detail template
- [x] 6.4 Add PDF view tests

## 7. Navigation integration

- [x] 7.1 Add report create link in patient UI
- [x] 7.2 Add template test for link visibility

## 8. Report refinements

- [x] 8.1 Expand report placeholder allowlist and required placeholders
- [x] 8.2 Extend report context builder and renderer tests for new placeholders
- [x] 8.3 Update report create flow (template title prefill + MM-DD-YYYY date input)
- [x] 8.4 Add report event card with PDF/delete actions and timeline wiring
- [x] 8.5 Align report detail layout and placeholder documentation
