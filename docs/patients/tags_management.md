# Tags Management

The patient tag catalogue is implemented by `apps.patients.AllowedTag` (the
catalogue entry) and `apps.patients.Tag` (a patient association). Django Taggit
is **not** the patient tagging system; it remains only as an unrelated legacy
dependency.

## Catalogue classification

Every catalogue tag has three independent attributes:

| Attribute     | Values                  | Meaning                         |
| ------------- | ----------------------- | ------------------------------- |
| Origem        | `system` / `custom`     | System-owned or locally created |
| Visibilidade  | `public` / `restricted` | Reader visibility class         |
| Especialidade | empty / one team        | Namespace; empty means global   |

- A **restricted** tag must belong to exactly one specialty team.
- A **public** tag may be global or belong to a team namespace.
- Existing tags were backfilled as `custom`/`public` in the global namespace.
  Their IDs, names, authors, patient associations and history were retained, and
  no team ownership, creator or principal tag was inferred.

## Creating and editing tags

Only administrators manage the catalogue. Use **Django Admin → Tags Permitidas**.
An operator must be an active Django-admin user and hold the relevant
`patients.add_allowedtag`, `patients.change_allowedtag` or
`patients.delete_allowedtag` permission. Staff status alone, specialty
membership and team leadership grant no catalogue authority.

The creator (`created_by`) is set from the authenticated administrator and is
read-only afterwards; edits record the acting administrator in `updated_by`.
Classification (`origin`, `visibility`, namespace) and responsibility are
administrative fields and are never inferred from labels.

## Lifecycle: active, inactive and archived

A tag has one identity across three canonical states derived from
`is_active` and `is_deleted`:

| State     | is_active | is_deleted | New assignments |
| --------- | --------- | ---------- | --------------- |
| Ativa     | true      | false      | Policy checked  |
| Inativa   | false     | false      | Denied          |
| Arquivada | false     | true       | Denied          |

Use the Django Admin bulk actions on **Tags Permitidas**:

- **Desativar tags selecionadas** — reversible inactivation;
- **Reativar tags selecionadas** — returns an inactive tag to active;
- **Arquivar tags selecionadas** — administrator soft-delete, never a physical
  delete;
- **Restaurar tags selecionadas** — administrator-only restoration.

Restoration returns the **same row inactive**; it never clones, recreates or
reactivates the tag. A separate activation is required. Every transition keeps
the catalogue ID, name reservation, patient associations, principal mapping and
history. Archived names stay reserved, so a new row cannot reuse them with
case or whitespace variations.

Each transition records its actor and time. The latest-action fields
(`deactivated_*`, `reactivated_*`, `archived_*`, `restored_*`) supplement the
append-only `AllowedTagTransition` history, where every transition is retained
in order. Reasons are optional and never required. Failed operations roll back
without partial state.

## Responsibility transfer

`responsible_user` is the current leader allowed to manage a custom restricted
team tag. Administrators choose the new responsible leader in the tag's
**Líder responsável** field; the change is applied as a transfer and recorded
with actor, time and both leaders.

- the recipient must currently lead the tag's own specialty team (active
  membership, leadership and an active specialty);
- the creator (`created_by`) never changes;
- the former responsible user loses management rights immediately, regardless
  of authorship;
- eligibility is reevaluated when the request is submitted, so a revoked
  leader or an ineligible recipient is rejected with no side effect;
- responsibility cannot be cleared directly, transferred for public/global
  tags, or changed on archived tags.

A responsible leader may edit descriptive fields and deactivate/reactivate
their own custom restricted tag in a team they actively lead. Archival,
restoration, transfer, classification, namespace and responsibility changes
remain administrator-only. The leader-facing page is delivered by a later
slice; the server-side policy already enforces these limits.

## Reserved names

Names are reserved case-insensitively and ignoring outer spaces
(`Lower(Trim(name))`) inside each namespace, including inactive and archived
tags. The global namespace and every specialty namespace are independent, so
two teams may both own `Reavaliar`, but a third row with " REAVALIAR " in the
same namespace is rejected. PostgreSQL 15 enforces this for ordinary and
concurrent writes; the forms, services and admin validate it first. Nothing is
merged or renamed automatically.

## Principal tag per team

Open **Django Admin → Especialidades Médicas** and select **Tag Principal**:

- at most one tag per team;
- it must be `public` and belong to that team's own namespace;
- no tag is created or assigned automatically;
- a tag referenced as principal cannot become restricted or move to another
  namespace until an administrator clears or changes the mapping.

## Assigning tags to patients

1. Open a patient's detail page.
2. Select the visible tags for that patient.
3. Save the changes.

Assignments and removals are policy checked per tag on top of the clinical
patient-access and mutation gates. Any eligible team member may assign, not only
a leader:

- a **restricted** tag requires current membership in its team;
- a **principal** tag requires that membership even though it stays public and
  filterable by everyone;
- a **non-principal public** tag keeps the clinical mutation baseline;
- an authorized catalogue administrator may act on any tag;
- only **active** tags can be newly assigned, while inactive or archived
  associations remain removable by the same per-tag authority.

Every write records a timeline event in the same transaction as the association,
including the Django Admin and bulk paths. A denied request changes nothing, and
a failed event write leaves no changed association. Repeating an assignment is
rejected by the database uniqueness of patient plus catalogue tag, so a race
cannot create a duplicate association or a second event.

**Remover Tags Autorizadas** removes only the associations the caller is
authorized to remove; other teams' classifications are preserved. Tags persist
across admission, discharge and status changes until an authorized actor removes
them.

## Using tags for filtering

1. Open **Patients → All Patients**.
2. Use the tag filter to restrict the list.
3. Legacy single-tag links remain supported.

## Preflight (read-only)

Before or after applying the additive catalogue migrations, run:

```bash
docker exec eqmd_dev python manage.py preflight_team_tags
```

The command only reads data. It reports the live schema state, normalized-name
collisions per namespace, restricted tags without a team, invalid principal
mappings and how much legacy tag history can be resolved against the retained
catalogue history (`known`, `ambiguous`, `unresolved`). Resolution of reported
collisions, mappings or legacy events requires an explicit operator decision;
the command never changes rows.

Legacy tag events only kept tag names. A legacy event is linked to a stable
catalogue tag only when exactly one identity provably carried that name when the
event happened, using the retained catalogue history. Ambiguous or unresolvable
legacy events keep their stored content untouched and are never guessed.

## Current limitation

Lifecycle, responsibility, assignment policy, atomic audited writes and stable
event references are delivered together. Restricted tag metadata is still **not**
hidden from every reader: assignment policy and audit immutability do not protect
names, colors or notes on list, detail, map, filter and timeline surfaces. Do not
create production restricted catalogue data until the privacy slice closes every
reader. The leader page is delivered by a later slice.
