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
- `MATRIX_ADMIN_USERS` (comma-separated Matrix user IDs in `@u_<public_id>:${MATRIX_FQDN}` format)
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

## Migrations
Create the new Matrix tracking tables:
```bash
python manage.py migrate
```

## Admin User IDs
Admin users use the same Matrix ID mapping as normal users (based on `public_id`).
To find a user's `public_id`, check the Django admin (User Profile) or run:
```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); user=User.objects.get(username='admin'); print(user.profile.public_id)"
```
Then set `MATRIX_ADMIN_USERS=@u_<public_id>:${MATRIX_FQDN}` in `.env`.

## Provision Rooms
Create the global room and per-user DM rooms for active users:
```bash
python manage.py matrix_provision_rooms
```

Optional flags:
- `--skip-global`
- `--skip-dm`
- `--global-room-name "Your Name"`

## Sync Lifecycle
Deactivate Matrix accounts for inactive users and kick them from the global room:
```bash
python manage.py matrix_sync_lifecycle
```

Optional flags:
- `--skip-global`
