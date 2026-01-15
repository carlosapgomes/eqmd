# Matrix Synapse Integration Plan (Updated) — Overview

## Scope (Based on Clarifications)
- **Conversations**:
  - **User ↔ Bot** (1:1 DM rooms), provisioned by the **bot**.
  - **One global “all users” room**, created/managed by an **admin** (or bot acting on behalf of admin).
- **Clients**: Element Web + Element mobile.
- **Federation**: **Disabled** (single homeserver, no federation endpoints exposed).
- **E2EE**: **Disabled by default** and **enforced** (users cannot enable it).
- **Room creation/invites**:
  - Normal users **cannot create rooms** and **cannot invite**.
  - Only **admin/bot** can create rooms and invite users.
- **Identity**: reuse EquipeMed’s existing auth (Django + allauth UI). Synapse uses OIDC SSO against EquipeMed.
- **Lifecycle coupling**: when an EquipeMed user is inactive/disabled, they cannot log in to Matrix and cannot keep using existing Matrix sessions.

## Architecture Summary

### Domains
- `${MATRIX_FQDN}`: Synapse client-server API (behind existing host nginx).
- `${CHAT_FQDN}`: Element Web (behind existing host nginx).
- `${EQMD_DOMAIN}` (EquipeMed): OIDC provider endpoints for Synapse SSO (behind existing host nginx).

### Containers / Services (docker-compose)
- `matrix-synapse` (Synapse homeserver)
- `element-web` (Element Web static app)
- `postgres` (existing) — add a separate DB/user for Synapse
- `eqmd` (existing) — provides OIDC and lifecycle hooks

### Key Enforcement Mechanism (Important)
Element configuration can improve UX, but **policy must be enforced server-side**:
- A small **Synapse module** denies:
  - room creation by normal users
  - invites by normal users
  - attempts to enable encryption (`m.room.encryption`) by anyone except optionally admin (recommended: deny for all)

## Design Decisions

### 0) Domain configuration (use env vars + templating)
Do not hardcode domain names in generated configs. Use `.env` as the single source of truth:
```bash
EQMD_DOMAIN=yourhospital.com
MATRIX_FQDN=matrix.${EQMD_DOMAIN}
CHAT_FQDN=chat.${EQMD_DOMAIN}
MATRIX_PUBLIC_BASEURL=https://${MATRIX_FQDN}/
OIDC_ISSUER=https://${EQMD_DOMAIN}/o
```

Important: Synapse/Element/nginx config files generally do not interpolate env vars by themselves. Prefer generating config files from templates during deploy/start:
- `matrix/homeserver.yaml.template` → `matrix/homeserver.yaml`
- `element/config.json.template` → `element/config.json`
- nginx include/snippet template → rendered config

### 1) DM model (User ↔ Bot)
- For each EquipeMed user, the bot creates (or reuses) **one DM room** with exactly:
  - the user
  - the bot
- The bot stores the DM room id in EquipeMed (recommended) so it can find the “user thread” reliably.

### 2) Global room model (All users)
- One “all users” room is created by admin/bot.
- When a user becomes active, they are invited to the global room (optional).
- When a user is disabled, they are kicked/banned and their Matrix account is deactivated.

### 3) User identity mapping
- Avoid using usernames as Matrix `localpart` (rename/collision risk).
- Recommended mapping:
  - Matrix user id: `@u_<eqmd_user_id>:${MATRIX_FQDN}`
  - Display name: from EquipeMed full name

### 4) Non-federated configuration
- Do not expose federation listener (no `federation` resource in Synapse listeners).
- Do not expose port `8448`.
- Nginx blocks `/_matrix/federation/*` and any other federation paths.

## Deliverables (Documents in This Folder)
- `prompts/matrix-updated/matrix-synapse-phase1-infrastructure.md` ✅ **COMPLETED**
- `prompts/matrix-updated/matrix-synapse-phase2-eqmd-oidc-provider.md` ✅ **COMPLETED**
- `prompts/matrix-updated/matrix-synapse-phase3-synapse-config.md`
- `prompts/matrix-updated/matrix-synapse-phase4-element-web-and-well-known.md`
- `prompts/matrix-updated/matrix-synapse-phase5-policy-bot-and-lifecycle.md`
- `prompts/matrix-updated/matrix-synapse-phase6-testing-deployment.md`

## Known Hard Parts / Risks (Handled Explicitly in the Plan)
- **Room creation restriction** requires a Synapse module (not just Element UI tweaks).
- **Disabling E2EE reliably** requires blocking encryption state events server-side.
- **Synapse → EquipeMed OIDC** from inside Docker likely needs a `host-gateway` mapping so the container can reach the host nginx using the public domain name.
