-- EQMD dedicated PostgreSQL 15 — roles (slice s3).
-- Runs once on an empty data directory via /docker-entrypoint-initdb.d.
-- The container entrypoint supplies EQMD_USER_PASSWORD and
-- EQMD_MIGRATOR_PASSWORD from the environment; the fallback is to export
-- both and run: psql -U postgres -d postgres -f 01-roles.sql.
-- Passwords are never hardcoded here.

\set ON_ERROR_STOP on
\getenv EQMD_USER_PASSWORD EQMD_USER_PASSWORD
\getenv EQMD_MIGRATOR_PASSWORD EQMD_MIGRATOR_PASSWORD

CREATE ROLE eqmd_user
  LOGIN
  PASSWORD :'EQMD_USER_PASSWORD'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE;

CREATE ROLE eqmd_migrator
  LOGIN
  PASSWORD :'EQMD_MIGRATOR_PASSWORD'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE;
