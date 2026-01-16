# Phase 6: Testing, Deployment, and Ops

## Goals

- Validate end-to-end behavior on Element Web and Element mobile.
- Confirm media uploads and size limits align across nginx and Synapse.
- Ensure backups, logging, and upgrade procedures are documented and repeatable.

## Core functional tests

### 1) SSO login

- Element Web: log in via SSO and verify sync completes.
- Element mobile: log in via SSO and verify sync completes.

### 2) Policy enforcement (web + mobile)

As a normal user:

- Attempt to create a room (should be blocked).
- Attempt to invite another user (should be blocked).
- Attempt to enable encryption (should be blocked).

### 3) Bot DM provisioning

Run provisioning:

```bash
python manage.py matrix_provision_rooms --skip-global
```

Verify a 1:1 DM exists between the user and the bot, and the bot can send a message.

### 4) Global room behavior

Create or sync the global room:

```bash
python manage.py matrix_provision_rooms --skip-dm
```

Disable a user in EQMD, then sync lifecycle:

```bash
python manage.py matrix_sync_lifecycle
```

Verify the inactive user is kicked from the global room and the Matrix account is deactivated.

## Media tests

Upload the following from Element Web:

- Image
- PDF
- Audio

Confirm uploads succeed and there are no 413 errors. Verify limits align:

- `nginx/matrix.conf` -> `client_max_body_size`
- `matrix/homeserver.yaml` -> `max_upload_size`

## Deployment checklist

- Pin versions in `.env`: `SYNAPSE_VERSION` and `ELEMENT_VERSION`.
- Persist Postgres data (`postgres_data` volume).
- Persist Synapse data (`./matrix` for signing keys and logs).
- Persist Matrix media store (`matrix_media_store` volume).
- Regenerate configs after env changes:

  ```bash
  uv run python scripts/generate_matrix_configs.py
  ```

## Backups

Production backup script includes Matrix DB and media store if present:

```bash
sudo ./backup.sh
```

Standalone Matrix backups:

```bash
./scripts/backup-matrix-db.sh
./scripts/backup-matrix-media.sh
```

## Upgrade strategy

- Upgrade in a staging-like environment first.
- Read Synapse release notes for:
  - OIDC behavior changes
  - module/spam-checker API changes
  - database migrations
- After upgrading, restart services and re-run smoke tests above.

## Observability

- Nginx access logs:
  - `/var/log/nginx/matrix.access.log`
  - `/var/log/nginx/element.access.log`
- Synapse logs: `matrix/logs/homeserver.log`
- Monitor media store disk usage:

  ```bash
  docker volume ls --format "{{.Name}}" | grep matrix_media_store
  docker run --rm -v <matrix_media_store_volume>:/data alpine du -sh /data
  ```

## Exit criteria

- All tests in "Core functional tests" pass on Element Web and Element mobile.
- Backups are in place for Matrix DB and media store.
- Upgrade procedure is documented and repeatable.
