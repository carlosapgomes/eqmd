## Context

Drug template list views and filters use `unaccent(lower(name))` for accent-insensitive substring matches. The autocomplete endpoint in `apps/outpatientprescriptions/views.py` currently uses plain `icontains`, which is accent-sensitive and inconsistent with the list views. With `icontains`, PostgreSQL cannot use a b-tree index, so queries become sequential scans as data grows.

## Goals / Non-Goals

- Goals: Improve performance of accent-insensitive substring search for `DrugTemplate.name` without changing query behavior; align autocomplete search with accent-insensitive matching.
- Non-Goals: Change search semantics, introduce new searchable fields, or add a stored normalized column.

## Decisions

- Decision: Use `pg_trgm` + a GIN trigram index on `unaccent(lower(name))`.
  - Rationale: Trigram GIN indexes support `icontains` efficiently on expressions and avoid maintaining a separate normalized column.
- Decision: Apply the same `unaccent(lower(...))` normalization to the autocomplete query.
  - Rationale: Keeps search behavior consistent across UI entry points.

## Alternatives Considered

- Stored normalized column with b-tree index: Doesn’t improve `icontains` and requires sync logic.
- Full-text search: Overkill for simple substring matching and different ranking semantics.

## Risks / Trade-offs

- Index size increases with trigrams; acceptable for a few thousand rows.
- Requires enabling `pg_trgm` extension in production.

## Migration Plan

1. Add migration to enable `pg_trgm`.
2. Add migration to create the trigram index on the normalized expression.
3. Deploy and apply migrations.

## Open Questions

- None.
