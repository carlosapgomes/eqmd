## 1. Implementation
- [x] 1.1 Create consentforms app with ConsentTemplate, ConsentForm (Event subclass), and ConsentAttachment models
- [x] 1.2 Register ConsentTemplate in Django admin with active toggle and audit history display
- [x] 1.3 Implement template rendering service with allowlist validation and immutable markdown snapshots
- [x] 1.4 Implement consent form create/detail/edit views and urls following dailynotes/simplenotes patterns
- [x] 1.5 Add patient timeline "Create event" entry for consent forms and template selection flow
- [x] 1.6 Integrate PDF generation using pdfgenerator (HospitalLetterheadGenerator + MarkdownToPDFParser)
- [x] 1.7 Implement attachment uploads with validation (1-3 images or single PDF) within edit window
- [x] 1.8 Add tests for rendering, permissions, CRUD, PDF generation, and attachments
