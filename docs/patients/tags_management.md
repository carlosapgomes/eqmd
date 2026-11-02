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

Administrators manage the whole catalogue through
**Django Admin → Tags Permitidas**. An operator must be an active Django-admin
user and hold the relevant `patients.add_allowedtag`,
`patients.change_allowedtag` or `patients.delete_allowedtag` permission. Staff
status alone, specialty membership and team leadership grant no administrative
catalogue authority.

Team leaders additionally maintain their own team's custom restricted tags on
the leader page described below; that page never grants Django Admin access.

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
remain administrator-only: the leader page described below exposes no
administrative action URL, and archive, restore, transfer and delete stay
available only through Django Admin.

## Leader team tag page

A current team leader reaches the page from the navigation entry
**Tags da Equipe**, or directly at `/patients/tags/team/<specialty-id>/`. The
team is always explicit in the URL and never changes the user's active
specialty context.

What a leader can do there:

- create a tag, which is always stored as `custom` + `restricted` in that
  team's namespace, with the acting leader as `created_by` and
  `responsible_user`;
- edit the name, description and colour of a tag they are currently
  responsible for;
- deactivate and reactivate their own tag, with the actor and time recorded.

What the page never allows, for leaders:

- choosing origin, visibility, namespace or responsibility — the server derives
  them, so forged POST values are ignored;
- creating a public, system or global tag, or a tag in a team they do not lead;
- archiving, restoring, transferring responsibility or deleting a tag;
- managing another leader's tag, a former responsible leader's tag, or a tag of
  another team (the request is denied with no catalogue or history change).

Eligibility is evaluated on every request: revoking membership or leadership
removes page access and the navigation entry on the next response, without
logging out. Names remain reserved per namespace across active, inactive and
archived tags, so a new team tag cannot reuse an archived name with case or
space variations. The page shows only the addressed team's restricted tags,
each with its lifecycle label (`Ativa`, `Inativa`, `Arquivada`) and its current
responsible leader.

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
2. Search and select one or more tags in the tag selector.
3. Choose **Qualquer tag** (ANY) or **Todas as tags** (ALL).
4. Submit the filter; repeated `tags=<id>` parameters are preserved through
   refresh, pagination and badge removal.

The selector searches the requester-visible catalogue by tag name or team
abbreviation. Active visible tags are listed by default. Tick **Incluir tags
antigas** to search visible inactive/archived tags; historical results are
labelled with their team abbreviation and state and are offered for filtering
only, never for new assignment. The lookup endpoint is read-only and has no
create operation.

Explicit filter state is URL-based:

- `tags=<id>&tags=<id>` selects multiple identities (duplicates are removed);
- `tag_mode=any` matches at least one selected tag, `tag_mode=all` requires all
  of them, and other search/status/ward predicates remain conjunctive;
- `tag_filter=manual` marks an explicit manual selection, including an empty
  one, and a clear action keeps that marker so the cleared state survives
  navigation;
- the legacy `tag=<id>` bookmark remains an explicit ANY single-tag filter, and
  a present empty `tag=` means an explicitly cleared selection.

HTTP status/name/ward filtering remains conjunctive and patient results stay
distinct. A forged, unknown or malformed explicit identifier returns the
generic message `Filtro de tag inválido.` with no patients instead of narrowing
or widening the list; inaccessible restricted metadata is never echoed.

### Filtering the ward map

The ward map at **Patients → Mapa de Pacientes** uses the same selector, the
same `tags`/`tag_mode`/`tag_filter` query parameters and the same saved
specialty preference as the list. Selecting tags on one surface and opening the
other keeps the same effective selection, ANY/ALL mode and manual/clear/default
precedence; the explicit save, clear and reapply actions behave identically on
both.

Differences are limited to each page's own eligibility and presentation:

- the map only shows **inpatients with a ward**, so a tag associated only with
  outpatients returns zero map rows (with zero totals) while the list still
  returns those patients;
- the header totals and each ward counter are computed from the rows actually
  rendered after filtering, never from global cached counts;
- empty wards are included only when **Mostrar alas vazias** is checked, and
  that control submits the same GET form, so the effective filters survive the
  reload;
- the AJAX tree refresh and the refresh button re-request the current URL, so
  the same filters apply to the partial response.

Map tag metadata and associations are re-read from the current catalogue on
every request on top of the shared structural cache: renaming, reclassifying,
revoking a membership or adding/removing an association is visible on the next
response without rebuilding the cache. Three empty situations are presented
differently: a filtered zero result ("Nenhum paciente encontrado"), an invalid
manual tag filter (`Filtro de tag inválido.`) and a stale or missing base cache
("Dados sendo atualizados").

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

## Restricted metadata visibility

Restricted tag names, colours, notes, identifiers and descriptions are readable
only by current members of the owning active team and by authorized catalogue
administrators. The union of all active memberships applies, not only the
selected current specialty, and it is re-evaluated on every request:

- patient list, detail, ward and map badges show only visible associations;
- add/remove/bulk JSON payloads, counters and tag selectors are projected too;
- the timeline shows authorized viewers the action-time snapshot, and outsiders
  only a generic restricted action with the team abbreviation, actor and time;
- reclassifying a public tag as restricted or revoking a membership applies to
  the very next response, including responses built from the shared ward cache.

See [tag-privacy-surfaces.md](tag-privacy-surfaces.md) for the complete reader
inventory, the legacy `?tag=` validation rule and the shared-cache reprojection
requirements.

## Per-user specialty tag preferences

Filter preferences are stored per retained user-specialty membership, not per
session or per current selection. The row records the selected catalogue
identities plus the `any`/`all` matching mode. Its **absence** means "not
configured yet"; an **existing empty selection** means the user intentionally
saved no tag filter and must not receive the principal tag again.

On the patient list, the effective state follows this precedence:

1. explicit manual state, including an explicitly empty selection
   (`tag_filter=manual`, repeated `tags`, `tag_mode`);
2. the saved preference of the valid active specialty, when one exists;
3. that specialty's active public principal tag with ANY matching;
4. no tag predicate, with a generic warning when a configured default exists
   but is unavailable.

Only explicit save persists a preference. Browsing, clearing and reapplying are
GET-only state changes: clearing keeps the manual marker (and survives refresh,
pagination and refresh links), while reapply drops the tag parameters so the
saved or principal default is recomputed. **Salvar como preferência da
especialidade ativa** is a CSRF-protected POST limited to the caller's current
valid specialty; forged or stale specialty targets are denied and no
preference is written into another team. Only currently visible active tags can
be saved; historical/inaccessible identities remain usable for manual
filtering but cannot become automatic defaults.

Automatic defaults are revalidated on every request. Inactive, archived or
inaccessible saved identities are omitted with the generic warning and the
remaining tags still apply; if none remain the tag predicate is dropped rather
than returning no patients. Stored identities are never silently rewritten, so
reactivating a tag restores it, and revoking membership retains the settings
without granting access. Rejoining the team reuses the retained preference and
never restores leadership automatically. The owner can review retained settings
at **Meu Perfil → Preferências de Tags**.

## Current limitation

Lifecycle, responsibility, assignment policy, atomic audited writes, stable
event references, requester-aware read privacy, the leader team tag page,
searchable multi-tag filtering on the patient list **and the ward map**, and
retained per-specialty preferences are delivered together as one release
candidate. Partial rollout is not supported: the change must be reviewed and
deployed as a whole, and applying its migrations or deploying any slice to
production requires separate human approval.
Team roster and membership administration stay in **Django Admin →
Especialidades dos Usuários**; the leader page never manages memberships. Do
not create production restricted catalogue data before that release review.
