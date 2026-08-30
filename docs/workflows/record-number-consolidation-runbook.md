# Record-Number Consolidation Operator Runbook

## Audience and Non-Negotiable Rules

This runbook is for the **project owner**. It resolves every canonical
record-number collision group on a database restored from production
and then applies the lifetime-unique migration.

- Only the project owner runs `--execute`. Implementer LLMs never run
  the consolidation against the restored database.
- The JSON decision plan lives outside the repository and is never
  committed: it carries clinical identifiers.
- No code path decides ownership automatically. Every keep, void, and
  renumber comes from the operator's reviewed plan.
- Voiding never deletes a row. The marker preserves the original
  number verbatim plus a decision reference
  (`<original>::voided::<plan_ref>:<assignment-id>`).
- Production rollout follows the same sequence, during a maintenance
  window.

## Prerequisites

- A restored PostgreSQL copy of production (development rehearsal) or
  the production database itself (real rollout).
- An operator account with staff access: its username is recorded as
  `updated_by` on every touched row.
- A secure directory outside the repository for the plan file.

## Step 1: Run the Aggregate Audit

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers
```

Expected shape (aggregate counts only, no identifiers):

```text
40 canonical record-number collision group(s) involving 86 row(s).
```

Record the numbers: the plan must cover every live group.

## Step 2: Review Per-Group Detail

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers --show-records
```

Per group this prints the canonical number plus the assignment and
patient ids. It is for the operator console only: output never
contains names, CPF, or CNS, and the detail must not be pasted into
tickets, commits, or reports.

```text
group canonical='rec100' assignments=[<uuid> ...] patients=[<uuid> ...]
```

## Step 3: Author the JSON Decision Plan

The fastest path uses the owner-authorized same-person criterion
(normalized name plus birthday equality, 2026-08-30):

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers \
  --emit-skeleton /tmp/skeleton.json --prefill
docker cp eqmd_dev:/tmp/skeleton.json ~/consolidation/plan.json
```

Groups whose every row matches the criterion come out fully drafted
(keep = current row of the earliest-created patient; current rows of
the duplicate renumber into a free `DUP-####` number; historical rows
void; rationale recorded). Mixed groups keep placeholders for manual
decisions. REVIEW every drafted group before executing: the criterion
is yours, the draft is a draft, and you remain the decision-maker.

Then complete every remaining group by hand, following this schema:

```json
{
  "plan_ref": "consol-2026-08-30",
  "groups": [
    {
      "canonical": "rec100",
      "keep": "<uuid of the rightful assignment>",
      "actions": [
        {
          "assignment": "<uuid of an erroneous historical row>",
          "action": "void",
          "rationale": "<clinical rationale, required>"
        },
        {
          "assignment": "<uuid of an erroneous current row>",
          "action": "renumber",
          "new_record_number": "<new unique number>",
          "rationale": "<clinical rationale, required>"
        }
      ]
    }
  ]
}
```

Authoring rules (the command refuses violations before any mutation):

- Cover EVERY live group from step 1; unknown, repeated, or missing
  groups abort the run.
- `keep` must be one assignment of the live group; every other row of
  the group needs exactly one action, referenced once.
- The patient's current row only accepts `renumber`; purely
  historical rows only accept `void`.
- A non-empty clinical rationale is required for every action; the
  rationale plus the plan reference is recorded on `change_reason`,
  and the operator on `updated_by`.
- Keep `plan_ref` short: a void marker costs `33 + len(plan_ref)`
  characters over the original against the 120-char column, so
  `len(plan_ref) <= 120 - len(original) - 33` (live 18-char originals
  still leave 60 spare characters).
- Renumbered numbers go through the audited append flow, which
  refuses any canonical conflict.
- Save the file outside the repository and never commit it.

## Step 4: Validate With a Dry Run

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers \
  --plan /secure/consolidation-plan.json \
  --user <operator-username> --dry-run
```

The dry run attempts every action inside a rolled-back transaction:
the database stays byte-identical afterwards. Confirm the reported
would-be end state:

```text
... would leave 0 collision group(s) involving 0 row(s)
```

If the plan is refused as unknown, stale, or incomplete, re-run the
audit: the data moved under the plan. Regenerate the plan against the
live discovery and validate again.

## Step 5: Execute (Project Owner Only)

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers \
  --plan /secure/consolidation-plan.json \
  --user <operator-username> --execute
```

Everything runs inside one transaction. After the writes, a zero
collision post-check re-runs discovery: any error or residual group
rolls back the whole plan, and nothing is committed.

```text
executed plan '<ref>': N action(s); post-check: 0 collision group(s)
```

## Step 6: Re-Run the Aggregate Audit

```bash
docker exec eqmd_dev python manage.py consolidate_record_numbers
```

Confirm zero:

```text
0 canonical record-number collision group(s) involving 0 row(s).
```

Do not proceed to the migration until this shows zero.

## Step 7: Apply the Migration

```bash
docker exec eqmd_dev python manage.py migrate patients
```

The migrations were renumbered before any environment applied the
constraint, so the order is:

- `0002_widen_record_number_column` widens
  `PatientRecordNumber.record_number` from 50 to 120. It is
  metadata-only on PostgreSQL and may safely apply before the
  consolidation is finished.
- `0003_patient_record_number_lifetime_unique` creates the lifetime
  unique constraint over `Lower(Trim(record_number))`. Its preflight
  re-verifies zero collision groups and fails closed otherwise: if
  any group reappeared, the migration aborts before the schema
  change.

Confirm the state:

```bash
docker exec eqmd_dev python manage.py showmigrations patients
```

Both `0002` and `0003` must show `[X]` after a successful run.

## Step 8: Third-LLM Verification

Hand the verifier exactly three artifacts:

1. the aggregate audit output (step 6, must show zero);
2. the `showmigrations patients` output (step 7, `0002` and `0003`
   applied);
3. the full test suite run (`./scripts/test.sh`, exit 0, zero
   failures).

## Production Rollout

During a maintenance window, repeat steps 1 through 7 against the
production database with a production-reviewed plan. The same fail
closed guarantees apply: no automatic decisions, no deletions, and no
commit without the zero collision post-check.
