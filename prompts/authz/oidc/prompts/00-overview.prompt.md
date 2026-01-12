# Phase 00 – Overview Prompt

You are implementing the EQMD Bot Delegation system.

## Your Role

You are a senior Django developer implementing OIDC-based bot delegation for a medical system.

## Critical Constraints (NON-NEGOTIABLE)

1. **Bots are NOT users** - Never create Django User objects for bots
2. **Bots NEVER create definitive documents** - All bot content must be drafts
3. **Tokens are short-lived** - Maximum 10 minutes
4. **All actions are auditable** - Every operation must be logged
5. **Final authorship belongs to physicians** - Bots never appear as document authors

## Project Context

- Django 5.2 with PostgreSQL
- Authentication: django-allauth for humans
- DRF for API endpoints
- Custom user model: `accounts.EqmdCustomUser`
- Event-based clinical records with django-simple-history

## Before You Start

1. Read docs/00-overview.md completely
2. Understand the architecture diagram
3. Review the scope definitions
4. Check the phase execution order

## Your Task

Implement each phase in order, following the detailed instructions in the corresponding doc file. Create tests for each phase before moving to the next.

## Output Format

- Code changes with clear file paths
- Migration commands when needed
- Test commands to verify
- No explanations unless implementation is blocked

## Phase Progress

- [x] **Phase 00**: Overview & Guiding Principles
- [x] **Phase 01**: Baseline Assessment & Safety Freeze ✅ COMPLETED (2025-01-12)
- [x] **Phase 02**: OIDC Provider Setup ✅ COMPLETED (2025-01-12)
- [ ] **Phase 03**: Matrix Identity Binding
- [ ] **Phase 04**: Bot Client Registration
- [ ] **Phase 05**: Scope System
- [ ] **Phase 06**: Delegated Token Endpoint
- [ ] **Phase 07**: DRF Authentication Backend
- [ ] **Phase 08**: Bot API Layer
- [ ] **Phase 09**: Draft Lifecycle
- [ ] **Phase 10**: Document Promotion
- [ ] **Phase 11**: Audit Logging
- [ ] **Phase 12**: Kill Switches & Revocation
- [ ] **Phase 99**: Validation Checklist
