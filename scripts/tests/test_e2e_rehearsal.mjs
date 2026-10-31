#!/usr/bin/env node
/**
 * Slice s7 end-to-end rehearsal on the Zen host.
 *
 * Phase A: disposable eqmd_s7_rehearsal compose stack with local networks
 * using the reserved eon names/CIDRs, init SQL, migrator, synthetic data
 * and media, full stack gates, dump + media tar + sha256 manifest export.
 *
 * Phase B: down -v, fresh stack, E4 prepare -> restore -> remap,
 * migrate --plan no-op proof, full stack gates, A==B counts/hashes,
 * roles/ownership/extensions, then guaranteed exact-name cleanup.
 *
 * Pulls the pinned digests read-only. No eon/origin access, no real .env,
 * no clinical data. Node host only; Python runs inside containers.
 */
import { spawnSync } from 'node:child_process';
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const evidenceDir = path.join(repoRoot, 'temp', 'migracao-eon', 's7');
const stagingDir = path.join(evidenceDir, 'staging');
const composeFile = path.join(repoRoot, 'docker-compose.eon.yml');
const overrideFile = path.join(evidenceDir, 'rehearsal.override.yml');
const envFile = path.join(repoRoot, 'env.eon.example');
const verifySql = path.join(
  repoRoot,
  'deploy',
  'eon',
  'restore',
  'verify-restore.sql',
);

const PROJECT = 'eqmd_s7_rehearsal';
const TIMINGS_NOTE =
  'Refreshed on every successful rehearsal run; this file always reflects ' +
  'the LATEST green run. Historical ranges are in ' +
  'deploy/eon/cutover/rehearsal-baseline.md.';
const EQMD_IMAGE =
  'ghcr.io/carlosapgomes/eqmd@sha256:' +
  'fe31d296f50dd34c19c437244ea9a3d61f75aba4ec7d806329b50f8340cc4c4f';
const POSTGRES_IMAGE =
  'postgres@sha256:' +
  '1d1095b0503145be79c79239372aefadfacf6b7c33c9245bbf99ce4b6b89c737';
const NGINX_IMAGE =
  'nginx@sha256:' +
  '51047bea59fed88fbd1f52565d2f5fabcb82d311cf6c9e507a10ce74bb3bc3f0';
const PYTHON_IMAGE =
  'python:3.12-slim-trixie@sha256:' +
  'aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159';

const NETWORKS = [
  ['<REDE_INGRESS>', '10.99.17.0/29'],
  ['<REDE_APP>', '10.99.18.0/24'],
  ['<REDE_DB>', '10.99.19.0/24'],
  ['<REDE_EGRESS>', '10.99.20.0/24'],
];
const VOLUMES = {
  media: `${PROJECT}_media`,
  logs: `${PROJECT}_logs`,
  pgdata: `${PROJECT}_pgdata`,
  static: `${PROJECT}_static`,
};
const CONTAINERS = [
  `${PROJECT}-postgres-1`,
  `${PROJECT}-eqmd-1`,
  `${PROJECT}-frontend-1`,
  `${PROJECT}-init-1`,
];

const created = { containers: [], volumes: [], networks: [] };
const timings = [];
let probeCounter = 0;
let ownsResources = false;

const SEED_SQL = `
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
SELECT 'tables', count(*)::text FROM pg_tables WHERE schemaname = 'public'
UNION ALL SELECT 'sequences', count(*)::text FROM information_schema.sequences
  WHERE sequence_schema = 'public'
UNION ALL SELECT 'indexes', count(*)::text FROM pg_indexes
  WHERE schemaname = 'public'
UNION ALL SELECT 'constraints', count(*)::text FROM pg_constraint c
  JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'public'
UNION ALL SELECT 'fk_total', count(*)::text FROM pg_constraint c
  JOIN pg_namespace n ON n.oid = c.connamespace
  WHERE n.nspname = 'public' AND c.contype = 'f'
UNION ALL SELECT 'rows_site', count(*)::text FROM synthetic_site
UNION ALL SELECT 'rows_patient', count(*)::text FROM synthetic_patient
UNION ALL SELECT 'rows_note', count(*)::text FROM synthetic_note;
`;

