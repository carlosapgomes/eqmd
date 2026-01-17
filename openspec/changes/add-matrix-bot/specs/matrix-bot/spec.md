## ADDED Requirements

### Requirement: Bot DM Rooms

The system SHALL provision a single Matrix DM room per EQMD user for bot interaction and store the room ID for reuse.

#### Scenario: Provision DM for active user

- **WHEN** an admin triggers bot DM provisioning for an active user
- **THEN** the system creates the DM room if it does not exist and reuses it if it already exists

### Requirement: Bot Process

The system SHALL provide a Django-managed Matrix bot process that connects with the bot access token and listens for messages.

#### Scenario: Start bot service

- **WHEN** the bot management command is executed
- **THEN** the bot connects to Synapse and begins handling DM messages

### Requirement: Binding Authorization

The system SHALL only process bot commands for Matrix users that map to active EQMD users with auto-verified Matrix bindings.

#### Scenario: Unbound Matrix user

- **WHEN** a Matrix user without a valid binding sends a bot message
- **THEN** the bot replies in Portuguese that access is unavailable and instructs the user to contact an admin

### Requirement: DM-Only Interaction

The bot SHALL respond only in the provisioned DM room for the user and refuse commands from other rooms.

#### Scenario: Command from non-DM room

- **WHEN** the bot receives `/buscar` from a room that is not the user’s provisioned DM
- **THEN** the bot replies in Portuguese asking the user to use their private room

### Requirement: Patient Search Command

The bot SHALL accept a `/buscar` command with optional prefixes (`reg:`, `leito:`, `enf:`) and free-text name terms.

#### Scenario: Combined search criteria

- **WHEN** a user sends `/buscar Maria reg:123 leito:301 enf:uti`
- **THEN** the bot applies all filters and searches by name, record number, bed, and ward

### Requirement: Search Scope and Ranking

The bot SHALL search patients with status INPATIENT or EMERGENCY, rank results by most probable match, and return at most 5 results.

#### Scenario: Top matches

- **WHEN** a search produces more than 5 inpatient matches
- **THEN** the bot returns only the 5 highest-ranked results

### Requirement: Permission Enforcement

The bot SHALL enforce existing patient access permissions for both search results and patient detail responses.

#### Scenario: Restricted search visibility

- **WHEN** a user searches for patients
- **THEN** only patients visible to the user by the current permission rules appear in results

#### Scenario: Restricted patient detail

- **WHEN** a user selects a patient they are not authorized to access
- **THEN** the bot replies in Portuguese that access is not permitted

### Requirement: Input Validation

The bot SHALL validate incoming commands for length and supported syntax before processing.

#### Scenario: Oversized command

- **WHEN** a user sends a `/buscar` command longer than 200 characters
- **THEN** the bot replies in Portuguese that the command is too long and asks the user to shorten it

#### Scenario: Unknown command

- **WHEN** a user sends an unsupported command
- **THEN** the bot replies with a short help message for `/buscar`

### Requirement: State Management

The bot SHALL keep at most one active search selection per DM room and expire pending selections after inactivity.

#### Scenario: New search overrides pending selection

- **WHEN** a user starts a new `/buscar` while a selection is pending
- **THEN** the previous selection state is discarded and replaced

#### Scenario: Selection timeout

- **WHEN** a pending selection is idle for 5 minutes
- **THEN** the bot clears the state and asks the user to start a new search

### Requirement: Selection and Demographics

The bot SHALL present results as a numbered list and display demographics for the selected patient.

#### Scenario: User selects a patient

- **WHEN** the user replies with a result number
- **THEN** the bot shows full name, birthdate, gender, record number, admission date, and length of stay in days

### Requirement: Error Handling

The bot SHALL provide clear Portuguese error messages for common failures.

#### Scenario: No search results

- **WHEN** no patients match the search criteria
- **THEN** the bot replies that no patients were found

#### Scenario: Invalid selection

- **WHEN** the user replies with a number that is out of range
- **THEN** the bot replies that the selection is invalid and asks for a valid number

#### Scenario: Internal error

- **WHEN** the bot encounters a system error during search or response rendering
- **THEN** the bot replies that the system is temporarily unavailable

### Requirement: Audit Logging

The system SHALL write JSONL audit entries for bot queries and responses including user, timestamp, room, action, and message text.

#### Scenario: Log chat interaction

- **WHEN** the bot receives a `/buscar` command and replies
- **THEN** two JSONL entries are written to the audit log file (inbound and outbound)

### Requirement: Audit Log Rotation

The system SHALL rotate the bot audit log daily and retain logs for 60 days.

#### Scenario: Daily rotation

- **WHEN** a new day begins
- **THEN** the bot audit log rotates and older logs are retained up to 60 days
