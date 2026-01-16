## 1. Implementation
- [x] 1.1 Add UserProfile fields for matrix_localpart and provisioning metadata; create migration.
- [x] 1.2 Add admin UI to edit matrix_localpart and trigger provisioning; validate localpart format/uniqueness.
- [x] 1.3 Extend SynapseAdminClient.ensure_user to send external_ids and update provisioning service to include display name.
- [x] 1.4 Create Matrix provisioning service that creates/updates the Matrix user and auto-creates/auto-verifies MatrixUserBinding.
- [x] 1.5 Update matrix_provision_rooms and matrix_sync_lifecycle to use the stored MXID (with safe fallback if unset).
- [x] 1.6 Update Synapse homeserver config/template to disable JIT OIDC user creation and allow only existing users.

## 2. Tests
- [x] 2.1 Add tests for UserProfile matrix_localpart validation and uniqueness.
- [x] 2.2 Add tests for admin provisioning flow (Synapse payload + MatrixUserBinding verified).
- [x] 2.3 Add tests for room provisioning using stored MXID.

## 3. Docs / Config
- [x] 3.1 Document required env vars and Synapse OIDC settings for pre-provisioned users.