const SEQUENCE_SQL = `
SELECT sequencename, last_value FROM pg_sequences
WHERE schemaname = 'public' ORDER BY sequencename;
`;

const PROBE_CODE = `
import json
import sys
import urllib.error
import urllib.request

url = sys.argv[1]
method = sys.argv[2] if len(sys.argv) > 2 else 'GET'
host = sys.argv[3] if len(sys.argv) > 3 else ''
headers = {'Host': host} if host else {}
request = urllib.request.Request(url, method=method, headers=headers)
try:
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read()
        print(json.dumps({'status': response.status,
                          'headers': dict(response.headers.items()),
                          'body': body.decode('utf-8', 'replace')}))
except urllib.error.HTTPError as error:
    body = error.read()
    print(json.dumps({'status': error.code,
                      'headers': dict(error.headers.items()),
                      'body': body.decode('utf-8', 'replace')}))
`;

function log(message) {
  console.log(`[s7] ${message}`);
}

function docker(args, options = {}) {
  const result = spawnSync('docker', args, {
    encoding: options.encoding === null ? null : 'utf8',
    input: options.input,
    maxBuffer: 64 * 1024 * 1024,
    timeout: options.timeout ?? 600000,
  });
  if (result.error) {
    throw new Error(`docker ${args[0]} failed: ${result.error.message}`);
  }
  const stderr = result.stderr ? result.stderr.toString() : '';
  if (result.status !== 0 && !options.allowFailure) {
    const stdout = result.stdout ? result.stdout.toString() : '';
    throw new Error(
      `docker ${args.slice(0, 12).join(' ')} exited ${result.status}\n` +
        `${stderr}${stdout}`,
    );
  }
  return result;
}

function compose(args, options = {}) {
  return docker([
    'compose', '-p', PROJECT,
    '-f', composeFile, '-f', overrideFile,
    '--env-file', envFile,
    ...args,
  ], options);
}

function exists(kind, name) {
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
  for (const name of CONTAINERS) {
    if (exists('containers', name)) conflicts.push(`container: ${name}`);
  }
  for (const name of Object.values(VOLUMES)) {
    if (exists('volumes', name)) conflicts.push(`volume: ${name}`);
  }
  for (const [name] of NETWORKS) {
    if (exists('networks', name)) conflicts.push(`network: ${name}`);
  }
  if (conflicts.length > 0) {
    throw new Error(
      'refusing to run: expected rehearsal names already exist ' +
        `(${conflicts.join(', ')}). Clean them manually only if stale; ` +
        'this script never deletes resources it did not create.',
    );
  }
}

function cleanup() {
  if (ownsResources) {
    try {
      compose(['down', '-v', '--remove-orphans'], {
        allowFailure: true,
        timeout: 180000,
      });
    } catch (error) {
      log(`cleanup compose warning: ${error.message}`);
    }
    for (const name of created.containers) {
      docker(['rm', '-f', name], { allowFailure: true });
    }
    for (const name of CONTAINERS) {
      docker(['rm', '-f', name], { allowFailure: true });
    }
    for (const name of Object.values(VOLUMES)) {
      docker(['volume', 'rm', '-f', name], { allowFailure: true });
    }
    for (const [name] of NETWORKS) {
      docker(['network', 'rm', name], { allowFailure: true });
    }
  }
  try {
    rmSync(stagingDir, { recursive: true, force: true });
  } catch (error) {
    log(`staging cleanup warning: ${error.message}`);
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    cleanup();
    process.exit(130);
  });
}

function stage(name, fn) {
  const started = Date.now();
  log(`start ${name}`);
  const value = fn();
  const ms = Date.now() - started;
  timings.push({ stage: name, ms });
  log(`done ${name}: ${ms} ms`);
  return value;
}

