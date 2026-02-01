## 1. App scaffolding and renderer

- [ ] 1.1 Create reports app package, services folder, and tests folder
- [ ] 1.2 Implement placeholder renderer with allowlist, required placeholders, and page_break token
- [ ] 1.3 Add renderer unit tests and register reports app in settings

## 2. ReportTemplate model

- [ ] 2.1 Add ReportTemplate model with history, visibility flags, and validation
- [ ] 2.2 Create admin registration for ReportTemplate
- [ ] 2.3 Add model tests for placeholder validation and defaults

## 3. Template permissions and CRUD UI

- [ ] 3.1 Implement template permission service (admin/staff, doctor, resident)
- [ ] 3.2 Add template list/create/update views with visibility filtering
- [ ] 3.3 Add template form and user-facing templates
- [ ] 3.4 Add view tests for template permissions and visibility

## 4. Report model and services

- [ ] 4.1 Add Report model extending Event with content, document_date, title, and template FK
- [ ] 4.2 Implement context builder for placeholders (patient/doctor/hospital/document)
- [ ] 4.3 Implement report service for rendering and creation
- [ ] 4.4 Add model/service tests for report behavior

## 5. Report CRUD UI

- [ ] 5.1 Add report create form/view with EasyMDE and template selection
- [ ] 5.2 Add report detail/update/delete views with 24h rules
- [ ] 5.3 Add user-facing templates for report create/detail/update/delete
- [ ] 5.4 Add view tests for report CRUD and permissions

## 6. PDF generation

- [ ] 6.1 Implement report PDF generator with letterhead, page breaks, signature section
- [ ] 6.2 Add PDF download view and URL
- [ ] 6.3 Add PDF button to report detail template
- [ ] 6.4 Add PDF view tests

## 7. Navigation integration

- [ ] 7.1 Add report create link in patient UI
- [ ] 7.2 Add template test for link visibility
