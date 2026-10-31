#!/usr/bin/env node
/**
 * Disposable PostgreSQL 15 rehearsal for slice s3.
 *
 * Proves: init SQL produces eqmd_db (UTF8/C) with roles/extensions,
 * pg_dump -Fc from a synthetic source restores with pg_restore
 * (--exit-on-error --no-owner --role=eqmd_migrator), object counts and
 * sequence values match, FKs are valid, eqmd_user is not privileged and
 * restored objects belong to eqmd_migrator.
 *
 * Every resource is named eqmd_s3_rehearsal_* and removed in a finally
 * block. Existing containers/networks/volumes are never touched.
 * Passwords are SYNTHETIC and exist only in this script.
 */
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const initDir = path.join(repoRoot, 'deploy', 'eon', 'init');
const verifySqlPath = path.join(
  repoRoot,
  'deploy',
  'eon',
  'restore',
  'verify-restore.sql',
);
const evidenceDir = path.join(repoRoot, 'temp', 'migracao-eon', 's3');

const IMAGE =
  'postgres@sha256:' +
  '1d1095b0503145be79c79239372aefadfacf6b7c33c9245bbf99ce4b6b89c737';
const PREFIX = 'eqmd_s3_rehearsal_';
const suffix =
  process.env.EQMD_S3_RUN_SUFFIX || `${process.pid}-${Date.now()}`;
const networkName = `${PREFIX}net_${suffix}`;
const sourceName = `${PREFIX}a_${suffix}`;
const targetName = `${PREFIX}b_${suffix}`;
const sourceVolume = `${PREFIX}vol_a_${suffix}`;
const targetVolume = `${PREFIX}vol_b_${suffix}`;
const ADMIN_PASSWORD = 'SYNTHETIC_s3_admin_password';
const USER_PASSWORD = 'SYNTHETIC_s3_user_password';
const MIGRATOR_PASSWORD = 'SYNTHETIC_s3_migrator_password';

const SOURCE_SQL = `
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE synthetic_site (
  id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  label text NOT NULL
);

CREATE TABLE synthetic_patient (
  id bigserial PRIMARY KEY,
  site_id bigint NOT NULL REFERENCES synthetic_site(id),
  code text NOT NULL UNIQUE
);

CREATE TABLE synthetic_note (
  id bigserial PRIMARY KEY,
  patient_id bigint NOT NULL REFERENCES synthetic_patient(id),
  body text NOT NULL
);

CREATE INDEX synthetic_patient_site_idx ON synthetic_patient(site_id);
CREATE INDEX synthetic_note_patient_idx ON synthetic_note(patient_id);

INSERT INTO synthetic_site (code, label)
SELECT 'S' || lpad(i::text, 2, '0'), 'Synthetic site ' || i
FROM generate_series(1, 3) AS i;

INSERT INTO synthetic_patient (site_id, code)
SELECT ((i - 1) % 3) + 1, 'P' || lpad(i::text, 3, '0')
FROM generate_series(1, 10) AS i;

INSERT INTO synthetic_note (patient_id, body)
SELECT ((i - 1) % 10) + 1, 'Synthetic note ' || lpad(i::text, 2, '0')
FROM generate_series(1, 20) AS i;
`;

const COUNTS_SQL = `
SELECT 'tables', count(*)::text
FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT 'sequences', count(*)::text
FROM information_schema.sequences WHERE sequence_schema = 'public'
UNION ALL
SELECT 'indexes', count(*)::text
FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 'constraints', count(*)::text
FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public'
UNION ALL
SELECT 'fk_total', count(*)::text
FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public' AND c.contype = 'f'
UNION ALL
SELECT 'rows_site', count(*)::text FROM synthetic_site
UNION ALL
SELECT 'rows_patient', count(*)::text FROM synthetic_patient
UNION ALL
SELECT 'rows_note', count(*)::text FROM synthetic_note;
`;

const SEQUENCE_SQL = `
SELECT sequencename, last_value
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY sequencename;
`;

const expected = {
  containers: [sourceName, targetName],
  volumes: [sourceVolume, targetVolume],
  networks: [networkName],
};
const created = { containers: [], volumes: [], networks: [] };

