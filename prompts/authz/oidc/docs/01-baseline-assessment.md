# Phase 01 – Baseline Assessment & Safety Freeze

## Goal

Establish a safe starting point by auditing the current authentication/authorization state and identifying all endpoints that need protection from bot access.

## Prerequisites

- Access to EQMD codebase
- Understanding of current permission system

## Tasks

### Task 1.1: Create Feature Branch

```bash
git checkout -b feature/oidc-delegated-bots
```

### Task 1.2: Document Current Authentication Stack

Create file `docs/security/current-auth-audit.md` with:

```markdown
# Current Authentication Audit

## Date: [DATE]

## Auditor: [NAME/BOT]

### Authentication Backends (settings.py)

- [ ] django.contrib.auth.backends.ModelBackend
- [ ] allauth.account.auth_backends.AuthenticationBackend
- [ ] apps.core.backends.EquipeMedPermissionBackend

### DRF Authentication Classes

- [ ] rest_framework.authentication.SessionAuthentication

### Middleware Stack

(List all auth-related middleware in order)

### Session Configuration

- ENGINE: [value]
- COOKIE_SECURE: [value]

### allauth Configuration

- LOGIN_METHODS: [value]
- EMAIL_VERIFICATION: [value]
- ALLOW_REGISTRATION: [value]
```

### Task 1.3: Inventory All API Endpoints

Create file `docs/security/endpoint-inventory.md`:

Scan the codebase for all views that:

1. Return JSON responses
2. Accept POST/PUT/PATCH/DELETE
3. Access patient data
4. Create or modify clinical documents

For each endpoint, document:

- URL pattern
- HTTP methods
- Current authentication (LoginRequiredMixin, @login_required, DRF)
- What data it accesses/modifies
- Bot access recommendation (ALLOW/DENY/SCOPE_REQUIRED)

```markdown
# API Endpoint Inventory

## Patient Endpoints

| URL                   | Methods           | Auth               | Data Access  | Bot Access          |
| --------------------- | ----------------- | ------------------ | ------------ | ------------------- |
| /patients/api/search/ | GET               | LoginRequiredMixin | Patient list | SCOPE: patient:read |
| /patients/<id>/tags/  | GET, POST, DELETE | LoginRequiredMixin | Patient tags | DENY                |

## Daily Notes Endpoints

| URL                              | Methods   | Auth               | Data Access       | Bot Access             |
| -------------------------------- | --------- | ------------------ | ----------------- | ---------------------- |
| /dailynotes/create/<patient_id>/ | GET, POST | LoginRequiredMixin | Creates DailyNote | SCOPE: dailynote:draft |

## Events Endpoints

...

## Media Endpoints

...
```

### Task 1.4: Identify Forbidden Endpoints

Create file `docs/security/bot-forbidden-endpoints.md`:

List ALL endpoints that bots MUST NEVER access:

```markdown
# Bot-Forbidden Endpoints

These endpoints MUST reject delegated bot tokens regardless of scope.

## User Management

- /admin/\* - All admin endpoints
- /accounts/\* - All allauth endpoints
- /profiles/\* - User profile management

## Document Finalization

- Any endpoint that sets is_draft=False (to be created)
- Any endpoint that signs prescriptions
- Any endpoint that finalizes discharge reports

## Patient Status Changes

- /patients/<id>/discharge/ - Discharge patient
- /patients/<id>/admit/ - Admit patient
- /patients/<id>/transfer/ - Transfer patient

## Sensitive Operations

- /patients/<id>/edit/ - Edit patient personal data (requires doctor + human)
- Any DELETE endpoints for clinical data
```

### Task 1.5: Review Permission Decorators

Audit all custom permission decorators in `apps/core/permissions/decorators.py`:

- `@patient_access_required` - How should this behave for bots?
- `@doctor_required` - Bots are never doctors
- `@can_edit_event_required` - Bots can only edit their own drafts
- `@patient_data_change_required` - Bots cannot change patient data

Document findings in `docs/security/decorator-bot-behavior.md`.

### Task 1.6: Verify Test Coverage

Run existing tests to establish baseline:

```bash
uv run pytest apps/core/tests/test_permissions/ -v
uv run pytest apps/accounts/tests/ -v
uv run pytest apps/dailynotes/tests/test_permissions.py -v
```

Document test results and coverage.

## Files to Create

1. `docs/security/current-auth-audit.md`
2. `docs/security/endpoint-inventory.md`
3. `docs/security/bot-forbidden-endpoints.md`
4. `docs/security/decorator-bot-behavior.md`
5. `docs/security/baseline-test-results.md`

## Files to Modify

None - this phase is audit only.

## Acceptance Criteria

- [x] Feature branch created: `feature/oidc-delegated-bots`
- [x] `current-auth-audit.md` documents all authentication backends and middleware
- [x] `endpoint-inventory.md` lists ALL endpoints with bot access recommendation
- [x] `bot-forbidden-endpoints.md` explicitly lists endpoints bots must never access
- [x] `decorator-bot-behavior.md` documents expected bot behavior for each decorator
- [x] All existing permission tests pass
- [x] No code changes made (audit only)

## Verification Commands

```bash
# Verify branch exists
git branch --show-current
# Expected: feature/oidc-delegated-bots

# Verify no code changes
git diff main --stat
# Expected: Only new files in docs/security/

# Verify tests pass
uv run pytest apps/core/tests/test_permissions/ -v
# Expected: All tests pass
```

## Notes for Implementer

- Be thorough in endpoint inventory - missing an endpoint is a security risk
- When in doubt about bot access, default to DENY
- Pay special attention to any endpoint that creates Event subclasses
- Document any ambiguities for human review
