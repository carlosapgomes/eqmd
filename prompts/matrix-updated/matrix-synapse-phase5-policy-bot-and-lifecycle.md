# Phase 5: Policy Enforcement + Bot Rooms + User Lifecycle Coupling

## Goal
Make the behavior match your rules even with Element mobile:
- Users cannot create rooms
- Users cannot invite
- Only bot/admin can create:
  - per-user bot DM room
  - one global room
- E2EE is off by default and cannot be enabled
- Disabled EquipeMed users lose Matrix access immediately (no lingering sessions)

## 1) Synapse policy module (server-side enforcement)
Implement a small Synapse module mounted into the Synapse container.

It MUST enforce:
- **Block room creation** for normal users (allow only bot + admins).
- **Block invites** for normal users (allow only bot + admins).
- **Block encryption enablement**:
  - deny `m.room.encryption` state events in all rooms (recommended: deny for everyone).

Configuration inputs:
- list of admin user ids (or a regex)
- bot user id

This is the cornerstone that makes the design safe across web + mobile clients.

## 2) Bot account
Create a dedicated bot Matrix user (example):
- `@eqmd_bot:${MATRIX_FQDN}`

Recommended approach:
- Create via Synapse admin API or via registration shared secret.
- Generate a long-lived access token for the bot and store it as a secret for the bot service to use.

## 3) Room provisioning logic

### 3.1 Per-user DM room
When an EquipeMed user becomes active:
- ensure a Matrix user exists (it will be created on first SSO login, but provisioning can pre-create)
- bot creates (or reuses) the DM room and invites the user
- store the DM room id in EquipeMed DB (recommended)

### 3.2 Global room
Admin (or bot on admin’s behalf):
- creates the global room
- invites all active users (initially and on new activations)

## 4) Lifecycle coupling (disable user => cut access)
When EquipeMed user is disabled/inactive:
- call Synapse admin API to **deactivate the Matrix account** (this should invalidate access tokens/sessions for that user)
- kick/ban from the global room

Also handle reactivation:
- reactivate Matrix user (or recreate if you choose)
- re-invite to global room

## 5) Where this code lives (suggested)
Add a Django app (e.g. `apps/matrix_integration/`) providing:
- models: Matrix user id, DM room id, global room id
- management commands:
  - provision bot user / token
  - provision DM rooms for active users
  - sync deactivations
- optional admin actions for “provision now”

Avoid assuming Celery exists; use explicit management commands + cron/systemd timer unless you already run a job queue.

## Exit Criteria
- Attempting to create a room as a normal user fails (web + mobile).
- Attempting to enable E2EE fails (web + mobile).
- New active user gets:
  - a DM room with the bot
  - access to the global room (if you want this)
- Disabling a user in EquipeMed deactivates their Matrix account and blocks further access.
