# Development Quality Gates Specification Delta

## MODIFIED Requirements

### Requirement: Enforced green repository baseline

The repository SHALL require green static, migration, lifecycle-fixture, and
full-test gates before blocked critical clinical changes resume, and the
full-test gate SHALL be wall-clock independent.

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

#### Scenario: Full suite is wall-clock independent

- **GIVEN** day-scoped dashboard tags and date-rendering assertions share the
  active timezone basis
- **WHEN** the full test suite runs at any wall-clock time
- **THEN** `./scripts/test.sh` exits 0 with zero failures and errors
- **AND** no date-boundary failure appears during the local late-evening or
  post-midnight window

#### Scenario: Divergent timezone does not break date assertions

- **GIVEN** the timezone-consistent tag and assertion anchors are in place
- **WHEN** the date-boundary-affected test modules run under a divergent
  `TIME_ZONE` whose local clock sits in the late-evening window
- **THEN** every module passes with zero failures
- **AND** the same modules also pass under the project `TIME_ZONE`
