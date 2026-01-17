# Matrix Reset and Rebuild

This guide wipes Synapse state (database + media) and recreates the Matrix stack.
It also includes the RS256 OIDC key setup needed by Synapse SSO.

## Scope
- Wipe Synapse database (`matrix_db`) and media store.
- Recreate Synapse containers and configs.
- Recreate RS256 keys and OIDC client (only if Django DB was wiped).

## 1) Stop Matrix services

```bash
sudo docker compose stop matrix-synapse element-web
sudo docker compose rm -f matrix-synapse element-web
```

## 2) Wipe Synapse media store (optional)

```bash
sudo docker volume rm ${CONTAINER_PREFIX:-eqmd}_matrix_media_store
```

## 3) Wipe Synapse database only (keeps Django DB)

```bash
set -a; source .env; set +a
sudo docker compose exec postgres psql -U ${POSTGRES_USER:-eqmd_user} -d postgres \
  -c "DROP DATABASE IF EXISTS matrix_db;"
sudo docker compose exec postgres psql -U ${POSTGRES_USER:-eqmd_user} -d postgres \
  -c "CREATE DATABASE matrix_db OWNER ${POSTGRES_USER:-eqmd_user};"
```

## 4) Regenerate Synapse configs

```bash
set -a; source .env; set +a
sudo docker compose exec -u root eqmd-dev python scripts/generate_matrix_configs.py
sudo chown ${EQMD_UID:-1001}:${EQMD_GID:-1001} matrix/homeserver.yaml
sudo chmod 644 matrix/homeserver.yaml
```

## 5) Start Synapse

```bash
sudo docker compose up -d matrix-synapse element-web
```

## 6) Create Synapse admin + token

`register_new_matrix_user` requires `registration_shared_secret` in
`matrix/homeserver.yaml`. If missing, add one and restart Synapse.

```bash
openssl rand -hex 32
# add to matrix/homeserver.yaml:
# registration_shared_secret: "<generated_hex>"

sudo docker compose restart matrix-synapse
sudo docker compose exec matrix-synapse register_new_matrix_user \
  -c /data/homeserver.yaml -u admin -p 'StrongPass' --admin http://localhost:8008
```

Get the admin access token and set `SYNAPSE_ADMIN_TOKEN` in `.env`:

```bash
sudo docker compose exec matrix-synapse curl -s -X POST http://localhost:8008/_matrix/client/v3/login \
  -H 'Content-Type: application/json' \
  -d '{"type":"m.login.password","identifier":{"type":"m.id.user","user":"admin"},"password":"StrongPass"}'
```

## 7) RS256 OIDC keys and client (only if Django DB was wiped)

```bash
sudo docker compose exec eqmd-dev python manage.py migrate
sudo docker compose exec eqmd-dev python manage.py creatersakey
sudo docker compose exec eqmd-dev python manage.py setup_synapse_oidc_client \
  --client-id matrix_synapse_client --matrix-fqdn ${MATRIX_FQDN}
```

Update `.env` with the printed `SYNAPSE_OIDC_CLIENT_SECRET`, then regenerate configs:

```bash
set -a; source .env; set +a
sudo docker compose exec -u root eqmd-dev python scripts/generate_matrix_configs.py
sudo chown ${EQMD_UID:-1001}:${EQMD_GID:-1001} matrix/homeserver.yaml
sudo chmod 644 matrix/homeserver.yaml
sudo docker compose restart matrix-synapse
```

## 8) Verify

```bash
curl -s https://matrix.sispep.com/_matrix/client/v3/login
curl -s https://app.sispep.com/o/jwks
```

`/login` should show `id: "oidc-${SYNAPSE_OIDC_PROVIDER_ID}"` and JWKS should include at least one RSA key.

## 9) Provision users

Use Django Admin → User Profiles:
1) Set `matrix_localpart`
2) Save
3) Click **Provision Matrix User**
