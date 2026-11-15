# Proposal: Report template tag discovery

## Why

Public report templates from multiple specialties share the same lists, making
relevant models difficult to find. Reusing the existing tag catalogue and
specialty defaults improves discovery without turning specialty classification
into a new access restriction.

## What Changes

- Allow authorized editors to associate zero or more existing tags when creating
  or updating a report template; never create catalogue tags from this form.
- Preserve current template ownership, administrative editing exceptions and
  public/private visibility.
- Offer tag filtering and dynamic name search in both `/reports/templates/`
  and the template selector used to create a patient's report.
- Reuse the patient list/map's saved specialty preferences, principal fallback,
  ANY/ALL modes, explicit clear and reapply semantics.
- Preserve restricted tag metadata visibility independently of template access.
- Leave existing templates untagged until an authorized editor classifies them.
  Active tag predicates exclude untagged templates; clearing restores them.
- Audit association changes technically in the data layer, without a new history
  screen, patient tag events or changes to already-created reports.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reports`: optional template classification, authorized association editing,
  requester-safe metadata and consistent discovery on both report surfaces.

The existing `patient-tag-filtering` and `team-tag-governance` capabilities
are reused, not changed. This proposal does not alter the Modelos hub or its
category-specific access rules.

## Impact

- Schema: optional report-template-to-catalogue associations and their audit
  history; no data backfill or change to patient/report records.
- Backend: `apps/reports/` models, forms, services, views, URLs and tests.
- UI: report-template editor/list and report-creation selector; source assets
  under `assets/`, distributed using the existing Webpack build.
- Dependencies: existing Django, PostgreSQL and django-simple-history only.
- Existing report rendering, placeholders, PDFs, duplication and manual
  creation remain unchanged.
- No breaking URL or submitted report-field changes are intended.

## Non-Goals

Drug/prescription templates, SampleContent, new tag governance, new preferences
storage, automatic template classification, tag inheritance by clinical
documents, an audit-history UI and a replacement for the current
application workflow.

## Review Clarifications

The operator accepted loading historical tag choices without navigation on both
enhanced discovery surfaces, and technical audit inspection without a new UI.
Slice handoffs must identify the actual reusable interfaces; browser proof follows
an explicit fixture-ownership and reproducibility contract in `verification.md`.
Sharing patient-list/map defaults does not require an identical tag widget or
HTTP error transport.

## Delivery Boundary

Planning only at change creation. Three sequential vertical slice contracts
will deliver classification, catalogue discovery and report-form discovery.
Implementation, shared-database migration and release remain separate actions.
