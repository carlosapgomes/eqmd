# dailynote-card-copy Specification

## Purpose

Define the copy behavior of the DailyNote timeline card: one-click copy
for notes that fit a single hospital field and a part-by-part copy dialog
for longer notes, with paragraph-aware splitting, per-part character
counts, copied-state feedback and explicit warnings for uncovered
content. Other event cards and the DailyNote detail page keep the shared
direct-copy behavior.

## Requirements

### Requirement: Conditional Copy Dialog on the DailyNote Timeline Card

The DailyNote timeline card copy button SHALL copy short notes directly
and SHALL open a copy dialog only when the raw note content exceeds one
hospital field (4,000 characters).

#### Scenario: Short note copies directly

- **WHEN** a user activates the copy button on a DailyNote card whose
  content has at most 4,000 characters
- **THEN** the full raw content is written to the clipboard
- **AND** a success toast is shown with the button's visual feedback
- **AND** no dialog opens

#### Scenario: Long note opens the copy dialog

- **WHEN** a user activates the copy button on a DailyNote card whose
  content has more than 4,000 characters
- **THEN** a dialog opens with a "Copiar tudo" button that writes the
  raw content verbatim
- **AND** the dialog offers one numbered part button (P1, P2, ...) per
  computed part, at most four

#### Scenario: The raw length drives the decision

- **WHEN** the raw content exceeds 4,000 characters but CRLF
  normalization shrinks it to 4,000 or fewer
- **THEN** the dialog still opens with the single available part button
  and the "Copiar tudo" button

#### Scenario: Draft notes use the same flow

- **WHEN** a user activates the copy button on a human-draft DailyNote
  card
- **THEN** the same direct-copy-or-dialog flow applies as for final
  notes

#### Scenario: Empty or whitespace-only content is rejected

- **WHEN** a user activates the copy button on a DailyNote card with no
  content or content made only of whitespace and line breaks
- **THEN** an error toast is shown, no dialog opens, and nothing is
  written to the clipboard

### Requirement: Paragraph-Boundary Part Splitting

The system SHALL split DailyNote content into parts at paragraph
boundaries, targeting 3,900 characters per part, and SHALL never produce
a part longer than 4,000 characters.

#### Scenario: Parts break at paragraph boundaries

- **WHEN** a note longer than 4,000 characters contains several
  paragraphs, none of them oversized
- **THEN** every part boundary falls on a blank-line paragraph boundary
- **AND** every part holding two or more paragraphs is at most 3,900
  characters (a single-paragraph part may reach 4,000)

#### Scenario: Every part fits a hospital field

- **WHEN** the dialog shows part buttons
- **THEN** each part button displays its character count
- **AND** every part is at most 4,000 characters

#### Scenario: Oversized paragraph splits with preserved separators

- **WHEN** a single paragraph is longer than 4,000 characters
- **THEN** the paragraph is split by lines, then by sentences, and only
  then hard-cut at 4,000 characters
- **AND** line pieces keep their single-newline separator, sentence
  pieces keep their sentence separator, and hard cuts keep no separator
- **AND** no resulting part exceeds 4,000 characters

### Requirement: Per-Part Character Counts and Copied State

The dialog part buttons SHALL show their character counts and SHALL keep
a copied indicator that persists while the dialog is open.

#### Scenario: Part buttons show counts

- **WHEN** the copy dialog opens for a long note
- **THEN** each part button shows its part number and its character
  count (for example "P1 · 3.850/4.000")

#### Scenario: Copied state persists across the paste workflow

- **WHEN** a user copies a part
- **THEN** that part button switches to a copied state (success styling
  plus a check indicator)
- **AND** the copied state persists while the dialog stays open
- **AND** copied states reset the next time the dialog opens

### Requirement: Uncovered-Content Warning for the Copy Dialog

The dialog SHALL warn explicitly when the shown part buttons do not cover
the full note content and SHALL never silently truncate content.

#### Scenario: Parts dropped by the button cap

- **WHEN** the split produces more parts than the four buttons can show
- **THEN** a warning names the total character count and the covered
  character count
- **AND** the warning explains that only the first four parts are shown

#### Scenario: Total beyond hospital capacity

- **WHEN** the total content exceeds 16,000 characters
- **THEN** the warning additionally cites the hospital capacity of four
  fields of 4,000 characters each

#### Scenario: Full copy always available

- **WHEN** any uncovered-content warning is shown
- **THEN** the "Copiar tudo" button remains available and writes the raw
  content verbatim

### Requirement: Other Cards Keep Direct Copy

The system SHALL keep the current direct-copy behavior for every
non-DailyNote event card and for the DailyNote detail page.

#### Scenario: Other event cards copy directly

- **WHEN** a user activates the copy button on a card of another event
  type (for example a simple note)
- **THEN** the content is copied directly with the existing feedback and
  no dialog opens

#### Scenario: DailyNote detail page is unchanged

- **WHEN** a user activates a copy button on the DailyNote detail page
- **THEN** the current direct-copy behavior applies
