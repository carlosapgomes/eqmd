# Concent Forms prompt

You are gpt-5.2-codex. Implement OpenSpec artifacts for a Django feature: Consent Forms management in an existing medical application.

IMPORTANT
- Before writing any artifacts, READ and FOLLOW:
  - @openspec/AGENTS.md
  - @openspec/project.md
- Use those files to determine:
  - Which artifacts to generate
  - File locations
  - Required structure and formatting
  - Agent responsibilities and conventions
- Do NOT invent artifact types or file layouts that conflict with OpenSpec configuration.

PROJECT CONTEXT
- This is an existing Django monolith with established conventions.
- Consent forms are printed, signed physically (wet signature by patient and doctor) and stamped.
- The system generates, prints, and archives the document text and audit trail.
- Canonical stored content MUST be pure Markdown.

EXISTING INFRASTRUCTURE (MUST REUSE)
- PDF generation already exists:
  - App: @apps/pdfgenerator
  - Reference usage: @apps/outpatientprescriptions
  - Inspect and reuse the same PDF generation pattern.
- CRUD and UI conventions:
  - Follow patterns from @apps/dailynotes and @apps/simplenotes.
- Authorization:
  - The system already restricts event edit/delete to the creator within a 24-hour window.
  - Reuse this logic; do NOT introduce new authorization rules.

CONSENT FORMS – FUNCTIONAL SCOPE
- Admin-only template management:
  - Admins create, edit, and version consent templates.
  - Templates are fully configurable; do NOT hardcode template “types”.
  - Clinicians can only consume templates; they cannot create or edit them.
- Templates use Markdown with placeholder-based templating.

TEMPLATING RULES
- Placeholder syntax:
  - {{ patient_name }}
  - {{ patient_record_number }}
  - {{ document_date }}
  - {{ procedure_description }}
- Rendering MUST be allowlist-based.
- Required placeholders:
  - patient_name
  - patient_record_number
  - document_date
- Unknown placeholders MUST raise an error.
- Rendering produces an immutable Markdown snapshot.

EVENT-BASED MODELING
- Consent forms MUST be implemented as Events.
- Derive the consent model from @apps/events base model so it appears in the patient timeline.

USER WORKFLOW
- From the patient timeline “Create event” dropdown:
  - User selects a consent template.
  - Show a form with:
    - patient_name (autofilled, read-only)
    - patient_record_number (autofilled, read-only)
    - document_date (autofilled to today, editable)
    - procedure_description (empty, required)
- On save:
  - Render the selected template to Markdown.
  - Store the rendered Markdown snapshot in the database.
  - Create an Event visible in the patient timeline.

PDF & PRINTING
- PDF generation MUST reuse @apps/pdfgenerator.
- Follow the integration pattern from @apps/outpatientprescriptions.
- PDFs are generated from the rendered Markdown snapshot.
- PDF generation may be on-demand and must be deterministic.

OPTIONAL SCANNED DOCUMENT UPLOAD
- Non-required feature.
- Within the existing 24-hour edit window:
  - The creator may edit the consent event.
  - Upload 1–3 images (one per page) OR a single PDF.
- Attach uploads to the consent event.
- Do NOT add new permissions or workflow states.

GOALS
- Produce OpenSpec-compliant artifacts that fully specify:
  - Domain model
  - APIs
  - UI flows
  - Templating and rendering rules
  - PDF generation integration
  - Audit and immutability guarantees
- Artifacts MUST align with existing project patterns and OpenSpec configuration.

OUTPUT RULES
- Output ONLY the OpenSpec artifacts required by @openspec/AGENTS.md and @openspec/project.md.
- No commentary or explanation.
- Use consistent naming across all artifacts.
- Assume Django + Django REST Framework.
- Assume repo-aware execution and inspection of referenced apps.

BEGIN.
