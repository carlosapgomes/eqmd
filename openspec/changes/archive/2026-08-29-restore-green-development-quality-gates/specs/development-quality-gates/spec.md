# Development Quality Gates Specification Delta

## ADDED Requirements

### Requirement: Deterministic supported Django runtime

Development Docker, CI, and lock resolution SHALL use the same project-approved
Django minor line. The approved line SHALL be Django 5.2 LTS until a separate
framework-upgrade change supersedes this decision.

#### Scenario: Dependency resolution stays on the approved minor line

- **GIVEN** a clean checkout with the committed dependency declaration and
  lockfile
- **WHEN** production and development dependencies are resolved
- **THEN** Django resolves to a version greater than or equal to 5.2.1 and less
  than 5.3
- **AND** local Docker and CI report the same resolved Django version
- **AND** dependency verification does not modify the lockfile

#### Scenario: Unsupported framework drift fails closed

- **GIVEN** the lockfile or running environment resolves an unsupported Django
  minor or major line
- **WHEN** the runtime parity gate runs
- **THEN** the gate returns a nonzero exit code
- **AND** the mismatch is reported explicitly
- **AND** no generated third-party migration is accepted as a workaround

#### Scenario: Legacy OIDC primary keys remain migration-stable

- **GIVEN** vendor OIDC migrations and retained PostgreSQL columns use
  `AutoField`
- **WHEN** Django loads the OIDC application under the project-wide
  `BigAutoField` default
- **THEN** a project-owned OIDC AppConfig selects `AutoField` for that app only
- **AND** the project-wide default remains unchanged
- **AND** the global migration-drift gate exits 0 without a generated vendor
  migration or schema alteration

### Requirement: Reproducible non-mutating development tools

Ruff, Mypy, and their declared configuration SHALL be installed from committed
dependency metadata during environment construction. Quality scripts SHALL
never install or upgrade packages in a running container.

#### Scenario: Required tool is available in a built development environment

- **GIVEN** a development image built from committed metadata
- **WHEN** Ruff and Mypy version checks run
- **THEN** both commands are available without package installation
- **AND** their versions satisfy committed constraints

#### Scenario: Missing tool fails without mutation

- **GIVEN** a required quality tool is absent
- **WHEN** a quality script runs
- **THEN** the script returns a nonzero exit code with remediation guidance
- **AND** the script does not invoke `pip install`, `uv pip install`, or run as
  root to mutate the environment

### Requirement: Contract-first failing-test repair

Every failing-test cohort SHALL be repaired against an explicit authoritative
contract. A stale test MAY be updated when evidence proves its assumption is
obsolete. Production behavior MAY change only when a regression test and an
authoritative contract prove a production defect.

#### Scenario: Legacy fixture no longer matches a model contract

- **GIVEN** a failing test uses a removed field, constructor argument, relation,
  or lifecycle default
- **WHEN** current specs, migrations, and supported factories prove the test
  fixture is stale
- **THEN** only the fixture/setup is updated
- **AND** the original business assertion remains at least as strict
- **AND** the focused module finishes with zero failures and errors

#### Scenario: Current production behavior violates an authoritative contract

- **GIVEN** a failing test reveals behavior inconsistent with a current spec or
  accepted domain rule
- **WHEN** the cohort is repaired
- **THEN** a behavior-level RED test is recorded
- **AND** production code receives the smallest cohesive fix
- **AND** focused and regression tests finish green
- **AND** the report includes an explicit rollback note

#### Scenario: Contract authority is ambiguous

- **GIVEN** code, tests, and documentation disagree without a clear authority
- **WHEN** the implementer cannot prove which behavior is correct
- **THEN** the slice is reported `INCOMPLETE`
- **AND** no assertion or production behavior is changed speculatively

### Requirement: Progressive module-green stabilization

Each stabilization slice SHALL make its named target command finish with exit
code 0 and zero failures/errors before the next slice begins. Known failures
outside the slice MAY remain only until their scheduled downstream slice and
MUST NOT increase or gain new unexplained failure IDs.

#### Scenario: Intermediate cohort becomes green

- **GIVEN** a recorded failing module/app baseline
- **WHEN** its stabilization slice completes
- **THEN** the target command exits 0 with zero failures/errors
- **AND** a full-suite comparison shows no new unexplained failure IDs
- **AND** a temporary Markdown report contains reproducible evidence

#### Scenario: Targeted test still fails

- **GIVEN** any failure or error remains in the target command
- **WHEN** the implementer prepares handoff
- **THEN** the slice status is `INCOMPLETE`
- **AND** its tasks remain unchecked
- **AND** the next slice does not begin

### Requirement: Enforced green repository baseline

The repository SHALL require green static, migration, lifecycle-fixture, and
full-test gates before blocked critical clinical changes resume.

#### Scenario: Full quality baseline is restored

- **GIVEN** every app cohort has completed third-LLM verification
- **WHEN** the consolidated quality gate runs
- **THEN** Django check, Ruff, formatting, Mypy scope, lock verification, and
  migration-drift checks exit 0
- **AND** `./scripts/test.sh` exits 0 with zero failures and errors
- **AND** the lifecycle fixture guard rail reports zero unapproved violations

#### Scenario: Patient-identity work resumes

- **GIVEN** the consolidated quality baseline is fully green
- **WHEN** slice 001 of
  `harden-patient-identity-and-duplicate-prevention` is rerun
- **THEN** all original slice gates must pass without a baseline waiver
- **AND** only then may tasks 1.1-1.5 be marked complete
- **AND** slice 002 remains blocked until third-LLM approval of that rerun

### Requirement: Aggregate and synthetic evidence only

Stabilization tests and reports SHALL use synthetic fixtures and aggregate test
results. They SHALL NOT query, copy, or expose identifiable restored patient
data.

#### Scenario: Slice report is generated

- **GIVEN** a stabilization slice has executed its gates
- **WHEN** its temporary report is written
- **THEN** the report contains commands, exit codes, test IDs, aggregate counts,
  and synthetic values only
- **AND** no patient-level production value is included
