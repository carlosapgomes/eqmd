## 1. Implementation

- [ ] 1.1 Add a migration to enable the `pg_trgm` extension (PostgreSQL only)
- [ ] 1.2 Add a GIN trigram index for `unaccent(lower(name))` on `DrugTemplate`
- [ ] 1.3 Normalize autocomplete search to use accent-insensitive comparisons
- [ ] 1.4 Update or add tests that verify the index exists on PostgreSQL and autocomplete uses normalization
- [ ] 1.5 Run `docker exec eqmd_dev python manage.py test`