function docker(args, options = {}) {
  const result = spawnSync('docker', args, {
    encoding: options.encoding === null ? null : 'utf8',
    input: options.input,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error) {
    throw new Error(`docker ${args[0]} failed to spawn: ${result.error.message}`);
  }
  const stderr = result.stderr ? result.stderr.toString() : '';
  if (result.status !== 0 && !options.allowFailure) {
    const stdout = result.stdout ? result.stdout.toString() : '';
    throw new Error(
      `docker ${args.join(' ')} exited ${result.status}\n${stderr}${stdout}`,
    );
  }
  return result;
}

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function resourceExists(kind, name) {
  const args =
    kind === 'containers'
      ? ['inspect', '--type', 'container', name]
      : kind === 'volumes'
        ? ['volume', 'inspect', name]
        : ['network', 'inspect', name];
  return docker(args, { allowFailure: true }).status === 0;
}

function assertNamesFree() {
  const conflicts = [];
  for (const [kind, names] of Object.entries(expected)) {
    for (const name of names) {
      if (resourceExists(kind, name)) conflicts.push(`${kind}: ${name}`);
    }
  }
  if (conflicts.length > 0) {
    throw new Error(
      'refusing to run: expected disposable names already exist ' +
        `(${conflicts.join(', ')}). Remove them manually only if stale; ` +
        'this script never deletes resources it did not create.',
    );
  }
}

function remainingResources() {
  const residue = { containers: [], volumes: [], networks: [] };
  for (const [kind, names] of Object.entries(expected)) {
    for (const name of names) {
      if (resourceExists(kind, name)) residue[kind].push(name);
    }
  }
  return residue;
}

function cleanup() {
  for (const name of created.containers) {
    docker(['rm', '-f', name], { allowFailure: true });
  }
  for (const name of created.volumes) {
    docker(['volume', 'rm', '-f', name], { allowFailure: true });
  }
  for (const name of created.networks) {
    docker(['network', 'rm', name], { allowFailure: true });
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    cleanup();
    process.exit(130);
  });
}

function waitReady(container) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const state = docker(
      ['inspect', '-f', '{{.State.Running}}', container],
      { allowFailure: true },
    );
    if (state.status !== 0 || state.stdout.trim() !== 'true') {
      const logs = docker(['logs', '--tail', '80', container], {
        allowFailure: true,
      });
      throw new Error(
        `${container} exited before readiness:\n${logs.stdout}${logs.stderr}`,
      );
    }
    const ready = docker(
      ['exec', container, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'],
      { allowFailure: true },
    );
    if (ready.status === 0) return;
    sleepSync(1000);
  }
  throw new Error(`${container} did not become ready in 120s`);
}

function psql(container, database, sql, options = {}) {
  const args = ['exec'];
  if (options.password) {
    args.push('-e', `PGPASSWORD=${options.password}`);
  }
  args.push('-i', container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U',
    options.user ?? 'postgres', '-d', database);
  if (options.host) {
    args.push('-h', options.host);
  }
  args.push('-At', '-F', '\t', '-f', '-');
  return docker(args, { input: sql }).stdout;
}

