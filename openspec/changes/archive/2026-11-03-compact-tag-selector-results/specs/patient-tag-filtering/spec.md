# Delta Spec: patient-tag-filtering

## ADDED Requirements

### Requirement: Compact accessible selector results

The tag selector search results SHALL render each visible tag as a single
compact activation row on both the patient list and the ward map. Each row
SHALL present the plain tag name, the team abbreviation at most once as a
discrete affordance, and any lifecycle state as text. The full row SHALL be
the activation target. Results already in the current selection SHALL be
identifiable and non-duplicating, and removing a selected chip SHALL restore
the matching result. The selector SHALL remain operable by keyboard and
SHALL announce searching, result counts and selection changes politely.

#### Scenario: Results show no redundant abbreviation

- **GIVEN** a team tag "CirVascular" with abbreviation "CVASC"
- **WHEN** the user opens the search results
- **THEN** the row shows the name once and the abbreviation once as a pill
- **AND** no second line repeats the abbreviation

#### Scenario: Full row activates

- **GIVEN** rendered search results
- **WHEN** the user clicks anywhere on a result row
- **THEN** the tag is added to the selection exactly once

#### Scenario: Already selected result is inert but visible

- **GIVEN** a result whose tag is already selected
- **WHEN** the user activates that row
- **THEN** the selection is unchanged and focus is preserved
- **AND** the row is labelled as selected

#### Scenario: Chip removal re-enables the result

- **GIVEN** a selected tag with its chip shown and its result inert
- **WHEN** the user removes the chip
- **THEN** the matching search result becomes activatable again
- **AND** the removal is announced politely

#### Scenario: Keyboard operation

- **GIVEN** the selector search field focused
- **WHEN** the user presses ArrowDown, moves with ArrowUp or Home and End,
  activates with Enter or Space and closes with Esc
- **THEN** results open, focus moves between rows, the tag is added and focus
  returns to the search field without clearing the term

#### Scenario: Status announcements

- **WHEN** the user searches, results load, more results are loaded or a tag
  is added or removed
- **THEN** a polite live region announces searching, found count, loaded
  count or the selection change respectively
- **AND** a stale response never overwrites newer results

#### Scenario: No-JavaScript fallback preserved

- **GIVEN** JavaScript disabled
- **WHEN** the user opens the patient list or the ward map
- **THEN** the native multi-select still submits the same filter parameters
