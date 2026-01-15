# Phase 1: Infrastructure (Docker + Nginx + Postgres) ✅ **COMPLETED**

## Goal
Add Synapse + Element Web to the current `docker-compose.yml` with minimal exposure:
- Public access only through your **existing host nginx reverse proxy**
- Service-to-service traffic over the **Docker internal network**

## ✅ Implementation Status: COMPLETED

**Completed Date**: January 15, 2026

**Implementation Details**: 
- All infrastructure components successfully implemented
- Docker services configured and tested
- Database bootstrap completed with proper permissions
- Configuration generation system working
- Nginx templates created for production deployment
- Federation properly disabled for security
- Documentation created in `docs/matrix/phase1-infrastructure-setup.md`

## 0) Standardize domain variables (single source of truth)
Add these to `.env` and reuse them everywhere (compose + generated configs):
```bash
EQMD_DOMAIN=yourhospital.com
MATRIX_FQDN=matrix.${EQMD_DOMAIN}
CHAT_FQDN=chat.${EQMD_DOMAIN}
MATRIX_PUBLIC_BASEURL=https://${MATRIX_FQDN}/
OIDC_ISSUER=https://${EQMD_DOMAIN}/o
```

## 1) Decide versions (pin them)
Do not use `:latest` for Synapse/Element.
- Choose a Synapse version `SYNAPSE_VERSION` and Element Web version `ELEMENT_VERSION`.
- Use the same versions throughout config generation and deployment.

## 2) PostgreSQL: create a dedicated DB/user
Create a new database and user in the existing Postgres container (names are examples):
- database: `matrix_db`
- user: `matrix_user`
- password: `${MATRIX_DATABASE_PASSWORD}`

Keep Synapse data separate from EquipeMed tables for backup/restore clarity.

## 3) docker-compose additions (high-level)
Add services:
- `matrix-synapse`
  - bind `127.0.0.1:8008:8008` (host-only, nginx forwards)
  - mount `./matrix/` into `/data` (config + signing keys + media store)
  - connect to `postgres` via the compose network
- `element-web`
  - bind `127.0.0.1:8080:80` (host-only, nginx forwards)
  - mount `./element/config.json`

Avoid `deploy.resources` unless you actually deploy via Swarm; prefer host-level limits or container runtime limits.

## 4) Files/directories to create
Create:
```
matrix/
  homeserver.yaml.template
  homeserver.yaml
  log_config.yaml
  signing.key (generated)
  media_store/ (volume or bind)
element/
  config.json.template
  config.json
nginx/
  matrix.conf.template (or include snippet for existing nginx)
  matrix.conf (rendered)
```

## 5) Host nginx routing (conceptual)

### `${MATRIX_FQDN}` (Synapse client-server API)
- Proxy `/_matrix/*` and `/_synapse/client/*` to `http://127.0.0.1:8008`
- Set `client_max_body_size` to support images/audio/pdfs (e.g. 50–100MB)
- Block federation endpoints explicitly (defense in depth):
  - return `404` for `/_matrix/federation/*`

### `${CHAT_FQDN}` (Element Web)
- Proxy `/` to `http://127.0.0.1:8080`
- Serve `/.well-known/matrix/client` (can be served on either `${MATRIX_FQDN}` or `${CHAT_FQDN}`; pick one and be consistent)

## 6) Synapse reaching EquipeMed OIDC (Docker → host nginx)
Because the OIDC issuer and endpoints are on your **public domain** (e.g. `https://${EQMD_DOMAIN}`), the Synapse container must resolve that domain to the host.

Recommended approach (Linux Docker):
- Add in `matrix-synapse` service:
  - `extra_hosts: ["${EQMD_DOMAIN}:host-gateway"]`

This lets the Synapse container reach `https://${EQMD_DOMAIN}` via the host nginx, while still using correct TLS hostname/issuer.

## Exit Criteria
- `docker compose up -d postgres`
- `docker compose up -d matrix-synapse element-web` (with placeholder config in place)
- Host nginx routes:
  - `https://${MATRIX_FQDN}/_matrix/client/versions` returns JSON
  - `https://${CHAT_FQDN}` loads Element
