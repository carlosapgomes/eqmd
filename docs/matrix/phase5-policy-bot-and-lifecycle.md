# Phase 5: Policy Bot + Lifecycle

## Goals

- Enforce room creation/invite and encryption restrictions at Synapse.
- Provision a bot account that creates per-user DMs and the global room.
- Deactivate Matrix accounts when EQMD users become inactive.

## Synapse Policy Module

Module file: `matrix/modules/eqmd_policy.py`

Configured in `matrix/homeserver.yaml` via:

```yaml
modules:
  - module: "eqmd_policy.EqmdPolicyModule"
    config:
      admin_users: "${MATRIX_ADMIN_USERS}"
      bot_user_id: "${MATRIX_BOT_USER_ID}"
      block_room_creation: true
      block_invites: true
      block_encryption: true
```

Restart the Synapse service after updating the module or config.
The Synapse admin API is served on the same listener as the client API.

## Environment Variables

Required for runtime commands:

- `SYNAPSE_ADMIN_TOKEN`
- `MATRIX_BOT_ACCESS_TOKEN`

Optional (defaults shown in `.env.example`):

- `MATRIX_ADMIN_INTERNAL_URL` (default `http://matrix-synapse:8008`)
- `MATRIX_CLIENT_INTERNAL_URL` (default `http://matrix-synapse:8008`)
- `MATRIX_BOT_USER_ID` (default `@rzero_bot:${MATRIX_FQDN}`)
- `MATRIX_BOT_DISPLAY_NAME` (default `EquipeMed Bot`)
- `MATRIX_ADMIN_USERS` (comma-separated Matrix user IDs in `@<localpart>:${MATRIX_FQDN}` format)
- `MATRIX_GLOBAL_ROOM_NAME`

## OIDC Connectivity Note

If you are using Cloudflare Tunnel for `app.sispep.com`, do not override DNS inside the Synapse container.
Remove any `extra_hosts` mapping for `${EQMD_DOMAIN}` in `docker-compose.yml`, then recreate the container so it resolves the public domain.

## Bot Setup

Create the bot user and generate a token:

```bash
python manage.py setup_matrix_bot
```

Save the printed token into `.env` as `MATRIX_BOT_ACCESS_TOKEN`.

Update the bot display name (optional):

```bash
python manage.py setup_matrix_bot --display-name "rzero"
```

## Bot Bootstrap (Run)

Start the bot process (long-running):

```bash
python manage.py run_matrix_bot
```

The bot command prefix is `!` (e.g., `!buscar ...`).

## Migrations

Create the new Matrix tracking tables:

```bash
python manage.py migrate
```

## Admin Provisioning (Matrix Users)

Provision Matrix users before they log in via OIDC.

1. Open Django Admin → User Profiles.
2. Set `matrix_localpart` (lowercase, memorable, no `@` or domain).
3. Save, then click **Provision Matrix User** (or select multiple profiles and use the action).
4. Confirm `matrix_provisioned_at` is set and the Matrix binding is verified.

Notes:

- If a user already has a different Matrix binding, provisioning will fail; resolve the binding first.
- Synapse uses `external_ids` with the profile UUID, so OIDC logins will only work after provisioning.

## Admin User IDs

Admin users use the same admin-managed Matrix localpart as normal users.
To find a user's Matrix localpart, check the Django admin (User Profile) or run:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); user=User.objects.get(username='admin'); print(user.profile.matrix_localpart)"
```

Then set `MATRIX_ADMIN_USERS=@<localpart>:${MATRIX_FQDN}` in `.env`.

## Provision Rooms

Create the global room and per-user DM rooms for active users:

```bash
python manage.py matrix_provision_rooms
```

Optional flags:

- `--skip-global`
- `--skip-dm`
- `--global-room-name "Your Name"`
- `--include-inactive` (re-provision inactive users too)

## Admin DM Provisioning

From Django Admin → Users list:

- Select user(s)
- Action: **(Re)provisionar sala privada do bot**

This reuses an existing DM room if one is already stored.

## Sync Lifecycle

Deactivate Matrix accounts for inactive users and kick them from the global room:

```bash
python manage.py matrix_sync_lifecycle
```

Optional flags:

- `--skip-global`
