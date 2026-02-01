Act as a senior Django architect and technical lead.

Your job is NOT to write implementation code.
Your job is to design a deterministic, production-grade implementation plan
that will be executed sequentially by another LLM (GLM).

You are planning work for a junior engineer.
Therefore:
- be explicit
- be step-by-step
- avoid ambiguity
- avoid large tasks

The output must optimize for:
- Clean Code
- Vertical slicing
- Test-Driven Development (tests first)
- Small safe increments
- Deterministic execution
- Easy verification
- Minimal risk per step

====================================
CONTEXT
====================================
Project: Django monolith
New app name: reports
Goal / use cases:
answers:

- reports can be edited or deleted in a 24h window by its creator as most of the other events
- only admin, doctors and residents can create templates. As this project is single tenant, public templates are visible system-wide
- I do not think they need custom fields because that's is the point for a generic template. Users can make a template for a specific recipient or purpose
- pdf output should be very similar to apps/consentforms , including a custom services/pdf_generator.py
- reports should not allow attachments

About the features:

- for Event + markdown content + EasyMDE pattern should follow examples in: apps/simplenotes/models.py, apps/simplenotes/forms.py, apps/dailynotes/forms.py
- for Template + placeholder rendering + validation should follow examples in: apps/consentforms/models.py, apps/consentforms/services/renderer.py, apps/consentforms/forms.py
- for Public/private templates pattern should follow examples in:  apps/drugtemplates/models.py and access filtering like Q(creator=user) | Q(is_public=True) in apps/outpatientprescriptions/views.py
- for PDF generation from markdown with hospital letterhead should follow examples in: apps/consentforms/services/pdf_generator.py  apps/pdfgenerator/services/pdf_generator.py, apps/pdfgenerator/services/markdown_parser.py, apps/pdfgenerator/views.py
- for Event type already reserved: Event.REPORT_EVENT = 8 in apps/events/models.py with label “Relatório”

Implementation Shape (matches existing patterns)

ok  - Report template model similar to consent templates: name, markdown_body, is_active, created_by, updated_by, history.
ok  - Report model extends Event like dailynotes/simplenotes: content (markdown), template FK (nullable), document_date, maybe title/subject.
ok  - Template visibility like drugtemplates: is_public + creator (optionally “system” templates via admin).
ok  - Form flow: select template → server renders initial content → user edits in EasyMDE → save event.
ok  - Timeline integration: set event_type = Event.REPORT_EVENT and description maybe from template name or user-provided title.

Placeholder Strategy Options
Option A: strict placeholders (like consentforms)

- Define allowed placeholders and require values for each (except page_break).

base placeholders (from existing models):

- Patient: patient_name, patient_record_number, patient_birth_date, patient_age, patient_gender, patient_fiscal_number, patient_healthcard_number, patient_ward, patient_bed, patient_status
- Doctor: doctor_name, doctor_profession, doctor_registration_number, doctor_specialty
- Document: document_date, document_datetime
- Hospital: hospital_name, hospital_city, hospital_state, hospital_address
- Layout: page_break (reuse the consentforms token approach)

PDF Strategy

- I need page breaks and signature sections, so you should follow consentforms’ custom generator (apps/consentforms/services/pdf_generator.py), which already supports a page_break token.

Follow existing project conventions and patterns.

====================================
GLOBAL ENGINEERING CONSTRAINTS (HARD RULES)
====================================

Clean Code:

- Single responsibility per function/class
- Functions <= 25 lines
- Classes small and cohesive
- No duplication (DRY)
- No business logic in views
- Business logic lives in services
- Persistence isolated in repositories/models
- Explicit, intention-revealing names
- No magic numbers or inline config
- Prefer composition over inheritance
- Avoid boolean flag arguments
- Explicit error handling only

Architecture:
views -> services -> repositories/models -> serializers/DTO

Testing:

- TDD strictly (tests first, then implementation)
- pytest + pytest-django
- Prefer behavior/integration tests over testing internals
- All business logic unit tested
- Each slice must leave the project green (all tests passing)

Slicing:

- Work only in small vertical feature slices
- Each slice must deliver an end-to-end working feature
- Each slice must be independently testable
- Each slice must fit within ~1–2 hours of work
- Avoid big-bang steps like “create all models” or “scaffold everything”
- Prefer MORE smaller slices over fewer larger ones
- If unsure, split further

Execution:

- After each slice: run tests + lint + type checks
- STOP after completing a slice
- Never combine multiple slices

====================================
OUTPUT FORMAT (STRICT)
====================================

Produce:

------------------------------------
1) OpenSpec
------------------------------------
- Functional requirements
- Non-functional requirements
- Engineering standards (clean code rules)
- Acceptance criteria
- Definition of Done

------------------------------------
2) Architecture Overview
------------------------------------
- Proposed app structure (files/modules)
- Layer responsibilities
- Dependency rules

------------------------------------
3) Slice Plan
------------------------------------
Break the work into MANY SMALL vertical slices.
Prefer 6–12 small slices rather than 2–3 large ones.

Each slice must be independently valuable and safe.

------------------------------------
4) For EACH slice output EXACTLY:
------------------------------------

### Slice N — <short name>

Goal:
(User-visible or testable outcome)

Scope boundaries:
(what is included / excluded)

Files to create/modify:
(explicit list)

Tests to write FIRST (TDD):
(list concrete pytest cases)

Implementation steps:
(minimal code only, no premature abstractions)

Refactor steps:
(clean code improvements only after tests pass)

Verification commands:
(pytest, lint, typecheck, etc.)

------------------------------------
MANDATORY CHECKLIST
------------------------------------
Provide a markdown checklist for deterministic execution:

Checklist:

Spec
- [ ] requirements understood

Tests (RED)
- [ ] failing tests written
- [ ] tests cover behavior and edge cases

Implementation (GREEN)
- [ ] minimal code added
- [ ] tests pass

Refactor (CLEAN)
- [ ] responsibilities separated
- [ ] duplication removed
- [ ] functions small
- [ ] naming improved
- [ ] business logic only in services

Verification
- [ ] pytest passes
- [ ] lint/ruff/flake8 passes
- [ ] type checks (mypy) pass

STOP RULE
- [ ] stop here and do NOT start next slice

------------------------------------
Prompt for Implementer LLM (GLM)
------------------------------------
Write a ready-to-copy prompt that:
- tells GLM to execute ONLY this slice
- follow TDD
- follow clean code rules
- complete checklist sequentially
- stop after completion

------------------------------------

IMPORTANT RULES
------------------------------------
- Do NOT generate implementation code
- Only output the plan
- Be extremely concrete
- Avoid vague instructions
- Prefer smaller slices
- If a slice feels large, split it
