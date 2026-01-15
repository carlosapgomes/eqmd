# Phase 6: Testing, Deployment, and Ops

## Goal
Validate end-to-end behavior with real clients and confirm operational basics (backups, updates).

## 1) Core functional tests

### 1.1 SSO login tests
- Element Web: login via SSO, verify sync
- Element mobile: login via SSO, verify sync

### 1.2 Policy enforcement tests (must pass on mobile too)
- As normal user:
  - cannot create a room
  - cannot invite another user
  - cannot enable encryption in any room

### 1.3 Bot DM provisioning
- Activate a user (or run provisioning command)
- Verify DM room exists and bot can message user

### 1.4 Global room behavior
- Admin creates global room
- Invite all users
- Verify disabled user is removed and loses access

## 2) Media tests
- Upload:
  - image
  - PDF
  - audio file
- Confirm nginx and Synapse size limits align (no confusing “413” errors).

## 3) Deployment checklist
- Pin versions (Synapse + Element).
- Persist:
  - Postgres data
  - Synapse `/data` (media store + signing keys)
- Backups:
  - nightly dump `matrix_db`
  - backup media store volume/path

## 4) Upgrade strategy
- Upgrade in a staging-like environment first (same versions as prod).
- Review Synapse release notes specifically for:
  - OIDC behavior changes
  - module/spam-checker API changes
  - database migrations

## 5) Observability
- Enable access logs at nginx for `${MATRIX_FQDN}` and `${CHAT_FQDN}`.
- Keep Synapse logs in a persisted location.
- Monitor disk usage of the media store.

## Exit Criteria
- All tests in section (1) pass using both Element Web and Element mobile.
- Backups are in place for DB + media.
- Upgrade procedure is documented and repeatable.
