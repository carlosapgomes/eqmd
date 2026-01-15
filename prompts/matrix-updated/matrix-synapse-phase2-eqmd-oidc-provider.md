# Phase 2: EquipeMed as OIDC Provider (for Synapse SSO)

## Goal
Use the existing EquipeMed authentication (Django + allauth login UI) and expose OIDC endpoints that Synapse can use for SSO.

## 0) Do not hardcode domain/issuer
Use `.env` variables as the source of truth:
```bash
EQMD_DOMAIN=yourhospital.com
OIDC_ISSUER=https://${EQMD_DOMAIN}/o
MATRIX_FQDN=matrix.${EQMD_DOMAIN}
```

## Key Point: This repo already has an OIDC provider
The repo currently uses `django-oidc-provider` at `config/urls.py`:
- `path("o/", include("oidc_provider.urls", namespace="oidc_provider"))`

However, current settings in `config/settings.py` are tuned for **bot delegation** (`client_credentials` only). Synapse SSO needs an interactive flow:
- authorization endpoint (user login + consent)
- token exchange
- userinfo and jwks
- discovery metadata

## 1) Decide endpoint base path
Option A (keep default): OIDC under `/o/`
- Issuer: `${OIDC_ISSUER}` (example: `https://${EQMD_DOMAIN}/o`)
- Discovery: `https://${EQMD_DOMAIN}/o/.well-known/openid-configuration`

Option B (custom paths): add aliases for prettier endpoints (optional)
- Only do this if you can maintain it long-term.

## 2) Enable interactive grant types for Synapse
Update `OIDC_PROVIDER` settings to support what Synapse needs:
- `authorization_code` grant (interactive)
- `token` response types as needed

Keep `client_credentials` enabled for existing bot delegation if you already use it.

## 3) Claims and stable subject
Expose stable user identity for Synapse mapping:
- `sub`: stable EquipeMed user id (or UUID)
- `name`: full name (display name)
- `preferred_username`: optional human-friendly username
- `eqmd_active`: boolean (recommended)

Rationale:
- Synapse can map the Matrix localpart from `sub` to avoid rename/collision problems.

## 4) Access control: disabled users cannot authenticate
Ensure OIDC authorization denies inactive/disabled users:
- If EquipeMed user `is_active=False`, the OIDC authorization flow must not complete.

This blocks new logins, but does not necessarily kill existing Synapse sessions; Phase 5 handles that.

## 5) Register Synapse as an OIDC client
Create an OIDC client in EquipeMed for Synapse:
- redirect URI(s): `https://${MATRIX_FQDN}/_synapse/client/oidc/callback` (exact path depends on Synapse version; confirm after pinning)
- client type: confidential
- client secret: generated and stored as `${SYNAPSE_OIDC_CLIENT_SECRET}`

## Exit Criteria
- From outside (and from inside the Synapse container), these are reachable:
  - OIDC discovery (`openid-configuration`)
  - JWKS endpoint
  - Authorization endpoint (redirects to login)
  - Token endpoint
- You can complete a browser-based authorization flow against EquipeMed.
