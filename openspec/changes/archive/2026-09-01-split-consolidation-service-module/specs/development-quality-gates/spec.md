# Development Quality Gates Specification Delta

## ADDED Requirements

### Requirement: Consolidation service modules stay split by responsibility

The patients consolidation service SHALL keep plan parsing/validation,
review/skeleton presentation, and plan execution in separate modules,
with `patient_record_consolidation` acting as the facade that
re-exports the public surface.

#### Scenario: Facade preserves the public surface

- **WHEN** an importer (command, prefill, tests) uses names from
  `patient_record_consolidation`
- **THEN** every previously public name remains importable from the
  facade, without any importer change

#### Scenario: Executor keeps marker ownership

- **WHEN** a consolidation plan is executed
- **THEN** void markers are written by the executor module
  (`patient_record_consolidation`), not by plan or review modules
