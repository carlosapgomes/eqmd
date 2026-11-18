# Page Navigation Feedback

## Purpose

Give application users accurate loading feedback for real document navigation
without blocking interactions completed in place.

## Requirements

### Requirement: Loading feedback reflects document navigation

The global page-loading overlay SHALL represent genuine same-window document
navigation, not an interaction intercepted by another controller. Cancelled
click/submit events, AJAX discovery, lookup and no-op Apply SHALL NOT leave
the overlay visible or wait for its defensive navigation timeout.
A delayed display SHALL recheck cancellation after event dispatch completes.

#### Scenario: Catalogue fragment succeeds without a page mask

- **WHEN** a catalogue link is intercepted and its fragment request succeeds
- **THEN** results become usable without a global page-navigation mask
- **AND** neither its scheduled show callback nor timeout can mask the page later

#### Scenario: Cancelled or failed interaction remains usable

- **WHEN** an intercepted request fails or a clean enhanced Apply is cancelled
- **THEN** the page-navigation overlay stays hidden
- **AND** existing inline error/draft behavior remains available for retry

#### Scenario: Genuine navigation retains feedback

- **WHEN** an ordinary eligible link or native navigation form proceeds
- **THEN** existing loading feedback remains available
- **AND** document load/pageshow clears it without waiting for the timeout
- **AND** existing external, hash, download and new-window exclusions remain

### Requirement: One loading overlay per rendered document

Every application document using the global loader SHALL expose exactly one
pageLoadingOverlay ID through the base-template hierarchy. A page without
that element SHALL remain safe. Template inheritance SHALL NOT add a second
hidden overlay or change unrelated page content.

#### Scenario: Inherited application page has a unique overlay

- **WHEN** catalogue, creation, patient list or map renders through base_app
- **THEN** its document contains exactly one pageLoadingOverlay element
- **AND** the loader controls that element consistently

#### Scenario: Loader tolerates pages without an overlay

- **WHEN** the loader runs on a document without its overlay
- **THEN** no navigation or application interaction is broken

### Requirement: Updated loading code is cache-safe

A changed global loading implementation SHALL be built through existing
Webpack tooling and referenced with a content-versioned main-bundle URL.
Previously cached unversioned assets SHALL NOT be required to expire for the
updated listener to load. This SHALL NOT change medical-data caching policy.

#### Scenario: Existing browser receives the corrected bundle

- **GIVEN** the browser cached the previous unversioned main bundle
- **WHEN** it receives current application HTML after deployment
- **THEN** that HTML requests the current content-versioned bundle
- **AND** the corrected AJAX/navigation behavior is available without clearing
  all browser data or changing service-worker cache strategy
