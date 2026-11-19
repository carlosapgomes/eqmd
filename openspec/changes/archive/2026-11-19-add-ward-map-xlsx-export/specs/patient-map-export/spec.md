# Ward-map XLSX export delta

## ADDED Requirements

### Requirement: Export mirrors the applied map result

The system SHALL export the ward map's current search/filter result as one
XLSX workbook download, resolved with the same viewer projection and
permission gates as the map page, and SHALL keep the requesting page on
`/patients/map`. A cached row whose patient is absent from the live
database SHALL be omitted entirely (identity and evolution included).

#### Scenario: Export equals the rendered rows

- **GIVEN** a warm cache and a map result for a given query string
- **WHEN** the user exports with the same query string
- **THEN** the workbook contains exactly the patients rendered by the map
- **AND** no patient outside the applied filters is included

#### Scenario: A patient removed from the live state is not exported

- **GIVEN** a cached row whose patient was soft-deleted during the cache
  TTL
- **WHEN** the workbook is built
- **THEN** that row is omitted entirely, identity and evolution included
- **AND** the build does not fail on the missing identity lookup

#### Scenario: Download leaves the page in place

- **WHEN** the export response arrives
- **THEN** the response is an XLSX attachment with a timestamped filename
- **AND** the browser remains on `/patients/map`

#### Scenario: Anonymous export is redirected to login

- **GIVEN** an anonymous request to the export endpoint
- **THEN** the request is redirected to the login flow without a file

#### Scenario: Missing map permission is refused

- **GIVEN** an authenticated user without `patients.view_patient`
- **WHEN** the user requests the export endpoint
- **THEN** the request is refused without a file

### Requirement: One sheet per surviving ward

The system SHALL create one sheet per ward that survives the applied
filters, in the map's ward order, each with the fixed columns `Leito`,
`Identificação`, `Médico/Interno`, `Evolução` and `Conduta` in that order,
with `Conduta` left blank for every row.

#### Scenario: Each ward result becomes one sheet

- **GIVEN** a map result with three wards carrying patients
- **WHEN** the user exports
- **THEN** the workbook has one sheet per ward in the map's ward order
- **AND** each sheet lists only that ward's patients

#### Scenario: An empty retained ward still has a sheet

- **GIVEN** `show_empty_wards` keeps a ward visible while other wards match
- **WHEN** the user exports
- **THEN** that ward's sheet exists with only its header row

### Requirement: Patient identification block

`Identificação` SHALL be one labeled multi-line cell containing name, sex,
age, record number, admission date in `DD/MM/AAAA` and inpatient days;
labels SHALL always be present with blank values when missing, except that
the inpatient-days line SHALL be omitted when no admission date exists.

#### Scenario: Full identification renders in one cell

- **GIVEN** an inpatient with complete identity fields and an admission date
- **WHEN** the workbook is built
- **THEN** the `Identificação` cell contains the six labeled lines with the
  patient's name, sex label, age, record number, admission date and day
  count

#### Scenario: Missing fields keep their labels blank

- **GIVEN** an inpatient without a record number and without an admission
  date
- **WHEN** the workbook is built
- **THEN** the Registro line keeps its label with a blank value
- **AND** no Internação line is present

#### Scenario: A status change inside the cache window keeps the row

- **GIVEN** a cached row whose patient was discharged minutes after the
  snapshot
- **WHEN** the workbook is built
- **THEN** the row is exported normally with live identity data
- **AND** only a patient absent from the live database is omitted

### Requirement: Latest published evolution only

`Evolução` SHALL hold the content of the patient's most recent published
daily note and `Médico/Interno` SHALL hold that note's author; drafts and
deleted notes SHALL be excluded; when no published note exists both cells
SHALL be blank.

#### Scenario: The most recent published note wins

- **GIVEN** a patient with two published notes at different times
- **WHEN** the workbook is built
- **THEN** `Evolução` holds the newer note's content
- **AND** `Médico/Interno` holds the newer note's author

