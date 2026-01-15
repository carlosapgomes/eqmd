# Phase 3: Synapse Configuration (Minimal, Non-Federated, Media-Friendly)

## Goal
Configure Synapse with:
- OIDC SSO against EquipeMed
- no federation
- no local registration
- media uploads for images/audio/pdfs

## 1) Generate baseline config from the pinned Synapse image
Always generate `homeserver.yaml` using the same pinned Synapse version you deploy.

This avoids “fake config keys” that cause Synapse to crash on startup.

## 2) Minimal must-have settings to confirm
In `matrix/homeserver.yaml`, ensure at least:
- `server_name: "${MATRIX_FQDN}"`
- Postgres DB config (host `postgres`, db `matrix_db`, user `matrix_user`)
- `public_baseurl: "${MATRIX_PUBLIC_BASEURL}"` (example: `https://${MATRIX_FQDN}/`)
- listeners:
  - client-server API enabled
  - **do not include federation resources**
- registration:
  - disabled (OIDC only)
- media:
  - `max_upload_size` set to match nginx body size
  - `media_store_path` persisted

## 3) OIDC provider configuration
Configure Synapse OIDC provider using the EquipeMed issuer/discovery.

Hard requirement:
- Use the **real public issuer** (`${OIDC_ISSUER}`) even if Synapse reaches it via `host-gateway`.

## 4) Admin API
Enable Synapse admin API so EquipeMed can:
- deactivate users when they are disabled in EquipeMed
- (optionally) create bot user access tokens

Store admin access token securely (env var / secrets), not in git.

## 5) Federation is disabled (defense in depth)
- Listener config does not serve federation resources
- Host nginx blocks `/_matrix/federation/*`
- Do not expose port `8448`

## Exit Criteria
- Synapse starts cleanly and serves:
  - `GET https://${MATRIX_FQDN}/_matrix/client/versions`
- OIDC provider is correctly configured (login button appears in clients)
- Upload size limits are consistent between nginx and Synapse
