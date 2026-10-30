-- Post-restore verification for the EQMD dedicated PostgreSQL 15 (slice s3).
-- Read-only: emits aggregate counts and ownership/extension facts only.
-- Run as: psql -U postgres -d eqmd_db -At -F $'\t' -f verify-restore.sql

\set ON_ERROR_STOP on

SELECT 'extensions',
       coalesce(string_agg(extname, ',' ORDER BY extname), '')
FROM pg_extension
WHERE extname IN ('unaccent', 'pg_trgm');

SELECT 'tables', count(*)
FROM pg_tables
WHERE schemaname = 'public';

SELECT 'sequences', count(*)
FROM information_schema.sequences
WHERE sequence_schema = 'public';

SELECT 'indexes', count(*)
FROM pg_indexes
WHERE schemaname = 'public';

SELECT 'constraints', count(*)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public';

SELECT 'fk_total', count(*)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public' AND c.contype = 'f';

SELECT 'fk_unvalidated', count(*)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public' AND c.contype = 'f' AND NOT c.convalidated;

SELECT 'sequence_state',
       coalesce(
         string_agg(
           sequencename || '=' || last_value,
           ',' ORDER BY sequencename
         ),
         ''
       )
FROM pg_sequences
WHERE schemaname = 'public';

SELECT 'table_owners',
       coalesce(string_agg(DISTINCT tableowner, ',' ORDER BY tableowner), '')
FROM pg_tables
WHERE schemaname = 'public';

SELECT 'tables_not_owned_by_migrator', count(*)
FROM pg_tables
WHERE schemaname = 'public' AND tableowner <> 'eqmd_migrator';

SELECT 'sequence_owners',
       coalesce(
         string_agg(
           DISTINCT pg_get_userbyid(c.relowner),
           ',' ORDER BY pg_get_userbyid(c.relowner)
         ),
         ''
       )
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'S' AND n.nspname = 'public';

SELECT 'sequences_not_owned_by_migrator', count(*)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'S'
  AND n.nspname = 'public'
  AND pg_get_userbyid(c.relowner) <> 'eqmd_migrator';

SELECT 'eqmd_user_superuser',
       CASE WHEN rolsuper THEN 'true' ELSE 'false' END
FROM pg_roles
WHERE rolname = 'eqmd_user';

SELECT 'eqmd_user_createdb',
       CASE WHEN rolcreatedb THEN 'true' ELSE 'false' END
FROM pg_roles
WHERE rolname = 'eqmd_user';

SELECT 'eqmd_user_createrole',
       CASE WHEN rolcreaterole THEN 'true' ELSE 'false' END
FROM pg_roles
WHERE rolname = 'eqmd_user';

SELECT 'eqmd_migrator_superuser',
       CASE WHEN rolsuper THEN 'true' ELSE 'false' END
FROM pg_roles
WHERE rolname = 'eqmd_migrator';

SELECT 'database_encoding', pg_encoding_to_char(encoding)
FROM pg_database
WHERE datname = current_database();

SELECT 'database_collate', datcollate
FROM pg_database
WHERE datname = current_database();

SELECT 'database_ctype', datctype
FROM pg_database
WHERE datname = current_database();