function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function ensureImage(reference) {
  if (docker(['image', 'inspect', reference], { allowFailure: true }).status === 0) {
    return;
  }
  log(`pulling ${reference}`);
  docker([
    'pull', '--platform', 'linux/amd64', reference,
  ], { timeout: 1800000 });
}

function waitPostgres() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const ready = compose([
      'exec', '-T', 'postgres', 'psql', '-U', 'postgres', '-d', 'eqmd_db',
      '-Atc', "SELECT count(*) FROM pg_roles WHERE rolname='eqmd_user';",
    ], { allowFailure: true });
    if (ready.status === 0 && ready.stdout.trim() === '1') return;
    sleepSync(1000);
  }
  throw new Error('postgres/init did not become ready');
}

function waitEqmd() {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const ready = compose([
      'exec', '-T', 'eqmd', 'python', '-c',
      'import urllib.request; ' +
        'print(urllib.request.urlopen(' +
        '"http://127.0.0.1:8000/health/", timeout=5).status)',
    ], { allowFailure: true });
    if (ready.status === 0 && ready.stdout.trim() === '200') return;
    sleepSync(1000);
  }
  throw new Error('eqmd health did not become 200');
}

function probe(network, url, options = {}) {
  probeCounter += 1;
  const name =
    `${PROJECT}_probe_${process.pid}_${Date.now()}_${probeCounter}`;
  const args = [
    'run', '--rm', '--name', name, '--network', network,
    PYTHON_IMAGE, 'python3', '-c', PROBE_CODE, url,
    options.method ?? 'GET', options.host ?? '',
  ];
  created.containers.push(name);
  const result = docker(args, { timeout: 60000 });
  const payload = JSON.parse(result.stdout);
  const headers = {};
  for (const [key, value] of Object.entries(payload.headers)) {
    headers[key.toLowerCase()] = value;
  }
  return { status: payload.status, headers, body: payload.body };
}

