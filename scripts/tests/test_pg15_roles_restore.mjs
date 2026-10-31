import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const initDir = path.join(repoRoot, 'deploy', 'eon', 'init');
const rolesPath = path.join(initDir, '01-roles.sql');
const databasePath = path.join(initDir, '02-database.sql');
const verifyPath = path.join(
  repoRoot,
  'deploy',
  'eon',
  'restore',
  'verify-restore.sql',
);
const composePath = path.join(repoRoot, 'docker-compose.eon.yml');

function read(file) {
  return readFileSync(file, 'utf8');
}

function compact(sql) {
  return sql.replace(/\s+/g, ' ').trim();
}

test('01-roles.sql defines eqmd_user without elevated attributes', () => {
  const sql = compact(read(rolesPath));
  assert.match(
    sql,
    /CREATE ROLE eqmd_user [^;]*LOGIN[^;]*NOSUPERUSER[^;]*NOCREATEDB[^;]*NOCREATEROLE/i,
  );
  assert.match(sql, /PASSWORD\s+:'EQMD_USER_PASSWORD'/);
});

test('01-roles.sql defines eqmd_migrator as a separate login', () => {
  const sql = compact(read(rolesPath));
  assert.match(
    sql,
    /CREATE ROLE eqmd_migrator [^;]*LOGIN[^;]*NOSUPERUSER[^;]*NOCREATEDB[^;]*NOCREATEROLE/i,
  );
  assert.match(sql, /PASSWORD\s+:'EQMD_MIGRATOR_PASSWORD'/);
  assert.doesNotMatch(sql, /GRANT\s+SUPERUSER/i);
});

test('no hardcoded role passwords in the init SQL', () => {
  const sql = `${compact(read(rolesPath))} ${compact(read(databasePath))}`;
  assert.doesNotMatch(sql, /PASSWORD\s+'[^']+'/i);
});

test('02-database.sql creates eqmd_db with explicit UTF8/C template0', () => {
  const sql = compact(read(databasePath));
  assert.match(sql, /CREATE DATABASE eqmd_db/i);
  assert.match(sql, /TEMPLATE\s*=?\s*template0/i);
  assert.match(sql, /ENCODING\s*=?\s*'UTF8'/i);
  assert.match(sql, /LC_COLLATE\s*=?\s*'C'/i);
  assert.match(sql, /LC_CTYPE\s*=?\s*'C'/i);
});

test('02-database.sql installs unaccent and pg_trgm owned by migrator', () => {
  const sql = compact(read(databasePath));
  assert.match(sql, /CREATE EXTENSION IF NOT EXISTS unaccent/i);
  assert.match(sql, /CREATE EXTENSION IF NOT EXISTS pg_trgm/i);
  assert.match(
    sql,
    /SET ROLE eqmd_migrator;[\s\S]*CREATE EXTENSION IF NOT EXISTS unaccent;[\s\S]*RESET ROLE;/,
    'extensions must be created under SET ROLE so the migrator owns them',
  );
});

test('02-database.sql grants runtime access and future privileges', () => {
  const sql = compact(read(databasePath));
  assert.match(sql, /GRANT CONNECT ON DATABASE eqmd_db TO eqmd_user/i);
  assert.match(sql, /GRANT USAGE ON SCHEMA public TO eqmd_user/i);
  assert.match(
    sql,
    /GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO eqmd_user/i,
  );
  assert.match(
    sql,
    /ALTER DEFAULT PRIVILEGES FOR ROLE eqmd_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO eqmd_user/i,
  );
  assert.match(
    sql,
    /ALTER DEFAULT PRIVILEGES FOR ROLE eqmd_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO eqmd_user/i,
  );
});

test('compose mounts the init directory read-only for postgres', () => {
  const compose = compact(read(composePath));
  assert.match(
    compose,
    /\.\/deploy\/eon\/init:\/docker-entrypoint-initdb\.d:ro/,
  );
});

test('verify-restore.sql checks extensions, counts and ownership', () => {
  const sql = compact(read(verifyPath));
  assert.match(sql, /pg_extension/i);
  assert.match(sql, /pg_tables/i);
  assert.match(sql, /pg_sequences/i);
  assert.match(sql, /pg_constraint/i);
  assert.match(sql, /eqmd_migrator/i);
  assert.match(sql, /eqmd_user/i);
  assert.doesNotMatch(sql, /SELECT\s+\*\s+FROM\s+synthetic/i);
});
