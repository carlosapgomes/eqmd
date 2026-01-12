# Phase 00 – Overview & Guiding Principles

## Executive Summary

This refactor introduces **OIDC-based delegated authentication for bots** into the EQMD system while **preserving django-allauth as the human IdP**. The goal is to enable Matrix-based bots to assist physicians with clinical documentation tasks under strict delegation controls.

## Non-Negotiable Principles

These principles MUST be enforced throughout all phases:

### 1. Bots Are Not Users

- Bots MUST be represented as OIDC Clients, never as Django User objects
- No bot should ever have a row in `accounts_eqmdcustomuser`
- Bot identity is established via `client_id`, not user credentials

### 2. Bots Never Create Definitive Clinical Documents

- All bot-created content MUST be marked as drafts (`is_draft=True`)
- Drafts auto-expire after 24-36 hours if not reviewed
- Only human physicians can promote drafts to definitive documents

### 3. Delegation Tokens Are Short-Lived and Scoped

- Maximum token lifetime: 10 minutes
- Tokens MUST specify explicit scopes
- Tokens MUST identify both the delegating physician (`sub`) and the bot (`azp`)

### 4. Final Clinical Authorship Belongs to the Physician

- When a draft is promoted, `created_by` becomes the approving physician
- No bot references appear in the final clinical record
- Audit trail preserves the delegation history separately

### 5. All Bot Actions Are Auditable

- Every delegated token issuance is logged
- Every bot action includes physician + bot + scope + timestamp
- Audit logs are immutable

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           MATRIX                                     │
│  ┌──────────────┐                                                   │
│  │   Physician  │ ──(1) command──▶ ┌──────────────┐                │
│  │ Matrix Client│                   │  Matrix Bot  │                │
│  └──────────────┘                   └──────┬───────┘                │
└─────────────────────────────────────────────┼───────────────────────┘
                                              │
                    (2) POST /auth/delegated-token/
                        {matrix_id, scopes}
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            EQMD                                      │
│                                                                      │
│  ┌────────────────────┐    ┌─────────────────────────────────────┐ │
│  │ MatrixUserBinding  │◀───│ Lookup physician by matrix_id       │ │
│  │ user ↔ matrix_id   │    └─────────────────────────────────────┘ │
│  └────────────────────┘                                             │
│            │                                                         │
│            ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Delegated Token Endpoint                                        ││
│  │ - Verify bot (client_credentials)                               ││
│  │ - Verify physician is active & can create documents             ││
│  │ - Verify requested scopes ⊆ bot allowed scopes                  ││
│  │ - Issue JWT: {sub: physician, azp: bot, scope: [...]}           ││
│  └─────────────────────────────────────────────────────────────────┘│
│            │                                                         │
│            │ (3) JWT token                                          │
│            ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Bot API Endpoints (DRF)                                         ││
│  │ - DelegatedJWTAuthentication validates token                    ││
│  │ - request.user = physician                                      ││
│  │ - request.actor = bot                                           ││
│  │ - request.scopes = [...]                                        ││
│  │ - HasScope permission checks                                    ││
│  └─────────────────────────────────────────────────────────────────┘│
│            │                                                         │
│            │ (4) Create draft                                       │
│            ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Event Model (is_draft=True)                                     ││
│  │ - draft_created_by_bot = bot client_id                          ││
│  │ - draft_delegated_by = physician                                ││
│  │ - draft_expires_at = now + 36h                                  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Phase Execution Order

Phases MUST be executed in order. Each phase has explicit acceptance criteria that must pass before proceeding.

| Phase | Name                       | Critical | Description                                        |
| ----- | -------------------------- | -------- | -------------------------------------------------- |
| 00    | Overview                   | ✅       | This document                                      |
| 01    | Baseline Assessment        | ✅       | Audit current auth, identify protected endpoints   |
| 02    | OIDC Provider Setup        | ✅       | Install django-oidc-provider, zero behavior change |
| 03    | Matrix Identity Binding    | ✅       | Link Matrix IDs to EQMD users                      |
| 04    | Bot Client Registration    | ✅       | Model bots as OIDC clients                         |
| 05    | Scope System               | Yes      | Define and enforce authorization scopes            |
| 06    | Delegated Token Endpoint   | Yes      | Core delegation mechanism                          |
| 07    | DRF Authentication Backend | Yes      | Validate delegated JWTs in API                     |
| 08    | Bot API Layer              | Yes      | REST API for bot operations                        |
| 09    | Draft Lifecycle            | Yes      | is_draft field, expiration, cleanup                |
| 10    | Document Promotion         | Yes      | Draft → definitive flow                            |
| 11    | Audit Logging              | Yes      | Comprehensive delegation audit trail               |
| 12    | Kill Switches & Revocation | Yes      | Emergency controls                                 |
| 99    | Validation Checklist       | Yes      | Security verification                              |

## Scope Definitions (Reference)

### Allowed Scopes (Bot Can Request)

```
patient:read          - Read patient demographics and status
exam:read             - Read exam results and requests
dailynote:draft       - Create daily note drafts
dischargereport:draft - Create discharge report drafts
prescription:draft    - Create prescription drafts
summary:generate      - Generate summaries from existing data
```

### Forbidden Scopes (Never Issued to Bots)

```
patient:write         - Modify patient data
note:finalize         - Create definitive clinical notes
prescription:sign     - Sign prescriptions
discharge:finalize    - Finalize discharge reports
user:*                - Any user management
admin:*               - Any admin operations
```

## Current System State (Reference)

### Authentication Stack

- django-allauth: Human login via email
- SessionAuthentication: DRF (session-based)
- Custom user model: `accounts.EqmdCustomUser`

### Authorization Stack

- 2-tier permission model (Doctors/Residents vs Others)
- `EquipeMedPermissionBackend` for object-level permissions
- Time-based event editing (24h window)

### Key Models

- `EqmdCustomUser`: Custom user with lifecycle management
- `Event`: Base class for all clinical events (has `created_by`, history)
- `DailyNote`, `DischargeReport`, etc.: Extend Event

### What Needs to Be Added

- ✅ `MatrixUserBinding`: Link matrix_id ↔ user (Phase 03 completed)
- OIDC Client registry (via django-oidc-provider) (Phase 02 completed)
- `is_draft` and related fields on Event model
- Delegated token endpoint
- DRF authentication backend for delegated JWTs
- Bot API endpoints
- Audit models for delegation events

## Success Criteria (End State)

After all phases complete:

1. ✅ Physician can link their Matrix account to EQMD (Phase 03 completed)
2. Matrix bot can request delegated token for a physician
3. Delegated token allows bot to create drafts only
4. ✅ Drafts expire automatically after 36 hours
5. ✅ Physician can review and promote drafts
6. ✅ Promoted documents show physician as author
7. ✅ Full audit trail exists for all delegated actions
8. ✅ Kill switch can disable all bot delegation instantly
9. ✅ Deactivated physician cannot delegate (existing tokens expire naturally)
10. ✅ No regression in human authentication flow
