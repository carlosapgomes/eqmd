## Why
Synapse OIDC currently JIT-creates Matrix accounts using the OIDC subject, which yields non-memorable MXIDs and exposes internal identifiers. The system needs admin-controlled Matrix user provisioning with a stable UUID binding for a small, private deployment.

## What Changes
- Store an admin-selected Matrix localpart on each UserProfile.
- Add a Django admin action to provision Matrix users in Synapse using the Admin API and external_ids linked to the UserProfile UUID.
- Auto-create and auto-verify MatrixUserBinding on successful provisioning.
- Update Matrix integration services/commands to use the stored MXID instead of deriving from UUIDs.
- Update Synapse OIDC configuration to disallow new-user creation and allow only existing users linked by external_ids.

## Impact
- Affected specs: matrix-user-provisioning (new)
- Affected code: apps/accounts, apps/matrix_integration, apps/botauth, matrix/homeserver.yaml, matrix/homeserver.yaml.template
