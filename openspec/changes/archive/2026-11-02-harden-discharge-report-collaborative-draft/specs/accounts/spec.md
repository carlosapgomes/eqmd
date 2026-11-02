# Accounts Specification Delta

## ADDED Requirements

### Requirement: Clinical identity integrity

The system SHALL require `profession_type` for user
accounts that need clinical access. Django admin
user creation and change forms SHALL reject a
missing `profession_type` unless the user is a
superuser or belongs to `User Managers`. The
`profession_type` field SHALL stay nullable at the
schema level.

#### Scenario: Admin blocks clinical user without profession

- **WHEN** an administrator saves a regular user
  without `profession_type`
- **THEN** validation fails with a profession
  error and nothing is saved

#### Scenario: Admin allows exempt users without profession

- **WHEN** an administrator saves a superuser or a
  `User Managers` member without `profession_type`
- **THEN** validation succeeds

### Requirement: Clinical identity auditability

The system SHALL provide a read-only management
command auditing clinical identity integrity. It
SHALL report active users with `NULL`
`profession_type` (excluding superusers and `User
Managers` members), profession groups missing
expected permissions, and non-exempt users in no
profession group. It SHALL NOT modify any
database row.

#### Scenario: Audit reports gaps read-only

- **WHEN** an operator runs the audit command
- **THEN** gaps are listed grouped by kind and no
  database row is modified

### Requirement: Profession group reconciliation

`setup_groups` SHALL reconcile permissions on
existing profession groups, not only on created
ones: after the command runs, every profession
group SHALL hold exactly its specified permission
set, including groups previously created empty by
the post-save signal.

#### Scenario: Empty signal-created group gains permissions

- **WHEN** a profession group exists without
  permissions and `setup_groups` runs
- **THEN** the group holds its full specified set