function psql(sql, options = {}) {
  return compose([
    'exec', '-T', 'postgres', 'psql',
    '-U', options.user ?? 'postgres',
    '-d', options.database ?? 'eqmd_db',
    '-At', '-F', '\t', '-f', '-',
  ], { input: sql }).stdout;
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

function mediaHashes(volume) {
  const code = `
import hashlib, json, os
root = '/media'
out = {}
for dirpath, _, files in os.walk(root):
    for name in sorted(files):
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, root)
        with open(full, 'rb') as handle:
            out[rel] = hashlib.sha256(handle.read()).hexdigest()
print(json.dumps(out, sort_keys=True))
`;
  const result = docker([
    'run', '--rm', '-v', `${volume}:/media:ro`,
    PYTHON_IMAGE, 'python3', '-c', code,
  ]);
  return JSON.parse(result.stdout);
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function verifyGates(phase) {
  const health = compose([
    'exec', '-T', 'eqmd', 'python', '-c',
    'import urllib.request; ' +
      'print(urllib.request.urlopen(' +
      '"http://127.0.0.1:8000/health/", timeout=5).status)',
  ]).stdout.trim();
  check(health === '200', `${phase}: health=${health}`);

  const staticManifest = probe(
    '<REDE_INGRESS>', 'http://frontend/static/manifest.json');
  check(staticManifest.status === 200, `${phase}: static manifest status`);

  const sw = probe('<REDE_INGRESS>', 'http://frontend/static/sw.js');
  check(sw.status === 200, `${phase}: sw status=${sw.status}`);
  check(
    (sw.headers['cache-control'] ?? '').includes('no-cache'),
    `${phase}: sw cache-control=${sw.headers['cache-control']}`,
  );

  const manifest = probe(
    '<REDE_INGRESS>', 'http://frontend/manifest.json',
    { host: 'equipemed.projetoshgrs.com' },
  );
  check(manifest.status === 200, `${phase}: manifest status=${manifest.status}`);
  check(
    (manifest.headers['cache-control'] ?? '').includes('no-cache'),
    `${phase}: manifest cache-control=${manifest.headers['cache-control']}`,
  );
  check(
    manifest.body.includes('EquipeMed'),
    `${phase}: manifest body does not look like Django`,
  );
  log(
    `${phase} gates: health=200, sw no-cache, manifest no-cache`,
  );
  return {
    health,
    static_manifest_status: staticManifest.status,
    sw_cache_control: sw.headers['cache-control'],
    manifest_cache_control: manifest.headers['cache-control'],
  };
}

function verifyDatabase() {
  const raw = psql(readFileSync(verifySql, 'utf8'));
  writeFileSync(path.join(evidenceDir, 'verify-restore.txt'), raw);
  const verify = parseKv(raw);
  check(verify.extensions === 'pg_trgm,unaccent', 'extensions mismatch');
  check(verify.fk_unvalidated === '0', 'unvalidated FK');
  check(verify.eqmd_user_superuser === 'false', 'eqmd_user superuser');
  check(verify.table_owners === 'eqmd_migrator', 'table ownership');
  check(verify.sequence_owners === 'eqmd_migrator', 'sequence ownership');
  check(verify.tables_not_owned_by_migrator === '0', 'table owner count');
  check(verify.sequences_not_owned_by_migrator === '0', 'sequence owner count');
  check(verify.database_encoding === 'UTF8', 'encoding');
  check(verify.database_collate === 'C', 'collate');
  check(verify.database_ctype === 'C', 'ctype');
  return verify;
}

function main() {
  mkdirSync(evidenceDir, { recursive: true });
  mkdirSync(stagingDir, { recursive: true });
  writeFileSync(overrideFile, [
    'volumes:',
    `  eqmd_media:\n    name: ${VOLUMES.media}`,
    `  eqmd_logs:\n    name: ${VOLUMES.logs}`,
    `  eqmd_pgdata:\n    name: ${VOLUMES.pgdata}`,
    `  eqmd_static:\n    name: ${VOLUMES.static}`,
    '',
  ].join('\n'));

  const summary = { project: PROJECT, timings, checks: {} };
  let failure = null;

  try {
    ensureImage(EQMD_IMAGE);
    ensureImage(POSTGRES_IMAGE);
    ensureImage(NGINX_IMAGE);
    assertNamesFree();
    ownsResources = true;

    stage('networks', () => {
      for (const [name, subnet] of NETWORKS) {
        docker(['network', 'create', '--subnet', subnet, name]);
        created.networks.push(name);
      }
    });

    stage('phase_a_postgres_up', () => {
      compose(['up', '-d', 'postgres']);
      waitPostgres();
    });
    stage('phase_a_init_prepare', () => {
      compose(['--profile', 'ops', 'run', '--rm', 'init']);
    });
    stage('phase_a_migrate', () => {
      compose(['--profile', 'ops', 'run', '--rm', 'migrate']);
    });
    stage('phase_a_seed', () => {
      psql(SEED_SQL);
    });
    stage('phase_a_media_seed', () => {
      docker([
        'run', '--rm', '--user', '9900:9900',
        '-v', `${VOLUMES.media}:/media`,
        'alpine@sha256:' +
          '28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b',
        'sh', '-c',
        'mkdir -p /media/synthetic && ' +
          'printf "synthetic alpha\\n" > /media/synthetic/alpha.txt && ' +
          'printf "synthetic beta media\\n" > /media/synthetic/beta.txt',
      ]);
    });
    stage('phase_a_full_up', () => {
      compose(['up', '-d']);
      waitEqmd();
    });
    const gatesA = stage('phase_a_gates', () => verifyGates('A'));
    const countsA = stage('phase_a_counts', () =>
      parseKv(psql(COUNTS_SQL)));
    const sequencesA = stage('phase_a_sequences', () =>
      psql(SEQUENCE_SQL).trim());
    const mediaA = stage('phase_a_media_hashes', () =>
      mediaHashes(VOLUMES.media));

    stage('export_dump', () => {
      const dump = compose([
        'exec', '-T', 'postgres', 'pg_dump', '-Fc',
        '--no-owner', '--no-acl', '--no-comments',
        '-U', 'postgres', '-d', 'eqmd_db',
      ], { encoding: null }).stdout;
      check(Buffer.isBuffer(dump) && dump.length > 0, 'empty dump');
      writeFileSync(path.join(stagingDir, 'eqmd-final.dump'), dump);
    });
    stage('export_media', () => {
      docker([
        'run', '--rm', '-v', `${VOLUMES.media}:/media:ro`,
        '-v', `${stagingDir}:/out`,
        'alpine@sha256:' +
          '28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b',
        'tar', '-C', '/media', '-czf', '/out/eqmd-media-final.tgz', '.',
      ]);
    });
    stage('manifest_transfer_check', () => {
      const files = ['eqmd-final.dump', 'eqmd-media-final.tgz'];
      const manifest = docker([
        'run', '--rm', '-v', `${stagingDir}:/data:ro`,
        'alpine@sha256:' +
          '28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b',
        'sh', '-c',
        'cd /data && sha256sum ' + files.join(' '),
      ]).stdout;
      writeFileSync(path.join(stagingDir, 'eqmd-final.sha256'), manifest);
      writeFileSync(path.join(evidenceDir, 'eqmd-final.sha256'), manifest);
      const checkResult = docker([
        'run', '--rm', '-v', `${stagingDir}:/data:ro`,
        'alpine@sha256:' +
          '28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b',
        'sh', '-c', 'cd /data && sha256sum -c eqmd-final.sha256',
      ]);
      check(checkResult.status === 0, 'manifest check failed');
    });

    stage('phase_b_down_reset', () => {
      compose(['down', '-v', '--remove-orphans']);
      for (const name of CONTAINERS) {
        docker(['rm', '-f', name], { allowFailure: true });
      }
      for (const name of Object.values(VOLUMES)) {
        docker(['volume', 'rm', '-f', name], { allowFailure: true });
      }
      sleepSync(2000);
      const leftovers = [
        ...CONTAINERS.filter((name) => exists('containers', name)),
        ...Object.values(VOLUMES).filter((name) => exists('volumes', name)),
      ];
      check(leftovers.length === 0, `down -v left ${leftovers.join(', ')}`);
    });

    stage('phase_b_postgres_up', () => {
      compose(['up', '-d', 'postgres']);
      waitPostgres();
    });
    stage('phase_b_e4_prepare', () => {
      compose(['--profile', 'ops', 'run', '--rm', 'init']);
    });
    stage('phase_b_restore_db', () => {
      const dump = readFileSync(path.join(stagingDir, 'eqmd-final.dump'));
      compose([
        'exec', '-T', 'postgres', 'pg_restore', '--exit-on-error',
        '--no-owner', '--role=eqmd_migrator',
        '-U', 'postgres', '-d', 'eqmd_db',
      ], { input: dump });
    });
    stage('phase_b_restore_media', () => {
      docker([
        'run', '--rm', '--user', '9900:9900',
        '-v', `${VOLUMES.media}:/media`,
        '-v', `${stagingDir}:/in:ro`,
        PYTHON_IMAGE,
        'tar', '--no-same-owner', '-C', '/media', '-xzf',
        '/in/eqmd-media-final.tgz',
      ]);
    });
    stage('phase_b_e4_remap', () => {
      compose(['--profile', 'ops', 'run', '--rm', 'init']);
    });
    stage('phase_b_migrate_plan', () => {
      const plan = compose([
        '--profile', 'ops', 'run', '--rm', 'migrate',
        'python', 'manage.py', 'migrate', '--plan',
      ]).stdout;
      writeFileSync(path.join(evidenceDir, 'migrate-plan.txt'), plan);
      check(
        plan.includes('No planned migration operations'),
        'migrate --plan is not empty',
      );
    });
    stage('phase_b_full_up', () => {
      compose(['up', '-d']);
      waitEqmd();
    });
    const gatesB = stage('phase_b_gates', () => verifyGates('B'));
    const countsB = stage('phase_b_counts', () =>
      parseKv(psql(COUNTS_SQL)));
    const sequencesB = stage('phase_b_sequences', () =>
      psql(SEQUENCE_SQL).trim());
    const mediaB = stage('phase_b_media_hashes', () =>
      mediaHashes(VOLUMES.media));
    const verify = stage('phase_b_verify_restore', () => verifyDatabase());

    for (const key of [
      'tables', 'sequences', 'indexes', 'constraints', 'fk_total',
      'rows_site', 'rows_patient', 'rows_note',
    ]) {
      check(
        countsA[key] === countsB[key],
        `${key} differs: A=${countsA[key]} B=${countsB[key]}`,
      );
    }
    check(sequencesA === sequencesB, 'sequence state differs');
    check(JSON.stringify(mediaA) === JSON.stringify(mediaB), 'media hashes differ');
    check(countsB.rows_note === '20', 'unexpected synthetic notes');

    const runtimeRows = psql(
      'SELECT count(*) FROM synthetic_patient;',
      { user: 'eqmd_user' },
    ).trim();
    check(runtimeRows === countsB.rows_patient, 'eqmd_user cannot read rows');

    const totalMs = timings.reduce((sum, item) => sum + item.ms, 0);
    check(totalMs < 30 * 60 * 1000, `runtime ${totalMs} ms exceeds 30 min`);

    Object.assign(summary.checks, {
      counts_a: countsA,
      counts_b: countsB,
      sequences_a: sequencesA.split('\n'),
      sequences_b: sequencesB.split('\n'),
      media_hashes_a: mediaA,
      media_hashes_b: mediaB,
      gates_a: gatesA,
      gates_b: gatesB,
      verify,
      runtime_rows_eqmd_user: runtimeRows,
      migrate_plan_noop: true,
    });
    summary.total_ms = totalMs;
    writeFileSync(
      path.join(evidenceDir, 'timings.json'),
      `${JSON.stringify({ note: TIMINGS_NOTE, project: PROJECT, stages: timings, total_ms: totalMs }, null, 2)}\n`,
    );
    writeFileSync(
      path.join(evidenceDir, 'rehearsal-summary.json'),
      `${JSON.stringify(summary, null, 2)}\n`,
    );
    log('all rehearsal assertions passed');
  } catch (error) {
    failure = error;
    console.error(`[s7] FAIL: ${error.message}`);
  } finally {
    const totalMs = timings.reduce((sum, item) => sum + item.ms, 0);
    writeFileSync(
      path.join(evidenceDir, 'timings.json'),
      `${JSON.stringify({ note: TIMINGS_NOTE, project: PROJECT, stages: timings, total_ms: totalMs }, null, 2)}\n`,
    );
    cleanup();
  }

  const residue = {
    containers: CONTAINERS.filter((name) => exists('containers', name)),
    volumes: Object.values(VOLUMES).filter((name) => exists('volumes', name)),
    networks: NETWORKS.map(([name]) => name).filter((name) =>
      exists('networks', name)),
  };
  summary.cleanup_residue = residue;
  console.log(`[s7] cleanup residue: ${JSON.stringify(residue)}`);
  writeFileSync(
    path.join(evidenceDir, 'summary-with-cleanup.json'),
    `${JSON.stringify(summary, null, 2)}\n`,
  );
  const hasResidue =
    residue.containers.length + residue.volumes.length + residue.networks.length >
    0;
  if (hasResidue) {
    failure = failure ?? new Error('eqmd_s7_rehearsal residue remains');
  }
  if (failure) {
    process.exitCode = 1;
    return;
  }
  console.log('[s7] PASS');
  if (!ownsResources) {
    console.log('[s7] resources were never created');
  }
}

main();
