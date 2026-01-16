## ADDED Requirements
### Requirement: Admin-managed Matrix identity
The system SHALL store an admin-selected Matrix localpart on each user profile and use it to construct the user's MXID.

#### Scenario: Admin sets localpart
- **WHEN** an admin saves a user profile with matrix localpart "joao.silva"
- **THEN** the system records it and computes the Matrix ID as "@joao.silva:<matrix_fqdn>"

### Requirement: Admin provisioning of Matrix users
The system SHALL allow admins to provision Matrix accounts via the Synapse Admin API and link them to the user profile UUID using external_ids.

#### Scenario: Provisioning creates Matrix account
- **WHEN** an admin triggers Matrix provisioning for a user with a saved localpart
- **THEN** the system creates or updates the Matrix user with external_ids containing the profile UUID and records a successful provisioning

### Requirement: OIDC login requires pre-provisioned Matrix account
The Synapse OIDC configuration SHALL disallow new-user creation and only allow existing users linked by the profile UUID.

#### Scenario: Login for unprovisioned user
- **WHEN** a user attempts OIDC login without a pre-provisioned Matrix account
- **THEN** Synapse denies the login and no Matrix user is created

### Requirement: Matrix binding auto-created on provisioning
The system SHALL auto-create and auto-verify a MatrixUserBinding when provisioning succeeds.

#### Scenario: Provisioning updates binding
- **WHEN** a Matrix user is provisioned for an EQMD user
- **THEN** a MatrixUserBinding exists with the chosen MXID and is marked verified