function parseKv(text) {
  const values = {};
  for (const line of text.trim().split('\n')) {
    const separator = line.indexOf('\t');
    if (separator === -1) continue;
    values[line.slice(0, separator)] = line.slice(separator + 1);
  }
  return values;
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function rehearse(evidence) {
  assertNamesFree();
  console.log('[s3] exact-name check passed; creating disposables');

  docker(['network', 'create', networkName]);
  created.networks.push(networkName);

  docker(['volume', 'create', sourceVolume]);
  created.volumes.push(sourceVolume);
  docker(['volume', 'create', targetVolume]);
  created.volumes.push(targetVolume);

  docker([
    'run', '-d', '--name', sourceName, '--network', networkName,
    '-e', `POSTGRES_PASSWORD=${ADMIN_PASSWORD}`,
    '-e', 'POSTGRES_USER=postgres',
    '-e', 'POSTGRES_DB=postgres',
    '-v', `${sourceVolume}:/var/lib/postgresql/data`,
    IMAGE,
  ]);
  created.containers.push(sourceName);

  docker([
    'run', '-d', '--name', targetName, '--network', networkName,
    '-e', `POSTGRES_PASSWORD=${ADMIN_PASSWORD}`,
    '-e', 'POSTGRES_USER=postgres',
    '-e', 'POSTGRES_DB=postgres',
    '-e', `EQMD_USER_PASSWORD=${USER_PASSWORD}`,
    '-e', `EQMD_MIGRATOR_PASSWORD=${MIGRATOR_PASSWORD}`,
    '-v', `${targetVolume}:/var/lib/postgresql/data`,
    '-v', `${initDir}:/docker-entrypoint-initdb.d:ro`,
    IMAGE,
  ]);
  created.containers.push(targetName);

  console.log('[s3] waiting for source and target');
  waitReady(sourceName);
  waitReady(targetName);

  console.log('[s3] creating synthetic source schema');
  psql(sourceName, 'postgres', SOURCE_SQL);

  const countsA = parseKv(psql(sourceName, 'postgres', COUNTS_SQL));
  const sequencesA = psql(sourceName, 'postgres', SEQUENCE_SQL).trim();

  console.log('[s3] dumping source with pg_dump -Fc --no-owner --no-acl --no-comments');
  const dump = docker([
    'exec', sourceName, 'pg_dump', '-Fc', '--no-owner', '--no-acl',
    '--no-comments', '-U', 'postgres', '-d', 'postgres',
  ], { encoding: null }).stdout;
  check(Buffer.isBuffer(dump) && dump.length > 0, 'pg_dump produced no data');
  console.log(`[s3] dump bytes=${dump.length}`);

  console.log('[s3] restoring into eqmd_db with pg_restore --exit-on-error --no-owner --role=eqmd_migrator');
  docker([
    'exec', '-i', targetName, 'pg_restore', '--exit-on-error', '--no-owner',
    '--role=eqmd_migrator', '-U', 'postgres', '-d', 'eqmd_db',
  ], { input: dump });

  const countsB = parseKv(psql(targetName, 'eqmd_db', COUNTS_SQL));
  const sequencesB = psql(targetName, 'eqmd_db', SEQUENCE_SQL).trim();
  const verifyText = psql(
    targetName,
    'eqmd_db',
    readFileSync(verifySqlPath, 'utf8'),
  );
  const verify = parseKv(verifyText);

  const runtimeRows = psql(targetName, 'eqmd_db',
    'SELECT count(*) FROM synthetic_patient;',
    { user: 'eqmd_user', password: USER_PASSWORD, host: '127.0.0.1' }).trim();
  const migratorLogin = psql(targetName, 'eqmd_db', 'SELECT 1;',
    { user: 'eqmd_migrator', password: MIGRATOR_PASSWORD }).trim();

  console.log(`[s3] A counts: ${JSON.stringify(countsA)}`);
  console.log(`[s3] B counts: ${JSON.stringify(countsB)}`);
  console.log(`[s3] A sequences: ${sequencesA.replace(/\n/g, '; ')}`);
  console.log(`[s3] B sequences: ${sequencesB.replace(/\n/g, '; ')}`);
  console.log(`[s3] verify: ${JSON.stringify(verify)}`);

  for (const key of [
    'tables', 'sequences', 'indexes', 'constraints', 'fk_total',
    'rows_site', 'rows_patient', 'rows_note',
  ]) {
    check(
      countsA[key] === countsB[key],
      `${key} differs: source=${countsA[key]} target=${countsB[key]}`,
    );
  }
  check(countsB.rows_note === '20', `expected 20 synthetic notes, got ${countsB.rows_note}`);
  check(sequencesA === sequencesB, 'sequence state differs after restore');
  check(Number(verify.fk_total) >= 1, 'no foreign key restored');
  check(verify.fk_unvalidated === '0', 'restored foreign key is not validated');
  check(
    verify.extensions === 'pg_trgm,unaccent',
    `extensions mismatch: ${verify.extensions}`,
  );
  check(verify.eqmd_user_superuser === 'false', 'eqmd_user is superuser');
  check(verify.eqmd_user_createdb === 'false', 'eqmd_user has CREATEDB');
  check(verify.eqmd_user_createrole === 'false', 'eqmd_user has CREATEROLE');
  check(verify.eqmd_migrator_superuser === 'false', 'eqmd_migrator is superuser');
  check(verify.table_owners === 'eqmd_migrator', `table owners: ${verify.table_owners}`);
  check(
    verify.sequence_owners === 'eqmd_migrator',
    `sequence owners: ${verify.sequence_owners}`,
  );
  check(verify.tables_not_owned_by_migrator === '0', 'some table is not migrator-owned');
  check(
    verify.sequences_not_owned_by_migrator === '0',
    'some sequence is not migrator-owned',
  );
  check(verify.database_encoding === 'UTF8', `encoding: ${verify.database_encoding}`);
  check(verify.database_collate === 'C', `collate: ${verify.database_collate}`);
  check(verify.database_ctype === 'C', `ctype: ${verify.database_ctype}`);
  check(runtimeRows === countsB.rows_patient, 'eqmd_user cannot read rows');
  check(migratorLogin === '1', 'eqmd_migrator cannot log in');

  evidence.counts_source = countsA;
  evidence.counts_target = countsB;
  evidence.sequences_source = sequencesA.split('\n');
  evidence.sequences_target = sequencesB.split('\n');
  evidence.verify = verify;
  evidence.runtime_rows_as_eqmd_user = runtimeRows;
  evidence.migrator_login = migratorLogin;
  console.log('[s3] all rehearsal assertions passed');
}

function main() {
  mkdirSync(evidenceDir, { recursive: true });
  const evidence = { image: IMAGE, prefix: PREFIX };
  let failure = null;
  try {
    rehearse(evidence);
  } catch (error) {
    failure = error;
    console.error(`[s3] FAIL: ${error.message}`);
  } finally {
    cleanup();
  }

  const residue = remainingResources();
  evidence.cleanup_residue = residue;
  console.log(`[s3] cleanup residue: ${JSON.stringify(residue)}`);
  try {
    writeFileSync(
      path.join(evidenceDir, 'rehearsal-metrics.json'),
      `${JSON.stringify(evidence, null, 2)}\n`,
    );
  } catch (error) {
    console.error(`[s3] could not write metrics: ${error.message}`);
  }

  const hasResidue =
    residue.containers.length + residue.volumes.length + residue.networks.length >
    0;
  if (hasResidue) {
    failure = failure ?? new Error('expected eqmd_s3_rehearsal_* names remain');
  }
  if (failure) {
    process.exitCode = 1;
    return;
  }
  console.log('[s3] PASS');
}

main();
