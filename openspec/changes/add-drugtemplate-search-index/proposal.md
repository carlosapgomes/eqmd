## Why

Drug template name search currently relies on runtime `unaccent(lower(name))` expressions with `icontains`. Without an index, PostgreSQL must compute the normalization per row and scan the table for substring matches. Adding a trigram index keeps accent-insensitive substring search responsive as the dataset grows to a few thousand records while preserving current behavior.

## What Changes

- Enable the `pg_trgm` extension in PostgreSQL.
- Add a GIN trigram index on the normalized drug template name (`unaccent(lower(name))`).
- Normalize the autocomplete search in `apps/outpatientprescriptions/views.py` to use the same accent-insensitive comparison as the main drug template lists.
- Keep existing search and sort behavior unchanged (performance-only change).

## Impact

- Affected specs: drugtemplates (search behavior/performance)
- Affected code:
  - `apps/drugtemplates/models.py` (index declaration)
  - `apps/drugtemplates/migrations/` (pg_trgm extension + index migration)
  - `apps/outpatientprescriptions/views.py` (autocomplete search normalization)
