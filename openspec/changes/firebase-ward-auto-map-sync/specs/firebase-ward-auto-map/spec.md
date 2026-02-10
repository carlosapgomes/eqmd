## ADDED Requirements

### Requirement: Firebase ward references are translated during patient sync
The `sync_firebase_data` command SHALL translate Firebase ward references to EQMD `Ward` records using a maintained mapping and apply the result to admissions and patient denormalized ward fields.

#### Scenario: New admitted patient gets mapped ward
- **WHEN** a Firebase patient is imported as admitted/emergency and the ward reference resolves to a mapped EQMD ward id
- **THEN** the created active admission SHALL store that `Ward`
- **THEN** the patient denormalized `ward` SHALL match the admission ward

#### Scenario: Existing patient admission creation gets mapped ward
- **WHEN** reconciliation creates an active admission for an existing patient and the Firebase ward resolves to a mapped EQMD ward id
- **THEN** the created active admission SHALL use the mapped `Ward`

### Requirement: Approved legacy mappings are enforced
The sync SHALL enforce approved explicit mappings for legacy ward labels and retired wards.

#### Scenario: Intermediário maps to Intermediário B
- **WHEN** Firebase ward reference corresponds to legacy `Intermediário`
- **THEN** the sync SHALL map it to EQMD `Intermediário B`

#### Scenario: Retired wards map to none
- **WHEN** Firebase ward reference corresponds to `Hosp. Dia` or `Anexo`
- **THEN** the sync SHALL intentionally assign no ward (`None`)
- **THEN** the sync SHALL classify this as mapped-to-none (not unresolved)

### Requirement: Unresolved wards do not block sync
Unknown or unmapped Firebase ward references MUST NOT fail the patient sync.

#### Scenario: Unknown Firebase ward reference
- **WHEN** Firebase sends a ward reference that cannot be resolved by the map
- **THEN** sync processing SHALL continue without setting a ward
- **THEN** the command SHALL increment unresolved ward counters and emit warning details

### Requirement: Ward changes for active admissions are reconciled
For patients with an active admission, ward changes from Firebase SHALL be reconciled when a valid mapped ward differs from current data.

#### Scenario: Active admission ward differs from mapped ward
- **WHEN** an existing patient has an active admission and Firebase resolves to a different mapped ward
- **THEN** the active admission ward SHALL be updated
- **THEN** the patient denormalized ward SHALL be updated to the same ward

### Requirement: Ward clearing behavior for non-admitted statuses remains unchanged
Ward translation MUST NOT alter current behavior for statuses that are not actively admitted.

#### Scenario: Outpatient or deceased reconciliation
- **WHEN** Firebase status resolves to outpatient or deceased
- **THEN** reconciliation SHALL clear patient ward as part of status closure flow
