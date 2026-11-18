# Tasks: Report-template tag editor UX

## 1. Usable classification on create and update

- [x] 1.1 RTTE-S1 — Deliver searchable multiple selection, removable chips and
      explicit empty submission on both shared editor surfaces, preserving
      field drafts, current authority and native fallback.
      Contract: [RTTE-S1](slices/slice-001-edit-template-tags.md).
      Report: /tmp/sirhosp-slice-RTTE-S1-report.md.

## Execution Boundary

One vertical slice is sufficient because creation/update already share
ReportTemplateForm, reporttemplate_form.html and association persistence.
Do not split this into separate backend, create and update tasks.

This is planning, not implementation approval. RTFA-S1/S2 are an accepted
working-tree baseline, not permission to modify or close that separate change.
No canonical sync, task completion, archive or Git write is authorized here.
The implementer runs the approved slice, collects evidence and stops for review.

## Closure — 2026-11-18

The operator authorized synchronization and archival after integrating the
implementation into main at commit `0a2a560`. The execution-boundary text above
records the original planning restrictions, not outstanding implementation.
All listed slices are complete; execution results and review limitations are
recorded in [verification](verification.md#execution-record--2026-11-18).
No application changes or Git writes are part of this closure.
