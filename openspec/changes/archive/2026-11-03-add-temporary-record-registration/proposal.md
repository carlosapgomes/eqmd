# Proposal: add temporary record registration

## Why

Doctors sometimes need to register a patient before the hospital registry
office has issued the definitive record number. Before the placeholder rule,
this need produced invisible chaos: a 7-patient group used `---` as the record
number, and other ad-hoc values were indistinguishable from real numbers.

The placeholder rule (archived change `2026-09-01-block-placeholder-record-numbers`)
blocked the chaotic channel, but it left the underlying need unserved: today a
doctor without the definitive number must either skip registration or type
something that looks valid. Both outcomes are worse than an explicit
temporary state.

Making the temporary state explicit converts a data-quality liability into a
managed workflow:

- temporary numbers are unmistakable (`TMP-XXXXXXXX`) and can never be
  mistaken for a real registry number;
- every temporary registration carries a mandatory reason and full audit
  trail (creator, timestamp) — already captured by existing fields;
- a pending dashboard keeps visible pressure on the structural problem
  (who creates temporaries, how long they stay unresolved), aligned with the
  prevention-plus-visibility strategy of ADR-0003.

## What Changes

1. Temporary record generation on patient creation: a checkbox replaces the
   record-number field with a server-side generated `TMP-` number plus a
   mandatory reason (stored in the existing `change_reason` audit field).
2. Prefix protection: the `TMP-` prefix is reserved for generated records;
   manually typed `TMP-` numbers are rejected at every write door
   (creation form, both record-number update forms, managed model method).
   Regularization reuses the existing record-number change flow, preserving
   history.
3. Staff-only pending dashboard: patients whose current record number is
   temporary, oldest first, with pending age and an aggregate count by
   creator.

## Out of Scope

- Database schema changes: this change requires zero migrations by design.
- Any change to import/refresh/sample-data management commands.
- Expiry notifications, automatic escalation, or scheduled jobs.
- Person-level creator analytics beyond the aggregate count (the dashboard
  aggregates by creator username; detailed audit stays in the per-row trail).
- New Django permission objects (dashboard gated by `is_staff`; documented
  trade-off in design).

## Success Criteria

- A patient can be created with a generated temporary number and a reason;
  the generated number is current and unique under the existing lifetime
  constraint.
- Manually typed `TMP-` numbers are rejected on every write door with a
  clear message.
- Regularizing a temporary number to a definitive one preserves the full
  record-number history (old row kept, `is_current=false`).
- Staff can list pending temporaries with age and creator aggregate;
  non-staff cannot.
- Full test suite green with no new lint/type findings.
