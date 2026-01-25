## ADDED Requirements

### Requirement: Drug Template Name Search Indexing

The system SHALL maintain a database index optimized for accent-insensitive substring search on drug template names.

#### Scenario: Accent-insensitive substring search

- **WHEN** a user searches for a partial drug name using substring matching
- **THEN** results include matches regardless of case or accents
- **AND** the query is supported by a trigram index on the normalized name

### Requirement: Autocomplete Search Normalization

The system SHALL apply the same accent-insensitive normalization used in drug template lists to autocomplete drug searches.

#### Scenario: Autocomplete matches accented names

- **WHEN** a user types a partial drug name in the autocomplete field
- **THEN** results include matches regardless of case or accents
