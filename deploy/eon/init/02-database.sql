-- EQMD dedicated PostgreSQL 15 — database, extensions and grants (slice s3).
-- Runs after 01-roles.sql on an empty data directory. The bootstrap
-- superuser/database are postgres/postgres; the application uses
-- eqmd_db/eqmd_user (see docker-compose.eon.yml).
-- Manual fallback (fresh volume only):
--   psql -U postgres -d postgres -f 02-database.sql

\set ON_ERROR_STOP on
\connect postgres

CREATE DATABASE eqmd_db
  WITH TEMPLATE = template0
       ENCODING = 'UTF8'
       LC_COLLATE = 'C'
       LC_CTYPE = 'C';

\connect eqmd_db

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

GRANT CONNECT ON DATABASE eqmd_db TO eqmd_user, eqmd_migrator;
GRANT USAGE ON SCHEMA public TO eqmd_user, eqmd_migrator;
GRANT CREATE ON SCHEMA public TO eqmd_migrator;

GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public TO eqmd_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eqmd_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eqmd_migrator;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eqmd_migrator;

-- Future objects created by the migrator remain usable by the runtime role.
ALTER DEFAULT PRIVILEGES FOR ROLE eqmd_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO eqmd_user;
ALTER DEFAULT PRIVILEGES FOR ROLE eqmd_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO eqmd_user;
ALTER DEFAULT PRIVILEGES FOR ROLE eqmd_migrator IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO eqmd_user;