#### Scenario: Equal timestamps break deterministically

- **GIVEN** two published notes for one patient with identical
  `event_datetime` and `created_at`
- **WHEN** the workbook is built
- **THEN** the note with the newest primary key is exported
- **AND** its author and content are exported together

#### Scenario: Drafts never leak into the export

- **GIVEN** a patient whose newest notes are a bot draft and a pending human
  draft, plus one older published note
- **WHEN** the workbook is built
- **THEN** only the older published note is exported

#### Scenario: No evolution leaves the cells blank

- **GIVEN** a patient without any published note
- **WHEN** the workbook is built
- **THEN** `Médico/Interno` and `Evolução` are both blank

### Requirement: Cells are literal text

All exported values SHALL be written as literal text with an explicit
string data type; a formula-like prefix SHALL NOT create a formula cell,
and XML-illegal control characters SHALL be stripped from every exported
value.

#### Scenario: A formula-like note stays text

- **GIVEN** a published note whose content begins with `=`
- **WHEN** the workbook is built, saved and reopened
- **THEN** the `Evolução` cell holds the literal text and is not a formula

#### Scenario: Illegal control characters are stripped

- **GIVEN** a published note containing an XML-illegal control character
- **WHEN** the workbook is saved
- **THEN** the save succeeds and the cell omits the illegal character

### Requirement: Sheet titles and readability

Sheet titles SHALL be the sanitized ward abbreviation capped at 31
characters without Excel-forbidden characters (`: \ / ? * [ ]`); when the
sanitized abbreviation is empty the sanitized ward name SHALL be used,
and when that is also empty the deterministic base `Ala` SHALL be used;
titles SHALL be deduplicated case-insensitively on collision, including
against suffixed titles; columns SHALL have the fixed widths 12, 48, 32, 72
and 45.

#### Scenario: Forbidden characters are stripped

- **GIVEN** a ward whose abbreviation contains a forbidden character
- **WHEN** the workbook is built
- **THEN** the sheet title omits that character and stays within 31
  characters

#### Scenario: Colliding sanitized titles are deduplicated

- **GIVEN** two wards whose sanitized abbreviations collide
- **WHEN** the workbook is built
- **THEN** each sheet has a distinct title via a numeric suffix

#### Scenario: A ward with no usable title text gets a base title

- **GIVEN** a ward whose abbreviation and name both sanitize to empty
- **WHEN** the workbook is built
- **THEN** the sheet title uses the deterministic base `Ala`

#### Scenario: Case-only collisions are deduplicated

- **GIVEN** two wards whose sanitized abbreviations differ only by letter
  case
- **WHEN** the workbook is built
- **THEN** each sheet has a distinct title via a numeric suffix

#### Scenario: Fixed column widths are applied

- **WHEN** any sheet is built
- **THEN** the five columns carry the fixed widths 12, 48, 32, 72 and 45

### Requirement: Export availability control

The export button SHALL sit above the map results and outside the filter
form; it SHALL be enabled when the filtered result has patients and
disabled, without an `href` and with `aria-disabled="true"`,
`tabindex="-1"` and an explanatory `title`, when the filtered result has no
patients; the endpoint SHALL refuse an empty-result request with 409 and no
file. No other criterion SHALL disable the button.

#### Scenario: Empty result disables the button

- **GIVEN** a warm cache and filters that match no patient
- **WHEN** the map renders
- **THEN** the export anchor has no `href`, is marked disabled and carries
  an explanatory title

#### Scenario: A cold cache falls under the same rule

- **GIVEN** an expired cache so the map shows the updating alert and an
  empty result
- **WHEN** the map renders
- **THEN** the export anchor is disabled by the empty-result rule alone

#### Scenario: Direct empty export is refused

- **GIVEN** filters that match no patient
- **WHEN** the export endpoint is requested directly
- **THEN** the response is 409 with an explanatory message and no file
